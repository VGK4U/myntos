/**
 * Staff My Leads Page
 * DC Protocol: DC_MOBILE_STAFF_LEADS_001
 * View and manage CRM leads assigned to staff
 * Enhanced with detail modal, follow-ups, and activity logging
 */

import { apiService } from '../services/api.service';
import { authService } from '../services/auth.service';
import { PageHeader } from '../components/PageHeader';
import { vgkBannerService } from '../services/vgk-banner.service';

interface Lead {
  id: number;
  name: string;
  phone: string;
  phone_primary_whatsapp?: boolean;
  alternate_phone?: string;
  email: string | null;
  category: string;
  category_id?: number;
  category_name?: string;
  company_id?: number;
  source: string | null;
  status: string;
  priority: string;
  created_at: string;
  updated_at?: string;
  last_followup: string | null;
  next_followup: string | null;
  notes: string | null;
  address?: string | null;
  area?: string | null;
  city?: string | null;
  state?: string | null;
  pincode?: string | null;
  requirements?: string | null;
  looking_for?: string | null;
  budget_min?: number | null;
  budget_max?: number | null;
  deal_value?: number;
  deal_value_total?: number;
  deal_value_received?: number;
  deal_value_balance?: number;
  handler_name?: string;
  telecaller_name?: string;
  field_staff_name?: string;
  mnr_handler_id?: string | null;
  mnr_handler_name?: string | null;
  guru_id?: string | null;
  guru_name?: string | null;
  z_guru_id?: string | null;
  z_guru_name?: string | null;
  submit_date?: string | null;  // DC-SUBMIT-DATE-001
  complete_date?: string | null;  // DC-COMPLETE-DATE-001
  solar_pipeline_status?: string | null;
  solar_brand_id?: number | null;
  solar_brand_name?: string | null;
  confirmed_final_value?: number | null;
  activities?: LeadActivity[];
  followups?: LeadFollowUp[];
  lead_notes?: LeadNote[];
}

interface LeadDeal {
  id: number;
  lead_id: number;
  company_id: number;
  revenue_category_id: number;
  deal_code: string;
  deal_date?: string;
  deal_value_total: number;
  deal_value_received: number;
  deal_value_balance: number;
  status: string;
  notes?: string;
  category_name?: string;
  category_code?: string;
  company_name?: string;
  created_at: string;
}

interface LeadTransaction {
  id: number;
  company_id: number;
  lead_id: number;
  deal_id?: number;
  transaction_date: string;
  amount: number;
  transaction_type: string;
  payment_mode: string;
  reference_number?: string;
  notes?: string;
  validation_status: string;
  validated_by_name?: string;
  validated_at?: string;
  created_by_name?: string;
  created_at: string;
}

interface RevenueCategory {
  id: number;
  name: string;
  slug?: string;
}

interface LeadActivity {
  id: number;
  type: string;
  description: string;
  created_at: string;
  created_by: string;
}

interface LeadFollowUp {
  id: number;
  scheduled_date: string;
  scheduled_time?: string;
  notes?: string;
  status: string;
  outcome?: string;
  created_at: string;
}

interface LeadNote {
  id: number;
  content: string;
  created_at: string;
  created_by_name: string;
}

interface Handler {
  id: number;
  name: string;
  emp_code: string;
}

const LEAD_STATUSES = ['new', 'contacted', 'qualified', 'negotiation', 'won', 'lost'];
const LEAD_PRIORITIES = ['low', 'normal', 'high', 'urgent'];
const QUICK_FILTERS = [
  { id: 'all', label: 'All Leads' },
  { id: 'today', label: "Today's Leads" },
  { id: 'overdue', label: 'Overdue Leads' },
  { id: 'future', label: 'Future Leads' },
  { id: 'no_followup', label: 'No Followup Leads' }
];

const ROLE_TABS = [
  { id: 'my_leads', label: 'My Leads', icon: '👤' },
  { id: 'as_primary', label: 'As Primary Holder', icon: '📋' },
  { id: 'as_telecaller', label: 'As Telecaller', icon: '📞' },
  { id: 'as_field', label: 'As Field Staff', icon: '🚗' },
  { id: 'as_handler', label: 'As Handler', icon: '🤝' },
  { id: 'fresh', label: 'Fresh Leads', icon: '✨' },
  { id: 'self', label: 'Self Leads', icon: '🎯' }
];

export class StaffLeadsPage {
  private container: HTMLElement;
  private leads: Lead[] = [];
  private loading: boolean = true;
  private activeRoleTab: string = 'my_leads';
  private activeStatusFilter: string = 'all';
  private selectedLead: Lead | null = null;
  private searchQuery: string = '';
  private dateFrom: string = '';
  private dateTo: string = '';
  private categoryFilter: string = '';
  private sourceFilter: string = '';
  private quickFilter: string = 'all';
  private daysSinceFilter: string = '';
  private submitDateFrom: string = '';  // DC-SUBMIT-DATE-001: Submit date filter (solar-only)
  private submitDateTo: string = '';
  private completeDateFrom: string = '';  // DC-COMPLETE-DATE-001: Complete date filter (solar-only)
  private completeDateTo: string = '';
  private dvrFrom: string = '';  // DC-SOLAR-DVR-ADV-20260701-001: 1st Txn Received date filter (solar-only)
  private dvrTo: string = '';
  private telecallerCode: string = '';
  private fieldStaffCode: string = '';
  private companies: Array<{id: number; name: string}> = [];
  private selectedCompanyId: number | null = null;
  private sortColumn: string = 'created_at';
  private sortDirection: 'asc' | 'desc' = 'desc';
  private leadDeals: LeadDeal[] = [];
  private leadTransactions: LeadTransaction[] = [];
  private revenueCategories: RevenueCategory[] = [];

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(params?: { leadId?: string; action?: string }): Promise<void> {
    this.render();
    await this.loadCompanies();
    await this.loadLeads();
    
    // DC Protocol: Handle navigation parameters for direct edit
    if (params?.action === 'edit' && params?.leadId) {
      await this.loadAndEditLead(parseInt(params.leadId));
    } else if (params?.action === 'create') {
      this.showAddLeadModal();
    }
  }

  private async loadCompanies(): Promise<void> {
    try {
      const authState = authService.getAuthState();
      const user = authState?.user;
      // Get companies from user's data_companies or make API call
      if (user?.data_companies) {
        this.companies = user.data_companies;
      } else {
        const response = await apiService.get<any>('/crm/my-companies');
        if (response.success && response.data) {
          this.companies = response.data;
        }
      }
    } catch (error) {
      console.error('[StaffLeads] Failed to load companies:', error);
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
      console.error('[StaffLeads] Pincode lookup failed:', error);
    }
  }

  private async loadAndEditLead(leadId: number): Promise<void> {
    try {
      const response = await apiService.get<any>(`/crm/leads/${leadId}`);
      if (response.success && response.data) {
        const lead = response.data;
        this.showEditLeadModal(lead);
      }
    } catch (error) {
      console.error('[StaffLeads] Failed to load lead for edit:', error);
      alert('Failed to load lead details');
    }
  }

  private async loadLeads(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const params = new URLSearchParams();
      
      // DC Protocol (Feb 2026): Company filter - null means all companies
      if (this.selectedCompanyId !== null) {
        params.append('company_id', this.selectedCompanyId.toString());
      }
      // If no company selected, don't include company_id for "All Companies" behavior
      
      params.append('role_filter', this.activeRoleTab);
      if (this.dateFrom) params.append('date_from', this.dateFrom);
      if (this.dateTo) params.append('date_to', this.dateTo);
      if (this.categoryFilter) params.append('category', this.categoryFilter);
      if (this.sourceFilter) params.append('source', this.sourceFilter);
      // DC Protocol (Feb 2026): Add quick filter support
      if (this.quickFilter && this.quickFilter !== 'all') params.append('quick_filter', this.quickFilter);
      // DC Protocol (Feb 2026): Add days since filter
      if (this.daysSinceFilter) params.append('days_since', this.daysSinceFilter);
      if (this.submitDateFrom) params.append('submit_date_from', this.submitDateFrom);
      if (this.submitDateTo) params.append('submit_date_to', this.submitDateTo);
      if (this.completeDateFrom) params.append('complete_date_from', this.completeDateFrom);
      if (this.completeDateTo) params.append('complete_date_to', this.completeDateTo);
      if (this.dvrFrom) params.append('first_dvr_from', this.dvrFrom);
      if (this.dvrTo) params.append('first_dvr_to', this.dvrTo);
      if (this.telecallerCode) params.append('telecaller_emp_code', this.telecallerCode);
      if (this.fieldStaffCode) params.append('field_staff_emp_code', this.fieldStaffCode);

      const response = await apiService.get<any>(`/crm/my-leads?${params.toString()}`);
      if (response.success && response.data) {
        this.leads = response.data.leads || response.data || [];
      }
    } catch (error) {
      console.error('[StaffLeads] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private getFilteredLeads(): Lead[] {
    let filtered = this.leads;
    
    if (this.activeStatusFilter !== 'all') {
      filtered = filtered.filter(l => l.status.toLowerCase() === this.activeStatusFilter);
    }
    
    if (this.searchQuery) {
      filtered = filtered.filter(l => 
        l.name.toLowerCase().includes(this.searchQuery) ||
        l.phone.includes(this.searchQuery) ||
        (l.email && l.email.toLowerCase().includes(this.searchQuery))
      );
    }
    
    // Apply sorting
    filtered = this.sortLeads(filtered);
    
    return filtered;
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container leads-page-enhanced">
        ${PageHeader.render({ title: 'My Leads', showBack: true, rightAction: { icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>', onClick: () => (window as any).__staffLeadsAddLead?.() } })}
        
        <!-- Role Filter Tabs -->
        <div class="role-tabs-scroll">
          <div class="role-tabs">
            ${ROLE_TABS.map(tab => `
              <button class="role-tab ${this.activeRoleTab === tab.id ? 'active' : ''}" data-role="${tab.id}">
                <span class="tab-icon">${tab.icon}</span>
                <span class="tab-label">${tab.label}</span>
              </button>
            `).join('')}
          </div>
        </div>
        
        <!-- Filter Bar -->
        <div class="leads-filter-bar">
          <div class="filter-row">
            <div class="filter-group flex-grow">
              <select id="companyFilter" class="form-select">
                <option value="">All Companies</option>
                ${this.companies.map(c => 
                  `<option value="${c.id}" ${this.selectedCompanyId === c.id ? 'selected' : ''}>${c.name}</option>`
                ).join('')}
              </select>
            </div>
          </div>
          <div class="filter-row">
            <div class="filter-group">
              <input type="date" id="dateFrom" class="form-input filter-date" value="${this.dateFrom}" placeholder="From Date">
            </div>
            <div class="filter-group">
              <input type="date" id="dateTo" class="form-input filter-date" value="${this.dateTo}" placeholder="To Date">
            </div>
          </div>
          <div class="filter-row solar-filter-row" style="${this.categoryFilter.toLowerCase().includes('solar') ? '' : 'display:none'}">
            <div class="filter-group">
              <input type="date" id="submitDateFrom" class="form-input filter-date" value="${this.submitDateFrom}" placeholder="Submit From">
            </div>
            <div class="filter-group">
              <input type="date" id="submitDateTo" class="form-input filter-date" value="${this.submitDateTo}" placeholder="Submit To">
            </div>
            <div class="filter-group">
              <input type="date" id="completeDateFrom" class="form-input filter-date" value="${this.completeDateFrom}" placeholder="Complete From">
            </div>
            <div class="filter-group">
              <input type="date" id="completeDateTo" class="form-input filter-date" value="${this.completeDateTo}" placeholder="Complete To">
            </div>
            <div class="filter-group">
              <input type="date" id="dvrFromFilter" class="form-input filter-date" value="${this.dvrFrom}" placeholder="1st Txn From">
            </div>
            <div class="filter-group">
              <input type="date" id="dvrToFilter" class="form-input filter-date" value="${this.dvrTo}" placeholder="1st Txn To">
            </div>
            <div class="filter-group flex-grow">
              <input type="text" id="telecallerCodeFilter" class="form-input" value="${this.telecallerCode}" placeholder="Support (Emp Code)">
            </div>
            <div class="filter-group flex-grow">
              <input type="text" id="fieldStaffCodeFilter" class="form-input" value="${this.fieldStaffCode}" placeholder="Showroom (Emp Code)">
            </div>
          </div>
          <div class="filter-row">
            <div class="filter-group flex-grow">
              <select id="quickFilterSelect" class="form-select">
                ${QUICK_FILTERS.map(f => 
                  `<option value="${f.id}" ${this.quickFilter === f.id ? 'selected' : ''}>${f.label}</option>`
                ).join('')}
              </select>
            </div>
            <div class="filter-group flex-grow">
              <select id="categoryFilter" class="form-select">
                <option value="">All Categories</option>
                <option value="EV" ${this.categoryFilter === 'EV' ? 'selected' : ''}>EV</option>
                <option value="Real Estate" ${this.categoryFilter === 'Real Estate' ? 'selected' : ''}>Real Estate</option>
                <option value="Insurance" ${this.categoryFilter === 'Insurance' ? 'selected' : ''}>Insurance</option>
                <option value="MNR" ${this.categoryFilter === 'MNR' ? 'selected' : ''}>MNR Referral</option>
              </select>
            </div>
          </div>
          <div class="filter-row">
            <div class="filter-group flex-grow">
              <select id="sourceFilter" class="form-select">
                <option value="">All Sources</option>
                <option value="Self Lead" ${this.sourceFilter === 'Self Lead' ? 'selected' : ''}>Self Lead</option>
                <option value="Direct" ${this.sourceFilter === 'Direct' ? 'selected' : ''}>Direct</option>
                <option value="Referral" ${this.sourceFilter === 'Referral' ? 'selected' : ''}>Referral</option>
                <option value="Website" ${this.sourceFilter === 'Website' ? 'selected' : ''}>Website</option>
                <option value="Social Media" ${this.sourceFilter === 'Social Media' ? 'selected' : ''}>Social Media</option>
              </select>
            </div>
            <div class="filter-group flex-grow">
              <select id="daysSinceFilter" class="form-select">
                <option value="">Days Since</option>
                <option value="lt6" ${this.daysSinceFilter === 'lt6' ? 'selected' : ''}>< 6 days</option>
                <option value="6-15" ${this.daysSinceFilter === '6-15' ? 'selected' : ''}>6-15 days</option>
                <option value="15-30" ${this.daysSinceFilter === '15-30' ? 'selected' : ''}>15-30 days</option>
                <option value="gt30" ${this.daysSinceFilter === 'gt30' ? 'selected' : ''}>> 30 days</option>
              </select>
            </div>
          </div>
        </div>
        
        <div class="search-box">
          <input type="text" id="searchInput" class="form-input" placeholder="Search leads by name, mobile...">
        </div>
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>

      <!-- Lead Detail Modal -->
      <div class="modal-overlay" id="detailModal" style="display: none;">
        <div class="modal-content modal-lg modal-fullscreen">
          <div class="modal-header">
            <h4>Lead Details</h4>
            <button class="modal-close" id="closeDetailModal">&times;</button>
          </div>
          <div class="modal-body" id="detailBody"></div>
        </div>
      </div>

      <!-- Add/Edit Lead Modal - Enhanced Design -->
      <div class="modal-overlay" id="leadFormModal" style="display: none;">
        <style>
          #leadFormModal .modal-content {
            max-height: 90vh;
            width: 100%;
            max-width: 420px;
            background: linear-gradient(180deg, #1e3a5f 0%, #0d1b2a 100%);
            border-radius: 20px;
            display: flex;
            flex-direction: column;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.1);
            animation: modalSlideUp 0.3s ease-out;
          }
          @keyframes modalSlideUp {
            from { transform: translateY(30px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
          }
          #leadFormModal .modal-header {
            background: linear-gradient(135deg, #10b981 0%, #047857 100%);
            padding: 20px 24px;
            border-radius: 20px 20px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: relative;
            overflow: hidden;
          }
          #leadFormModal .modal-header::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -20%;
            width: 100px;
            height: 100px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 50%;
          }
          #leadFormModal .modal-header h4 {
            margin: 0;
            color: white;
            font-size: 20px;
            font-weight: 700;
            position: relative;
            z-index: 1;
          }
          #leadFormModal .modal-close {
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
          #leadFormModal .modal-close:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: scale(1.05);
          }
          #leadFormModal .modal-body {
            padding: 24px;
            overflow-y: auto;
            flex: 1;
            max-height: calc(90vh - 180px);
          }
          #leadFormModal .modal-body::-webkit-scrollbar {
            width: 6px;
          }
          #leadFormModal .modal-body::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 3px;
          }
          #leadFormModal .modal-body::-webkit-scrollbar-thumb {
            background: rgba(16, 185, 129, 0.5);
            border-radius: 3px;
          }
          #leadFormModal .form-section {
            margin-bottom: 20px;
          }
          #leadFormModal .section-title {
            font-size: 12px;
            font-weight: 600;
            color: #10b981;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid rgba(16, 185, 129, 0.2);
          }
          #leadFormModal .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 14px;
          }
          #leadFormModal .form-group {
            margin-bottom: 16px;
          }
          #leadFormModal .form-group label {
            display: flex;
            align-items: center;
            gap: 6px;
            color: #a8c0d8;
            font-size: 13px;
            font-weight: 500;
            margin-bottom: 8px;
          }
          #leadFormModal .form-group label .required {
            color: #f87171;
            font-weight: bold;
          }
          #leadFormModal .form-input,
          #leadFormModal .form-select,
          #leadFormModal .form-textarea {
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
          #leadFormModal .form-input::placeholder,
          #leadFormModal .form-textarea::placeholder {
            color: rgba(168, 192, 216, 0.5);
          }
          #leadFormModal .form-input:focus,
          #leadFormModal .form-select:focus,
          #leadFormModal .form-textarea:focus {
            outline: none;
            border-color: #10b981;
            background: rgba(16, 185, 129, 0.08);
            box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15);
          }
          #leadFormModal .form-select {
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%2310b981' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 14px center;
            padding-right: 40px;
            cursor: pointer;
          }
          #leadFormModal .form-select option {
            background: #1e3a5f;
            color: #e6f1ff;
            padding: 10px;
          }
          #leadFormModal .form-textarea {
            resize: vertical;
            min-height: 70px;
          }
          #leadFormModal .modal-footer {
            padding: 20px 24px;
            border-top: 1px solid rgba(255, 255, 255, 0.08);
            display: flex;
            gap: 12px;
            justify-content: stretch;
            flex-shrink: 0;
            background: rgba(13, 27, 42, 0.5);
            border-radius: 0 0 20px 20px;
          }
          #leadFormModal .btn-secondary {
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
          #leadFormModal .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.12);
            border-color: rgba(255, 255, 255, 0.25);
          }
          #leadFormModal .btn-primary {
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
          }
          #leadFormModal .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(16, 185, 129, 0.45);
          }
          #leadFormModal .btn-primary:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
          }
        </style>
        <div class="modal-content" style="max-height: 90vh; width: 100%; max-width: 420px; background: linear-gradient(180deg, #1e3a5f 0%, #0d1b2a 100%) !important; border-radius: 20px; padding: 0; display: flex; flex-direction: column; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);">
          <div class="modal-header" style="background: linear-gradient(135deg, #10b981 0%, #047857 100%) !important; padding: 20px 24px; border-radius: 20px 20px 0 0; display: flex; justify-content: space-between; align-items: center;">
            <h4 id="leadFormTitle" style="margin: 0; color: white !important; font-size: 20px; font-weight: 700;">Add New Lead</h4>
            <button class="modal-close" id="closeFormModal" style="background: rgba(255, 255, 255, 0.2); border: none; color: white; width: 36px; height: 36px; border-radius: 10px; font-size: 22px; cursor: pointer; display: flex; align-items: center; justify-content: center;">&times;</button>
          </div>
          <div class="modal-body" style="padding: 24px; overflow-y: auto; flex: 1; max-height: calc(90vh - 180px);">
            <div class="form-section" style="margin-bottom: 20px;">
              <div class="section-title" style="font-size: 12px; font-weight: 600; color: #10b981; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid rgba(16, 185, 129, 0.2);">Basic Information</div>
              <div class="form-group" style="margin-bottom: 16px;">
                <label style="display: flex; align-items: center; gap: 6px; color: #a8c0d8; font-size: 13px; font-weight: 500; margin-bottom: 8px;">Name <span class="required" style="color: #f87171;">*</span></label>
                <input type="text" id="leadName" class="form-input" placeholder="Full name" style="width: 100%; padding: 14px 16px; border-radius: 12px; border: 2px solid rgba(255, 255, 255, 0.08); background: rgba(13, 27, 42, 0.6) !important; color: #e6f1ff !important; font-size: 15px; box-sizing: border-box;">
              </div>
              <div class="form-row" style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
                <div class="form-group" style="margin-bottom: 16px;">
                  <label style="display: flex; align-items: center; gap: 6px; color: #a8c0d8; font-size: 13px; font-weight: 500; margin-bottom: 8px;">Mobile <span class="required" style="color: #f87171;">*</span></label>
                  <input type="tel" id="leadMobile" class="form-input" placeholder="10-digit mobile" maxlength="10" inputmode="numeric" style="width: 100%; padding: 14px 16px; border-radius: 12px; border: 2px solid rgba(255, 255, 255, 0.08); background: rgba(13, 27, 42, 0.6) !important; color: #e6f1ff !important; font-size: 15px; box-sizing: border-box;">
                </div>
                <div class="form-group" style="margin-bottom: 16px;">
                  <label style="display: flex; align-items: center; gap: 6px; color: #a8c0d8; font-size: 13px; font-weight: 500; margin-bottom: 8px;">Email</label>
                  <input type="email" id="leadEmail" class="form-input" placeholder="email@example.com" style="width: 100%; padding: 14px 16px; border-radius: 12px; border: 2px solid rgba(255, 255, 255, 0.08); background: rgba(13, 27, 42, 0.6) !important; color: #e6f1ff !important; font-size: 15px; box-sizing: border-box;">
                </div>
              </div>
            </div>
            
            <div class="form-section" style="margin-bottom: 20px;">
              <div class="section-title" style="font-size: 12px; font-weight: 600; color: #10b981; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid rgba(16, 185, 129, 0.2);">Lead Classification</div>
              <div class="form-row" style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
                <div class="form-group" style="margin-bottom: 16px;">
                  <label style="display: flex; align-items: center; gap: 6px; color: #a8c0d8; font-size: 13px; font-weight: 500; margin-bottom: 8px;">Category <span class="required" style="color: #f87171;">*</span></label>
                  <select id="leadCategory" class="form-select" style="width: 100%; padding: 14px 16px; border-radius: 12px; border: 2px solid rgba(255, 255, 255, 0.08); background: rgba(13, 27, 42, 0.6) !important; color: #e6f1ff !important; font-size: 15px; box-sizing: border-box; appearance: none;">
                    <option value="">Select category...</option>
                    <option value="EV">EV</option>
                    <option value="Solar">Solar</option>
                    <option value="Real Estate">Real Estate</option>
                    <option value="Insurance">Insurance</option>
                    <option value="MNR">MNR Referral</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
                <div class="form-group" style="margin-bottom: 16px;">
                  <label style="display: flex; align-items: center; gap: 6px; color: #a8c0d8; font-size: 13px; font-weight: 500; margin-bottom: 8px;">Priority</label>
                  <select id="leadPriority" class="form-select" style="width: 100%; padding: 14px 16px; border-radius: 12px; border: 2px solid rgba(255, 255, 255, 0.08); background: rgba(13, 27, 42, 0.6) !important; color: #e6f1ff !important; font-size: 15px; box-sizing: border-box; appearance: none;">
                    ${LEAD_PRIORITIES.map(p => `<option value="${p}">${p.charAt(0).toUpperCase() + p.slice(1)}</option>`).join('')}
                  </select>
                </div>
              </div>
              <div class="form-group" style="margin-bottom: 16px;">
                <label style="display: flex; align-items: center; gap: 6px; color: #a8c0d8; font-size: 13px; font-weight: 500; margin-bottom: 8px;">Source</label>
                <select id="leadSource" class="form-select" style="width: 100%; padding: 14px 16px; border-radius: 12px; border: 2px solid rgba(255, 255, 255, 0.08); background: rgba(13, 27, 42, 0.6) !important; color: #e6f1ff !important; font-size: 15px; box-sizing: border-box; appearance: none;">
                  <option value="">Select source...</option>
                  <option value="Direct">Direct</option>
                  <option value="Referral">Referral</option>
                  <option value="Website">Website</option>
                  <option value="Social Media">Social Media</option>
                  <option value="Cold Call">Cold Call</option>
                  <option value="Event">Event</option>
                </select>
              </div>
            </div>
            
            <div class="form-section" style="margin-bottom: 20px;">
              <div class="section-title" style="font-size: 12px; font-weight: 600; color: #10b981; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid rgba(16, 185, 129, 0.2);">Contact Details</div>
              <div class="form-group" style="margin-bottom: 8px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                  <input type="checkbox" id="leadPhoneWhatsapp" checked style="width: 18px; height: 18px; accent-color: #10b981;">
                  <label for="leadPhoneWhatsapp" style="color: #a8c0d8; font-size: 13px;">WhatsApp on Primary</label>
                </div>
              </div>
              <div class="form-group" style="margin-bottom: 16px;">
                <label style="display: flex; align-items: center; gap: 6px; color: #a8c0d8; font-size: 13px; font-weight: 500; margin-bottom: 8px;">Alternate Mobile</label>
                <input type="tel" id="leadMobileSecondary" class="form-input" placeholder="Alternate number" maxlength="10" inputmode="numeric" style="width: 100%; padding: 14px 16px; border-radius: 12px; border: 2px solid rgba(255, 255, 255, 0.08); background: rgba(13, 27, 42, 0.6) !important; color: #e6f1ff !important; font-size: 15px; box-sizing: border-box;">
              </div>
              <div class="form-group" style="margin-bottom: 8px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                  <input type="checkbox" id="leadPhoneSecondaryWhatsapp" style="width: 18px; height: 18px; accent-color: #10b981;">
                  <label for="leadPhoneSecondaryWhatsapp" style="color: #a8c0d8; font-size: 13px;">WhatsApp on Alternate</label>
                </div>
              </div>
            </div>

            <div class="form-section" style="margin-bottom: 20px;">
              <div class="section-title" style="font-size: 12px; font-weight: 600; color: #10b981; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid rgba(16, 185, 129, 0.2);">Requirements & Budget</div>
              <div class="form-group" style="margin-bottom: 16px;">
                <label style="display: flex; align-items: center; gap: 6px; color: #a8c0d8; font-size: 13px; font-weight: 500; margin-bottom: 8px;">Looking For</label>
                <input type="text" id="leadLookingFor" class="form-input" placeholder="What is the lead looking for?" style="width: 100%; padding: 14px 16px; border-radius: 12px; border: 2px solid rgba(255, 255, 255, 0.08); background: rgba(13, 27, 42, 0.6) !important; color: #e6f1ff !important; font-size: 15px; box-sizing: border-box;">
              </div>
              <div class="form-group" style="margin-bottom: 16px;">
                <label style="display: flex; align-items: center; gap: 6px; color: #a8c0d8; font-size: 13px; font-weight: 500; margin-bottom: 8px;">Requirements</label>
                <textarea id="leadRequirements" class="form-textarea" rows="2" placeholder="Detailed requirements..." style="width: 100%; padding: 14px 16px; border-radius: 12px; border: 2px solid rgba(255, 255, 255, 0.08); background: rgba(13, 27, 42, 0.6) !important; color: #e6f1ff !important; font-size: 15px; box-sizing: border-box; resize: vertical; min-height: 60px;"></textarea>
              </div>
              <div class="form-row" style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
                <div class="form-group" style="margin-bottom: 16px;">
                  <label style="display: flex; align-items: center; gap: 6px; color: #a8c0d8; font-size: 13px; font-weight: 500; margin-bottom: 8px;">Budget Min</label>
                  <input type="number" id="leadBudgetMin" class="form-input" placeholder="Min" inputmode="numeric" style="width: 100%; padding: 14px 16px; border-radius: 12px; border: 2px solid rgba(255, 255, 255, 0.08); background: rgba(13, 27, 42, 0.6) !important; color: #e6f1ff !important; font-size: 15px; box-sizing: border-box;">
                </div>
                <div class="form-group" style="margin-bottom: 16px;">
                  <label style="display: flex; align-items: center; gap: 6px; color: #a8c0d8; font-size: 13px; font-weight: 500; margin-bottom: 8px;">Budget Max</label>
                  <input type="number" id="leadBudgetMax" class="form-input" placeholder="Max" inputmode="numeric" style="width: 100%; padding: 14px 16px; border-radius: 12px; border: 2px solid rgba(255, 255, 255, 0.08); background: rgba(13, 27, 42, 0.6) !important; color: #e6f1ff !important; font-size: 15px; box-sizing: border-box;">
                </div>
              </div>
            </div>

            <div class="form-section" style="margin-bottom: 20px;">
              <div class="section-title" style="font-size: 12px; font-weight: 600; color: #10b981; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid rgba(16, 185, 129, 0.2);">Location Details</div>
              <div class="form-group" style="margin-bottom: 16px;">
                <label style="display: flex; align-items: center; gap: 6px; color: #a8c0d8; font-size: 13px; font-weight: 500; margin-bottom: 8px;">Address</label>
                <textarea id="leadAddress" class="form-textarea" rows="2" placeholder="Street address" style="width: 100%; padding: 14px 16px; border-radius: 12px; border: 2px solid rgba(255, 255, 255, 0.08); background: rgba(13, 27, 42, 0.6) !important; color: #e6f1ff !important; font-size: 15px; box-sizing: border-box; resize: vertical; min-height: 60px;"></textarea>
              </div>
              <div class="form-row" style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
                <div class="form-group" style="margin-bottom: 16px;">
                  <label style="display: flex; align-items: center; gap: 6px; color: #a8c0d8; font-size: 13px; font-weight: 500; margin-bottom: 8px;">Area</label>
                  <input type="text" id="leadArea" class="form-input" placeholder="Area/Locality" style="width: 100%; padding: 14px 16px; border-radius: 12px; border: 2px solid rgba(255, 255, 255, 0.08); background: rgba(13, 27, 42, 0.6) !important; color: #e6f1ff !important; font-size: 15px; box-sizing: border-box;">
                </div>
                <div class="form-group" style="margin-bottom: 16px;">
                  <label style="display: flex; align-items: center; gap: 6px; color: #a8c0d8; font-size: 13px; font-weight: 500; margin-bottom: 8px;">City</label>
                  <input type="text" id="leadCity" class="form-input" placeholder="City" style="width: 100%; padding: 14px 16px; border-radius: 12px; border: 2px solid rgba(255, 255, 255, 0.08); background: rgba(13, 27, 42, 0.6) !important; color: #e6f1ff !important; font-size: 15px; box-sizing: border-box;">
                </div>
              </div>
              <div class="form-row" style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
                <div class="form-group" style="margin-bottom: 16px;">
                  <label style="display: flex; align-items: center; gap: 6px; color: #a8c0d8; font-size: 13px; font-weight: 500; margin-bottom: 8px;">State</label>
                  <input type="text" id="leadState" class="form-input" placeholder="State" style="width: 100%; padding: 14px 16px; border-radius: 12px; border: 2px solid rgba(255, 255, 255, 0.08); background: rgba(13, 27, 42, 0.6) !important; color: #e6f1ff !important; font-size: 15px; box-sizing: border-box;">
                </div>
                <div class="form-group" style="margin-bottom: 16px;">
                  <label style="display: flex; align-items: center; gap: 6px; color: #a8c0d8; font-size: 13px; font-weight: 500; margin-bottom: 8px;">Pincode</label>
                  <input type="text" id="leadPincode" class="form-input" placeholder="PIN" maxlength="6" inputmode="numeric" style="width: 100%; padding: 14px 16px; border-radius: 12px; border: 2px solid rgba(255, 255, 255, 0.08); background: rgba(13, 27, 42, 0.6) !important; color: #e6f1ff !important; font-size: 15px; box-sizing: border-box;">
                </div>
              </div>
            </div>

            <div class="form-section" style="margin-bottom: 20px;">
              <div class="section-title" style="font-size: 12px; font-weight: 600; color: #10b981; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid rgba(16, 185, 129, 0.2);">Follow-up & Notes</div>
              <div class="form-row" style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
                <div class="form-group" style="margin-bottom: 16px;">
                  <label style="display: flex; align-items: center; gap: 6px; color: #a8c0d8; font-size: 13px; font-weight: 500; margin-bottom: 8px;">Expected Close</label>
                  <input type="date" id="leadExpectedCloseDate" class="form-input" style="width: 100%; padding: 14px 16px; border-radius: 12px; border: 2px solid rgba(255, 255, 255, 0.08); background: rgba(13, 27, 42, 0.6) !important; color: #e6f1ff !important; font-size: 15px; box-sizing: border-box;">
                </div>
                <div class="form-group" style="margin-bottom: 16px;">
                  <label style="display: flex; align-items: center; gap: 6px; color: #a8c0d8; font-size: 13px; font-weight: 500; margin-bottom: 8px;">Next Followup</label>
                  <input type="date" id="leadNextFollowupDate" class="form-input" style="width: 100%; padding: 14px 16px; border-radius: 12px; border: 2px solid rgba(255, 255, 255, 0.08); background: rgba(13, 27, 42, 0.6) !important; color: #e6f1ff !important; font-size: 15px; box-sizing: border-box;">
                </div>
              </div>
              <div class="form-group" style="margin-bottom: 16px;">
                <label style="display: flex; align-items: center; gap: 6px; color: #a8c0d8; font-size: 13px; font-weight: 500; margin-bottom: 8px;">Tags</label>
                <input type="text" id="leadTags" class="form-input" placeholder="Comma separated tags" style="width: 100%; padding: 14px 16px; border-radius: 12px; border: 2px solid rgba(255, 255, 255, 0.08); background: rgba(13, 27, 42, 0.6) !important; color: #e6f1ff !important; font-size: 15px; box-sizing: border-box;">
              </div>
              <div class="form-group" style="margin-bottom: 16px;">
                <label style="display: flex; align-items: center; gap: 6px; color: #a8c0d8; font-size: 13px; font-weight: 500; margin-bottom: 8px;">Notes</label>
                <textarea id="leadNotes" class="form-textarea" rows="2" placeholder="Additional notes..." style="width: 100%; padding: 14px 16px; border-radius: 12px; border: 2px solid rgba(255, 255, 255, 0.08); background: rgba(13, 27, 42, 0.6) !important; color: #e6f1ff !important; font-size: 15px; box-sizing: border-box; resize: vertical; min-height: 60px;"></textarea>
              </div>
            </div>

            <div class="form-section" style="margin-bottom: 20px;">
              <div class="section-title" style="font-size: 12px; font-weight: 600; color: #8b5cf6; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid rgba(139, 92, 246, 0.2);">Network Assignment (Optional)</div>
              <div class="form-group" style="margin-bottom: 12px; position: relative;">
                <label style="display: flex; align-items: center; gap: 6px; color: #a8c0d8; font-size: 13px; font-weight: 500; margin-bottom: 8px;">MNR/VGK Handler</label>
                <input type="text" id="leadNetworkSearch" class="form-input" placeholder="Search by MNR/VGK ID or name..." autocomplete="off" style="width: 100%; padding: 14px 16px; border-radius: 12px; border: 2px solid rgba(139, 92, 246, 0.3); background: rgba(13, 27, 42, 0.6) !important; color: #e6f1ff !important; font-size: 15px; box-sizing: border-box;">
                <input type="hidden" id="leadMnrHandlerId">
                <input type="hidden" id="leadGuruId">
                <!-- DC-VGK-BRAND-INCENTIVE-001: Solar brand dropdown (hidden for non-solar) -->
                <div id="solarBrandSection" style="display:none; margin-top:12px">
                  <label style="display:flex;align-items:center;gap:6px;color:#a8c0d8;font-size:13px;font-weight:500;margin-bottom:8px"><i class="fas fa-tag" style="color:#0891b2"></i>Solar Brand (incentive)</label>
                  <select id="leadSolarBrandId" style="width:100%;padding:14px 16px;border-radius:12px;border:2px solid rgba(255,255,255,.08);background:rgba(13,27,42,.6)!important;color:#e6f1ff!important;font-size:15px;box-sizing:border-box;appearance:none">
                    <option value="">None</option>
                  </select>
                </div>
                <div id="leadNetworkDropdown" style="display: none; position: absolute; top: 100%; left: 0; right: 0; background: #1a2f4a; border: 1px solid rgba(139, 92, 246, 0.4); border-radius: 10px; max-height: 180px; overflow-y: auto; z-index: 200; margin-top: 4px; box-shadow: 0 8px 24px rgba(0,0,0,0.4);"></div>
              </div>
              <div id="leadNetworkSelected" style="display: none; background: rgba(139, 92, 246, 0.1); border: 1px solid rgba(139, 92, 246, 0.3); border-radius: 10px; padding: 10px 14px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <span id="leadNetworkSelectedText" style="color: #c4b5fd; font-weight: 600; font-size: 14px;"></span>
                  <button id="leadNetworkClearBtn" style="background: none; border: none; color: #f87171; cursor: pointer; font-size: 20px; line-height: 1; padding: 0 4px;">×</button>
                </div>
                <div id="leadGuruRow" style="display: none; color: #a8c0d8; font-size: 12px; margin-top: 4px;">Senior: <span id="leadGuruName" style="color: #93c5fd;"></span></div>
              </div>
            </div>
          </div>
          <div class="modal-footer" style="padding: 20px 24px; border-top: 1px solid rgba(255, 255, 255, 0.08); display: flex; gap: 12px; background: rgba(13, 27, 42, 0.5); border-radius: 0 0 20px 20px;">
            <button class="btn btn-secondary" id="cancelFormBtn" style="flex: 1; padding: 16px 20px; background: rgba(255, 255, 255, 0.08); border: 2px solid rgba(255, 255, 255, 0.15); color: #a8c0d8; border-radius: 12px; font-size: 15px; font-weight: 600; cursor: pointer;">Cancel</button>
            <button class="btn btn-primary" id="saveLeadBtn" style="flex: 1.5; padding: 16px 20px; background: linear-gradient(135deg, #10b981 0%, #047857 100%); border: none; color: white; border-radius: 12px; font-size: 15px; font-weight: 700; cursor: pointer; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.35);">Create Lead</button>
          </div>
        </div>
      </div>

      <!-- Action Modal Styles -->
      <style>
        /* Horizontal Stats Layout */
        .leads-stats { background: linear-gradient(135deg, #1e3a5f 0%, #0d2137 100%); border-radius: 16px; padding: 16px 20px; margin: 12px 0; }
        .leads-stats .stats-row { display: flex; flex-direction: row; justify-content: space-around; align-items: center; gap: 8px; }
        .leads-stats .stat-item { display: flex; flex-direction: column; align-items: center; flex: 1; padding: 8px 4px; border-right: 1px solid rgba(255,255,255,0.1); }
        .leads-stats .stat-item:last-child { border-right: none; }
        .leads-stats .stat-value { font-size: 28px; font-weight: 700; color: #10b981; line-height: 1.2; }
        .leads-stats .stat-value.success { color: #10b981; }
        
        /* Sortable Table Headers */
        .leads-table th.sortable { cursor: pointer; user-select: none; white-space: nowrap; }
        .leads-table th.sortable:hover { background: rgba(16, 185, 129, 0.15); }
        .leads-table th.sortable .sort-icon { margin-left: 4px; opacity: 0.4; font-size: 12px; }
        .leads-table th.sortable .sort-icon.active { opacity: 1; color: #10b981; }
        .leads-stats .stat-value.warning { color: #f59e0b; }
        .leads-stats .stat-label { font-size: 12px; color: #a8c0d8; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }
        
        /* Action Modal Dark Theme */
        .action-modal .modal-content { max-width: 380px; width: 100%; background: linear-gradient(180deg, #1e3a5f 0%, #0d1b2a 100%); border-radius: 16px; box-shadow: 0 20px 50px rgba(0,0,0,0.5); }
        .action-modal .modal-header { background: linear-gradient(135deg, #10b981 0%, #047857 100%); padding: 16px 20px; border-radius: 16px 16px 0 0; display: flex; justify-content: space-between; align-items: center; }
        .action-modal .modal-header h4 { margin: 0; color: white; font-size: 16px; font-weight: 600; }
        .action-modal .modal-close { background: rgba(255,255,255,0.2); border: none; color: white; width: 32px; height: 32px; border-radius: 8px; font-size: 20px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
        .action-modal .modal-body { padding: 20px; }
        .action-modal .form-group { margin-bottom: 16px; }
        .action-modal .form-group label { display: block; color: #a8c0d8; font-size: 13px; font-weight: 500; margin-bottom: 8px; }
        .action-modal .form-group label .required { color: #f87171; }
        .action-modal .form-input, .action-modal .form-select, .action-modal .form-textarea { width: 100%; padding: 12px 14px; background: rgba(13, 27, 42, 0.8) !important; border: 1px solid rgba(255,255,255,0.15) !important; border-radius: 10px; color: #e6f1ff !important; font-size: 14px; box-sizing: border-box; -webkit-appearance: none; }
        .action-modal input[type="date"], .action-modal input[type="time"] { background: rgba(13, 27, 42, 0.8) !important; border: 1px solid rgba(255,255,255,0.15) !important; color: #e6f1ff !important; color-scheme: dark; }
        .action-modal .form-input:focus, .action-modal .form-select:focus, .action-modal .form-textarea:focus { outline: none; border-color: #10b981 !important; background: rgba(16,185,129,0.1) !important; }
        .action-modal .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .action-modal .form-hint { font-size: 12px; color: #6b7280; margin-top: 4px; }
        .action-modal .modal-footer { padding: 16px 20px; border-top: 1px solid rgba(255,255,255,0.08); display: flex; gap: 12px; }
        .action-modal .btn { flex: 1; padding: 14px; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; border: none; }
        .action-modal .btn-secondary { background: rgba(255,255,255,0.08); color: #a8c0d8; border: 1px solid rgba(255,255,255,0.15); }
        .action-modal .btn-primary { background: linear-gradient(135deg, #10b981 0%, #047857 100%); color: white; box-shadow: 0 4px 12px rgba(16,185,129,0.3); }
        .action-modal .btn-danger { background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white; }
      </style>

      <!-- Follow-up Modal -->
      <div class="modal-overlay action-modal" id="followupModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Schedule Follow-up</h4>
            <button class="modal-close" id="closeFollowupModal">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>Follow-up Date <span class="required">*</span></label>
              <input type="date" id="followupDate" class="form-input">
            </div>
            <div class="form-group">
              <label>Follow-up Time</label>
              <input type="time" id="followupTime" class="form-input">
            </div>
            <div class="form-group">
              <label>Notes</label>
              <textarea id="followupNotes" class="form-textarea" rows="2" placeholder="Follow-up agenda..."></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="cancelFollowupBtn">Cancel</button>
            <button class="btn btn-primary" id="saveFollowupBtn">Schedule</button>
          </div>
        </div>
      </div>

      <!-- Status Update Modal -->
      <div class="modal-overlay action-modal" id="statusModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Update Status</h4>
            <button class="modal-close" id="closeStatusModal">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>New Status <span class="required">*</span></label>
              <select id="newStatus" class="form-select">
                ${LEAD_STATUSES.map(s => `<option value="${s}">${s.charAt(0).toUpperCase() + s.slice(1)}</option>`).join('')}
              </select>
            </div>
            <div class="form-group">
              <label>Remarks</label>
              <textarea id="statusRemarks" class="form-textarea" rows="2" placeholder="Reason for status change..."></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="cancelStatusBtn">Cancel</button>
            <button class="btn btn-primary" id="saveStatusBtn">Update Status</button>
          </div>
        </div>
      </div>

      <!-- Activity Log Modal -->
      <div class="modal-overlay action-modal" id="activityModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Log Activity</h4>
            <button class="modal-close" id="closeActivityModal">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>Activity Type <span class="required">*</span></label>
              <select id="activityType" class="form-select">
                <option value="call">Phone Call</option>
                <option value="email">Email</option>
                <option value="meeting">Meeting</option>
                <option value="whatsapp">WhatsApp</option>
                <option value="site_visit">Site Visit</option>
                <option value="note">Note</option>
              </select>
            </div>
            <div class="form-group">
              <label>Description <span class="required">*</span></label>
              <textarea id="activityDescription" class="form-textarea" rows="3" placeholder="What happened?"></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="cancelActivityBtn">Cancel</button>
            <button class="btn btn-primary" id="saveActivityBtn">Log Activity</button>
          </div>
        </div>
      </div>

      <!-- Add Note Modal -->
      <div class="modal-overlay action-modal" id="noteModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Add Note</h4>
            <button class="modal-close" id="closeNoteModal">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>Note <span class="required">*</span></label>
              <textarea id="noteContent" class="form-textarea" rows="4" placeholder="Enter your note..."></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="cancelNoteBtn">Cancel</button>
            <button class="btn btn-primary" id="saveNoteBtn">Save Note</button>
          </div>
        </div>
      </div>

      <!-- Deal Value Modal -->
      <div class="modal-overlay action-modal" id="dealModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Update Value</h4>
            <button class="modal-close" id="closeDealModal">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>Total Value</label>
              <input type="number" id="dealTotal" class="form-input" placeholder="0.00">
            </div>
            <div class="form-group">
              <label>Amount Received <span style="font-size:10px;color:#6b7280;">auto — from validated payments</span></label>
              <input type="number" id="dealReceived" class="form-input" placeholder="0.00" readonly style="background:#f3f4f6;opacity:0.8;" title="Auto-calculated from validated payment transactions.">
            </div>
            <div class="form-group" id="cfvOverrideGroup" style="display:none;">
              <label style="color:#92400e;">Confirmed Final (₹) <span style="font-size:10px;background:#fef9c3;border:1px solid #fcd34d;padding:1px 5px;border-radius:4px;">Override</span></label>
              <input type="number" id="dealConfirmedFinal" class="form-input" placeholder="Override confirmed final value">
            </div>
            <p class="form-hint">Balance will be calculated automatically</p>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="cancelDealBtn">Cancel</button>
            <button class="btn btn-primary" id="saveDealBtn">Update</button>
          </div>
        </div>
      </div>

      <!-- Create Task Modal -->
      <div class="modal-overlay action-modal" id="taskModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Create Task from Lead</h4>
            <button class="modal-close" id="closeTaskModal">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>Task Title <span class="required">*</span></label>
              <input type="text" id="taskTitle" class="form-input" placeholder="Task title...">
            </div>
            <div class="form-group">
              <label>Description</label>
              <textarea id="taskDescription" class="form-textarea" rows="2" placeholder="Task description..."></textarea>
            </div>
            <div class="form-group">
              <label>Assignee <span class="required">*</span></label>
              <select id="taskAssignee" class="form-select">
                <option value="">Select assignee...</option>
                <option value="self">Assign to Self</option>
              </select>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Due Date</label>
                <input type="date" id="taskDueDate" class="form-input">
              </div>
              <div class="form-group">
                <label>Priority</label>
                <select id="taskPriority" class="form-select">
                  <option value="low">Low</option>
                  <option value="normal" selected>Normal</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                </select>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="cancelTaskBtn">Cancel</button>
            <button class="btn btn-primary" id="saveTaskBtn">Create Task</button>
          </div>
        </div>
      </div>

      <!-- Delete Confirmation Modal -->
      <div class="modal-overlay" id="deleteModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Delete Lead</h4>
            <button class="modal-close" id="closeDeleteModal">&times;</button>
          </div>
          <div class="modal-body">
            <p class="confirm-text">Are you sure you want to delete this lead? This action cannot be undone.</p>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="cancelDeleteBtn">Cancel</button>
            <button class="btn btn-danger" id="confirmDeleteBtn">Delete</button>
          </div>
        </div>
      </div>

      <!-- Add Deal Modal -->
      <div class="modal-overlay action-modal" id="addDealModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Add Deal</h4>
            <button class="modal-close" id="closeAddDealModal">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>Revenue Category <span class="required">*</span></label>
              <select id="dealCategory" class="form-select">
                <option value="">Select category...</option>
              </select>
            </div>
            <div class="form-group">
              <label>Value</label>
              <input type="number" id="newDealValue" class="form-input" placeholder="0.00" step="0.01">
            </div>
            <div class="form-group">
              <label>Deal Date</label>
              <input type="date" id="newDealDate" class="form-input">
            </div>
            <div class="form-group">
              <label>Notes</label>
              <textarea id="newDealNotes" class="form-textarea" rows="2" placeholder="Deal notes..."></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="cancelAddDealBtn">Cancel</button>
            <button class="btn btn-primary" id="saveAddDealBtn">Create Deal</button>
          </div>
        </div>
      </div>

      <!-- Add Transaction Modal -->
      <div class="modal-overlay action-modal" id="addTxnModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Add Transaction</h4>
            <button class="modal-close" id="closeAddTxnModal">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>Amount <span class="required">*</span></label>
              <input type="number" id="txnAmount" class="form-input" placeholder="0.00" step="0.01">
            </div>
            <div class="form-group">
              <label>Transaction Date <span class="required">*</span></label>
              <input type="datetime-local" id="txnDate" class="form-input">
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Type</label>
                <select id="txnType" class="form-select">
                  <option value="advance">Advance</option>
                  <option value="partial" selected>Partial</option>
                  <option value="final">Final</option>
                  <option value="refund">Refund</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div class="form-group">
                <label>Payment Mode</label>
                <select id="txnMode" class="form-select">
                  <option value="cash">Cash</option>
                  <option value="upi">UPI</option>
                  <option value="neft">NEFT</option>
                  <option value="rtgs">RTGS</option>
                  <option value="cheque">Cheque</option>
                  <option value="card">Card</option>
                  <option value="dd">Demand Draft</option>
                  <option value="other">Other</option>
                </select>
              </div>
            </div>
            <div class="form-group">
              <label>Link to Deal</label>
              <select id="txnDeal" class="form-select">
                <option value="">No specific deal</option>
              </select>
            </div>
            <div class="form-group">
              <label>Reference Number</label>
              <input type="text" id="txnReference" class="form-input" placeholder="UTR / Cheque No / Ref...">
            </div>
            <div class="form-group">
              <label>Notes</label>
              <textarea id="txnNotes" class="form-textarea" rows="2" placeholder="Transaction notes..."></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="cancelAddTxnBtn">Cancel</button>
            <button class="btn btn-primary" id="saveAddTxnBtn">Record Transaction</button>
          </div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: 'My Leads', showBack: true });
    this.attachModalListeners();
  }

  private attachModalListeners(): void {
    // DC Protocol: Register global handler for PageHeader add button
    (window as any).__staffLeadsAddLead = () => this.showAddLeadModal();
    
    document.getElementById('closeDetailModal')?.addEventListener('click', () => this.hideModal('detailModal'));
    document.getElementById('closeFormModal')?.addEventListener('click', () => this.hideModal('leadFormModal'));
    document.getElementById('cancelFormBtn')?.addEventListener('click', () => this.hideModal('leadFormModal'));
    document.getElementById('saveLeadBtn')?.addEventListener('click', () => this.saveLead());

    document.getElementById('closeFollowupModal')?.addEventListener('click', () => this.hideModal('followupModal'));
    document.getElementById('cancelFollowupBtn')?.addEventListener('click', () => this.hideModal('followupModal'));
    document.getElementById('saveFollowupBtn')?.addEventListener('click', () => this.saveFollowup());

    document.getElementById('closeStatusModal')?.addEventListener('click', () => this.hideModal('statusModal'));
    document.getElementById('cancelStatusBtn')?.addEventListener('click', () => this.hideModal('statusModal'));
    document.getElementById('saveStatusBtn')?.addEventListener('click', () => this.saveStatus());

    document.getElementById('closeActivityModal')?.addEventListener('click', () => this.hideModal('activityModal'));
    document.getElementById('cancelActivityBtn')?.addEventListener('click', () => this.hideModal('activityModal'));
    document.getElementById('saveActivityBtn')?.addEventListener('click', () => this.saveActivity());

    document.getElementById('closeNoteModal')?.addEventListener('click', () => this.hideModal('noteModal'));
    document.getElementById('cancelNoteBtn')?.addEventListener('click', () => this.hideModal('noteModal'));
    document.getElementById('saveNoteBtn')?.addEventListener('click', () => this.saveNote());

    document.getElementById('closeDealModal')?.addEventListener('click', () => this.hideModal('dealModal'));
    document.getElementById('cancelDealBtn')?.addEventListener('click', () => this.hideModal('dealModal'));
    document.getElementById('saveDealBtn')?.addEventListener('click', () => this.saveDealValue());

    document.getElementById('closeTaskModal')?.addEventListener('click', () => this.hideModal('taskModal'));
    document.getElementById('cancelTaskBtn')?.addEventListener('click', () => this.hideModal('taskModal'));
    document.getElementById('saveTaskBtn')?.addEventListener('click', () => this.createTask());

    document.getElementById('closeDeleteModal')?.addEventListener('click', () => this.hideModal('deleteModal'));
    document.getElementById('cancelDeleteBtn')?.addEventListener('click', () => this.hideModal('deleteModal'));
    document.getElementById('confirmDeleteBtn')?.addEventListener('click', () => this.deleteLead());

    document.getElementById('closeAddDealModal')?.addEventListener('click', () => this.hideModal('addDealModal'));
    document.getElementById('cancelAddDealBtn')?.addEventListener('click', () => this.hideModal('addDealModal'));
    document.getElementById('saveAddDealBtn')?.addEventListener('click', () => this.saveNewDeal());

    document.getElementById('closeAddTxnModal')?.addEventListener('click', () => this.hideModal('addTxnModal'));
    document.getElementById('cancelAddTxnBtn')?.addEventListener('click', () => this.hideModal('addTxnModal'));
    document.getElementById('saveAddTxnBtn')?.addEventListener('click', () => this.saveNewTransaction());

    document.getElementById('searchInput')?.addEventListener('input', (e) => {
      this.searchQuery = (e.target as HTMLInputElement).value.toLowerCase();
      this.updateContent();
    });

    document.querySelectorAll('.role-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        const role = tab.getAttribute('data-role');
        if (role) {
          this.activeRoleTab = role;
          document.querySelectorAll('.role-tab').forEach(t => t.classList.remove('active'));
          tab.classList.add('active');
          this.loadLeads();
        }
      });
    });

    document.getElementById('dateFrom')?.addEventListener('change', (e) => {
      this.dateFrom = (e.target as HTMLInputElement).value;
      this.loadLeads();
    });

    document.getElementById('dateTo')?.addEventListener('change', (e) => {
      this.dateTo = (e.target as HTMLInputElement).value;
      this.loadLeads();
    });

    document.getElementById('categoryFilter')?.addEventListener('change', (e) => {
      this.categoryFilter = (e.target as HTMLSelectElement).value;
      this.loadLeads();
    });

    document.getElementById('sourceFilter')?.addEventListener('change', (e) => {
      this.sourceFilter = (e.target as HTMLSelectElement).value;
      this.loadLeads();
    });

    // DC Protocol (Feb 2026): Quick filter listener
    document.getElementById('quickFilterSelect')?.addEventListener('change', (e) => {
      this.quickFilter = (e.target as HTMLSelectElement).value;
      this.loadLeads();
    });

    // DC Protocol (Feb 2026): Company filter listener
    document.getElementById('companyFilter')?.addEventListener('change', (e) => {
      const value = (e.target as HTMLSelectElement).value;
      this.selectedCompanyId = value ? parseInt(value) : null;
      this.loadLeads();
    });

    // DC Protocol (Feb 2026): Days since filter listener
    document.getElementById('submitDateFrom')?.addEventListener('change', (e) => {
      this.submitDateFrom = (e.target as HTMLInputElement).value;
      this.loadLeads();
    });
    document.getElementById('submitDateTo')?.addEventListener('change', (e) => {
      this.submitDateTo = (e.target as HTMLInputElement).value;
      this.loadLeads();
    });
    document.getElementById('completeDateFrom')?.addEventListener('change', (e) => {
      this.completeDateFrom = (e.target as HTMLInputElement).value;
      this.loadLeads();
    });
    document.getElementById('completeDateTo')?.addEventListener('change', (e) => {
      this.completeDateTo = (e.target as HTMLInputElement).value;
      this.loadLeads();
    });
    document.getElementById('dvrFromFilter')?.addEventListener('change', (e) => {
      this.dvrFrom = (e.target as HTMLInputElement).value;
      this.loadLeads();
    });
    document.getElementById('dvrToFilter')?.addEventListener('change', (e) => {
      this.dvrTo = (e.target as HTMLInputElement).value;
      this.loadLeads();
    });
    let _tcTimer: any; document.getElementById('telecallerCodeFilter')?.addEventListener('input', (e) => {
      clearTimeout(_tcTimer); _tcTimer = setTimeout(() => { this.telecallerCode = (e.target as HTMLInputElement).value.trim(); this.loadLeads(); }, 500);
    });
    let _fsTimer: any; document.getElementById('fieldStaffCodeFilter')?.addEventListener('input', (e) => {
      clearTimeout(_fsTimer); _fsTimer = setTimeout(() => { this.fieldStaffCode = (e.target as HTMLInputElement).value.trim(); this.loadLeads(); }, 500);
    });
    document.getElementById('daysSinceFilter')?.addEventListener('change', (e) => {
      this.daysSinceFilter = (e.target as HTMLSelectElement).value;
      this.loadLeads();
    });

    // DC Protocol: Add Lead button - use correct selector for PageHeader action button
    const addBtn = document.getElementById('headerActionBtn');
    if (addBtn) {
      addBtn.onclick = () => this.showAddLeadModal();
    }
  }

  private showModal(modalId: string): void {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.style.display = 'flex';
      if (modalId === 'leadFormModal') this.applyLeadFormStyles(modal);
    }
  }

  private hideModal(modalId: string): void {
    const modal = document.getElementById(modalId);
    if (modal) modal.style.display = 'none';
  }

  private applyLeadFormStyles(modal: HTMLElement): void {
    const content = modal.querySelector('.modal-content') as HTMLElement;
    if (content) {
      Object.assign(content.style, {
        maxHeight: '90vh', width: '100%', maxWidth: '420px',
        background: 'linear-gradient(180deg, #1e3a5f 0%, #0d1b2a 100%)',
        borderRadius: '20px', padding: '0', display: 'flex', flexDirection: 'column',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.5)'
      });
    }
    const header = modal.querySelector('.modal-header') as HTMLElement;
    if (header) {
      Object.assign(header.style, {
        background: 'linear-gradient(135deg, #10b981 0%, #047857 100%)',
        padding: '20px 24px', borderRadius: '20px 20px 0 0',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center'
      });
    }
    const headerTitle = modal.querySelector('.modal-header h4') as HTMLElement;
    if (headerTitle) {
      Object.assign(headerTitle.style, { margin: '0', color: 'white', fontSize: '20px', fontWeight: '700' });
    }
    const closeBtn = modal.querySelector('.modal-close') as HTMLElement;
    if (closeBtn) {
      Object.assign(closeBtn.style, {
        background: 'rgba(255, 255, 255, 0.2)', border: 'none', color: 'white',
        width: '36px', height: '36px', borderRadius: '10px', fontSize: '22px',
        cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center'
      });
    }
    const body = modal.querySelector('.modal-body') as HTMLElement;
    if (body) {
      Object.assign(body.style, { padding: '24px', overflowY: 'auto', flex: '1', maxHeight: 'calc(90vh - 180px)' });
    }
    modal.querySelectorAll('.section-title').forEach((el) => {
      Object.assign((el as HTMLElement).style, {
        fontSize: '12px', fontWeight: '600', color: '#10b981', textTransform: 'uppercase',
        letterSpacing: '1px', marginBottom: '12px', paddingBottom: '8px',
        borderBottom: '1px solid rgba(16, 185, 129, 0.2)'
      });
    });
    modal.querySelectorAll('.form-group').forEach((el) => {
      Object.assign((el as HTMLElement).style, { marginBottom: '16px' });
    });
    modal.querySelectorAll('.form-group label').forEach((el) => {
      Object.assign((el as HTMLElement).style, {
        display: 'flex', alignItems: 'center', gap: '6px', color: '#a8c0d8',
        fontSize: '13px', fontWeight: '500', marginBottom: '8px'
      });
    });
    modal.querySelectorAll('input, select, textarea').forEach((el) => {
      Object.assign((el as HTMLElement).style, {
        width: '100%', padding: '14px 16px', borderRadius: '12px',
        border: '2px solid rgba(255, 255, 255, 0.08)',
        background: 'rgba(13, 27, 42, 0.6)', color: '#e6f1ff', fontSize: '15px', boxSizing: 'border-box'
      });
    });
    modal.querySelectorAll('.form-row').forEach((el) => {
      Object.assign((el as HTMLElement).style, { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' });
    });
    const footer = modal.querySelector('.modal-footer') as HTMLElement;
    if (footer) {
      Object.assign(footer.style, {
        padding: '20px 24px', borderTop: '1px solid rgba(255, 255, 255, 0.08)',
        display: 'flex', gap: '12px', background: 'rgba(13, 27, 42, 0.5)', borderRadius: '0 0 20px 20px'
      });
    }
    const cancelBtn = modal.querySelector('.btn-secondary') as HTMLElement;
    if (cancelBtn) {
      Object.assign(cancelBtn.style, {
        flex: '1', padding: '16px 20px', background: 'rgba(255, 255, 255, 0.08)',
        border: '2px solid rgba(255, 255, 255, 0.15)', color: '#a8c0d8',
        borderRadius: '12px', fontSize: '15px', fontWeight: '600', cursor: 'pointer'
      });
    }
    const submitBtn = modal.querySelector('.btn-primary') as HTMLElement;
    if (submitBtn) {
      Object.assign(submitBtn.style, {
        flex: '1.5', padding: '16px 20px', background: 'linear-gradient(135deg, #10b981 0%, #047857 100%)',
        border: 'none', color: 'white', borderRadius: '12px', fontSize: '15px',
        fontWeight: '700', cursor: 'pointer', boxShadow: '0 4px 15px rgba(16, 185, 129, 0.35)'
      });
    }
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    const filtered = this.getFilteredLeads();
    const statuses = ['all', 'new', 'contacted', 'qualified', 'converted', 'lost'];
    const counts: Record<string, number> = { all: this.leads.length };
    statuses.slice(1).forEach(s => {
      counts[s] = this.leads.filter(l => l.status.toLowerCase() === s).length;
    });

    content.innerHTML = `
      <div class="leads-stats card">
        <div class="stats-row">
          <div class="stat-item">
            <span class="stat-value">${this.leads.length}</span>
            <span class="stat-label">Total</span>
          </div>
          <div class="stat-item">
            <span class="stat-value success">${counts.converted}</span>
            <span class="stat-label">Converted</span>
          </div>
          <div class="stat-item">
            <span class="stat-value warning">${counts.new + counts.contacted}</span>
            <span class="stat-label">Active</span>
          </div>
        </div>
      </div>

      <div class="filter-tabs status-filters">
        ${statuses.map(s => `
          <button class="tab ${this.activeStatusFilter === s ? 'active' : ''}" data-filter="${s}">
            ${s.charAt(0).toUpperCase() + s.slice(1)} (${counts[s] || 0})
          </button>
        `).join('')}
      </div>

      ${filtered.length > 0 ? `
        <div class="table-scroll-container">
          <table class="leads-table crm-table">
            <thead>
              <tr>
                <th class="sticky-col sortable" data-sort="name">Name ${this.getSortIcon('name')}</th>
                <th class="sortable" data-sort="phone">Mob ${this.getSortIcon('phone')}</th>
                <th class="sortable" data-sort="category">Cat ${this.getSortIcon('category')}</th>
                <th class="sortable" data-sort="source">Src ${this.getSortIcon('source')}</th>
                <th class="sortable" data-sort="status">Sts ${this.getSortIcon('status')}</th>
                <th class="sortable" data-sort="priority">Pri ${this.getSortIcon('priority')}</th>
                <th class="sortable" data-sort="handler">Hdlr ${this.getSortIcon('handler')}</th>
                <th class="sortable" data-sort="created_at">Date ${this.getSortIcon('created_at')}</th>
                <th class="sortable" data-sort="next_followup">F/Up ${this.getSortIcon('next_followup')}</th>
                <th class="sortable" data-sort="deal_value_total">Deal ${this.getSortIcon('deal_value_total')}</th>
                <th>Act</th>
              </tr>
            </thead>
            <tbody>
              ${filtered.map(lead => this.renderLeadRow(lead)).join('')}
            </tbody>
          </table>
        </div>
      ` : `
        <div class="empty-state card">
          <div class="empty-icon">👥</div>
          <p>No ${this.activeStatusFilter === 'all' ? '' : this.activeStatusFilter} leads</p>
        </div>
      `}
    `;

    document.querySelectorAll('.status-filters .tab').forEach(btn => {
      btn.addEventListener('click', () => {
        this.activeStatusFilter = btn.getAttribute('data-filter') || 'all';
        this.updateContent();
      });
    });

    // Sortable table headers
    document.querySelectorAll('.leads-table th.sortable').forEach(th => {
      th.addEventListener('click', () => {
        const column = th.getAttribute('data-sort');
        if (column) this.handleSort(column);
      });
    });

    document.querySelectorAll('.leads-table tbody tr').forEach(row => {
      row.addEventListener('click', (e) => {
        if ((e.target as HTMLElement).closest('.action-btn')) return;
        const leadId = row.getAttribute('data-id');
        if (leadId) this.showLeadDetails(parseInt(leadId));
      });
    });

    document.querySelectorAll('.action-btn.followup').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const leadId = parseInt(btn.getAttribute('data-id') || '0');
        const lead = this.leads.find(l => l.id === leadId);
        if (lead) { this.selectedLead = lead; this.showModal('followupModal'); }
      });
    });

    document.querySelectorAll('.action-btn.status').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const leadId = parseInt(btn.getAttribute('data-id') || '0');
        const lead = this.leads.find(l => l.id === leadId);
        if (lead) { this.selectedLead = lead; this.showModal('statusModal'); }
      });
    });
  }

  private renderLeadRow(lead: Lead): string {
    const statusClass = lead.status.toLowerCase().replace(' ', '-');
    const priorityClass = lead.priority?.toLowerCase() || 'normal';
    const created = new Date(lead.created_at).toLocaleDateString('en', { day: 'numeric', month: 'short', year: '2-digit' });
    const nextFollowup = lead.next_followup ? new Date(lead.next_followup).toLocaleDateString('en', { day: 'numeric', month: 'short' }) : '-';
    const dealValue = lead.deal_value_total ? `₹${lead.deal_value_total.toLocaleString()}` : '-';
    const phone = lead.phone || '';
    const whatsappNumber = phone.replace(/\D/g, '');

    return `
      <tr data-id="${lead.id}">
        <td class="sticky-col">
          <div class="lead-name-cell">
            <span class="lead-name">${lead.name}</span>
            <div class="lead-contact-links">
              <a href="tel:${phone}" class="mobile-link" onclick="event.stopPropagation()">${phone || '-'}</a>
              ${phone ? `<a href="https://wa.me/91${whatsappNumber}" class="whatsapp-link" target="_blank" onclick="event.stopPropagation()">💬</a>` : ''}
            </div>
          </div>
        </td>
        <td><span class="category-tag">${lead.category_name || lead.category || '-'}</span></td>
        <td>${lead.source || 'Direct'}</td>
        <td><span class="status-badge ${statusClass}">${lead.status}</span></td>
        <td><span class="priority-badge ${priorityClass}">${lead.priority || 'Normal'}</span></td>
        <td>${lead.handler_name || '-'}</td>
        <td>${created}</td>
        <td>${nextFollowup}</td>
        <td class="deal-value">${dealValue}</td>
        <td>
          <div class="action-btns">
            <a href="tel:${phone}" class="action-btn call" onclick="event.stopPropagation()">📞</a>
            <a href="https://wa.me/91${whatsappNumber}" class="action-btn whatsapp" target="_blank" onclick="event.stopPropagation()">💬</a>
            <button class="action-btn followup" data-id="${lead.id}" title="Follow-up">📅</button>
            <button class="action-btn edit" data-id="${lead.id}" title="Edit">✏️</button>
          </div>
        </td>
      </tr>
    `;
  }

  private renderLead(lead: Lead): string {
    const statusClass = lead.status.toLowerCase().replace(' ', '-');
    const priorityClass = lead.priority?.toLowerCase() || 'normal';
    const date = new Date(lead.created_at).toLocaleDateString('en', { day: 'numeric', month: 'short' });

    return `
      <div class="lead-card card" data-id="${lead.id}">
        <div class="lead-header">
          <div class="lead-info">
            <h4>${lead.name}</h4>
            <p class="lead-contact">${lead.phone}</p>
          </div>
          <div class="lead-badges">
            <span class="priority-badge ${priorityClass}">${lead.priority || 'Normal'}</span>
            <span class="status-badge ${statusClass}">${lead.status}</span>
          </div>
        </div>
        <div class="lead-meta">
          <span class="lead-category">${lead.category}</span>
          <span class="lead-source">${lead.source || 'Direct'}</span>
          <span class="lead-date">${date}</span>
        </div>
        ${lead.next_followup ? `
          <div class="followup-reminder">
            📅 Follow-up: ${new Date(lead.next_followup).toLocaleDateString('en', { day: 'numeric', month: 'short' })}
          </div>
        ` : ''}
      </div>
    `;
  }

  private async showLeadDetails(leadId: number): Promise<void> {
    const lead = this.leads.find(l => l.id === leadId);
    if (!lead) return;

    this.selectedLead = lead;
    const body = document.getElementById('detailBody');
    if (!body) return;

    const companyId = this.getLeadCompanyId(lead);
    this.leadDeals = [];
    this.leadTransactions = [];
    let callHistory: any[] = [];
    let callSummary: any = null;
    try {
      const [dealsResp, txnResp, callResp] = await Promise.all([
        apiService.get(`/crm/leads/${leadId}/deals?company_id=${companyId}`),
        apiService.get(`/crm/leads/${leadId}/transactions?company_id=${companyId}`),
        apiService.get(`/call-tracking/lead/${leadId}/calls?per_page=50`).catch(() => null)
      ]);
      if ((dealsResp.data as any)?.deals) this.leadDeals = (dealsResp.data as any).deals;
      else if (Array.isArray(dealsResp.data)) this.leadDeals = dealsResp.data as any[];
      if ((txnResp.data as any)?.transactions) this.leadTransactions = (txnResp.data as any).transactions;
      if (callResp) {
        callHistory = (callResp.data as any[]) || [];
        callSummary = (callResp as any).summary || null;
      }
    } catch (e) {
      console.warn('Failed to load deals/transactions', e);
    }

    const statusClass = lead.status.toLowerCase().replace(' ', '-');
    const priorityClass = lead.priority?.toLowerCase() || 'normal';

    body.innerHTML = `
      <div class="lead-detail-header">
        <div class="lead-avatar">${lead.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}</div>
        <div class="lead-title">
          <h3>${lead.name}</h3>
          <div class="lead-badges">
            <span class="priority-badge ${priorityClass}">${lead.priority || 'Normal'}</span>
            <span class="status-badge ${statusClass}">${lead.status}</span>
          </div>
        </div>
      </div>

      <!-- DC Protocol N001: VGK Member Status Banner (lazy-loaded) -->
      <div id="sl-mob-vgk-banner" style="margin:0 0 10px"></div>

      <div class="lead-contact-section">
        <a href="tel:${lead.phone}" class="contact-btn">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72"/>
          </svg>
          Call
        </a>
        ${lead.email ? `
          <a href="mailto:${lead.email}" class="contact-btn">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
              <polyline points="22,6 12,13 2,6"/>
            </svg>
            Email
          </a>
        ` : ''}
        <a href="https://wa.me/${lead.phone.replace(/[^0-9]/g, '')}" class="contact-btn" target="_blank">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
          </svg>
          WhatsApp
        </a>
      </div>

      <div class="lead-info-section card">
        <div class="info-row">
          <span class="info-label">Category</span>
          <span class="info-value">${lead.category}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Source</span>
          <span class="info-value">${lead.source || 'Direct'}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Created</span>
          <span class="info-value">${new Date(lead.created_at).toLocaleDateString('en', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
        </div>
        ${lead.email ? `
          <div class="info-row">
            <span class="info-label">Email</span>
            <span class="info-value">${lead.email}</span>
          </div>
        ` : ''}
        ${lead.address ? `
          <div class="info-row">
            <span class="info-label">Address</span>
            <span class="info-value">${lead.address}${lead.city ? `, ${lead.city}` : ''}</span>
          </div>
        ` : ''}
        ${lead.telecaller_name ? `
          <div class="info-row">
            <span class="info-label">Support</span>
            <span class="info-value">${lead.telecaller_name}</span>
          </div>
        ` : ''}
        ${lead.field_staff_name ? `
          <div class="info-row">
            <span class="info-label">Showroom</span>
            <span class="info-value">${lead.field_staff_name}</span>
          </div>
        ` : ''}
        ${lead.support_staff_name ? `
          <div class="info-row">
            <span class="info-label">Support Staff</span>
            <span class="info-value">${lead.support_staff_name}</span>
          </div>
        ` : ''}
        ${lead.technical_staff1_name ? `
          <div class="info-row">
            <span class="info-label">Tech Staff 1</span>
            <span class="info-value">${lead.technical_staff1_name}</span>
          </div>
        ` : ''}
        ${lead.technical_name ? `
          <div class="info-row">
            <span class="info-label">Tech Staff 2</span>
            <span class="info-value">${lead.technical_name}</span>
          </div>
        ` : ''}
        ${lead.guru_id ? `
          <div class="info-row">
            <span class="info-label">Senior</span>
            <span class="info-value">${lead.guru_name || lead.guru_id} <span style="color:#6b7280;font-size:11px">(${lead.guru_id})</span></span>
          </div>
        ` : ''}
        ${lead.z_guru_id ? `
          <div class="info-row">
            <span class="info-label">Extended</span>
            <span class="info-value">${lead.z_guru_name || lead.z_guru_id} <span style="color:#6b7280;font-size:11px">(${lead.z_guru_id})</span></span>
          </div>
        ` : ''}
      </div>

      ${lead.next_followup ? `
        <div class="followup-card card">
          <h5>📅 Next Follow-up</h5>
          <p>${new Date(lead.next_followup).toLocaleDateString('en', { weekday: 'long', day: 'numeric', month: 'long' })}</p>
        </div>
      ` : ''}

      ${lead.notes ? `
        <div class="notes-section card">
          <h5>Notes</h5>
          <p>${lead.notes}</p>
        </div>
      ` : ''}

      <div class="deals-revenue-section card">
        <div class="section-header-row">
          <h5>💰 Deals & Revenue</h5>
          <button class="btn btn-sm btn-outline" id="addDealBtnDetail">+ Deal</button>
        </div>
        <div class="revenue-summary">
          <div class="rev-stat">
            <span class="rev-label">Total</span>
            <span class="rev-value">₹${(lead.deal_value_total || 0).toLocaleString()}</span>
          </div>
          <div class="rev-stat">
            <span class="rev-label">Received</span>
            <span class="rev-value success">₹${(lead.deal_value_received || 0).toLocaleString()}</span>
          </div>
          <div class="rev-stat">
            <span class="rev-label">Balance</span>
            <span class="rev-value warning">₹${(lead.deal_value_balance || 0).toLocaleString()}</span>
          </div>
        </div>
        ${this.leadDeals.length > 0 ? `
          <div class="deals-list">
            ${this.leadDeals.map(d => `
              <div class="deal-card">
                <div class="deal-card-header">
                  <span class="deal-code">${d.deal_code || 'N/A'}</span>
                  <span class="deal-status-badge ${d.status}">${d.status}</span>
                </div>
                <div class="deal-card-body">
                  <span class="deal-cat">${d.category_name || 'Uncategorized'}</span>
                  <span class="deal-amt">₹${(d.deal_value_total || 0).toLocaleString()}</span>
                </div>
                ${d.deal_date ? `<div class="deal-card-date">${new Date(d.deal_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</div>` : ''}
              </div>
            `).join('')}
          </div>
        ` : '<p class="empty-hint">No deals yet</p>'}
      </div>

      <div class="transactions-section card">
        <div class="section-header-row">
          <h5>💳 Transactions</h5>
          <button class="btn btn-sm btn-outline" id="addTxnBtnDetail">+ Payment</button>
        </div>
        ${this.leadTransactions.length > 0 ? `
          <div class="txn-list">
            ${this.leadTransactions.map(t => `
              <div class="txn-row">
                <div class="txn-left">
                  <span class="txn-amount ${t.transaction_type === 'refund' ? 'refund' : ''}">
                    ${t.transaction_type === 'refund' ? '-' : '+'}₹${t.amount.toLocaleString()}
                  </span>
                  <span class="txn-meta">${t.transaction_type} · ${t.payment_mode}${t.reference_number ? ' · ' + t.reference_number : ''}</span>
                  <span class="txn-date">${new Date(t.transaction_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
                </div>
                <div class="txn-right">
                  <span class="validation-badge ${t.validation_status}">${t.validation_status}</span>
                </div>
              </div>
            `).join('')}
          </div>
        ` : '<p class="empty-hint">No transactions yet</p>'}
      </div>

      <div class="lead-actions-section">
        <div class="actions-row">
          <button class="btn btn-primary" id="editLeadBtn">✏️ Edit Lead</button>
          <button class="btn btn-secondary" id="updateStatusBtn">Update Status</button>
        </div>
        <div class="actions-row">
          <button class="btn btn-secondary" id="scheduleFollowupBtn">Follow-up</button>
          <button class="btn btn-secondary" id="logActivityBtn">Log Activity</button>
        </div>
        <div class="actions-row">
          <button class="btn btn-secondary" id="addNoteBtn">Add Note</button>
          <button class="btn btn-secondary" id="updateDealBtn">Value</button>
        </div>
        <div class="actions-row">
          <button class="btn btn-secondary" id="createTaskBtn">Create Task</button>
          <button class="btn btn-danger" id="deleteLeadBtn">Delete</button>
        </div>
      </div>

      ${lead.lead_notes && lead.lead_notes.length > 0 ? `
        <div class="notes-log-section">
          <h5>Notes</h5>
          ${lead.lead_notes.map(n => `
            <div class="note-item card">
              <p>${n.content}</p>
              <span class="note-meta">${n.created_by_name} • ${new Date(n.created_at).toLocaleDateString('en', { day: 'numeric', month: 'short' })}</span>
            </div>
          `).join('')}
        </div>
      ` : ''}

      ${lead.followups && lead.followups.length > 0 ? `
        <div class="followups-section">
          <h5>Follow-ups</h5>
          ${lead.followups.slice(0, 5).map(f => `
            <div class="followup-item ${f.status}">
              <div class="followup-date">${new Date(f.scheduled_date).toLocaleDateString('en', { day: 'numeric', month: 'short' })}</div>
              <div class="followup-info">
                <span class="followup-status">${f.status}</span>
                ${f.notes ? `<p>${f.notes}</p>` : ''}
              </div>
            </div>
          `).join('')}
        </div>
      ` : ''}

      <div class="call-history-section-mobile card">
        <h5>Call Records${callSummary ? ` (${callSummary.total_calls})` : ''}</h5>
        ${callSummary ? `
          <div class="call-summary-row">
            <span class="call-stat outgoing">↑ ${callSummary.outgoing || 0} Out</span>
            <span class="call-stat incoming">↓ ${callSummary.incoming || 0} In</span>
            <span class="call-stat missed">✕ ${callSummary.missed || 0} Missed</span>
            <span class="call-stat duration">${Math.floor((callSummary.total_duration_seconds || 0) / 60)}m</span>
          </div>
        ` : ''}
        ${callHistory.length === 0 ? '<p class="empty-hint">No call records found</p>' : `
          <div class="call-records-list">
            ${callHistory.map(c => {
              const dt = new Date(c.call_datetime);
              const dateStr = dt.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
              const timeStr = dt.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
              const mins = Math.floor((c.duration_seconds || 0) / 60);
              const secs = (c.duration_seconds || 0) % 60;
              const durationStr = c.duration_seconds > 0 ? `${mins}m ${secs}s` : '-';
              const typeClass = (c.call_type || '').toLowerCase();
              const typeLabel = c.call_type === 'OUTGOING' ? '↑ Out' : c.call_type === 'INCOMING' ? '↓ In' : c.call_type === 'MISSED' ? '✕ Missed' : c.call_type || '-';
              return `
                <div class="call-record-item">
                  <div class="call-record-left">
                    <span class="call-type-badge ${typeClass}">${typeLabel}</span>
                    <div class="call-record-info">
                      <span class="call-agent-name">${c.staff_name || 'Unknown'}</span>
                      <span class="call-record-meta">${dateStr} ${timeStr} · ${durationStr}</span>
                    </div>
                  </div>
                  <div class="call-record-right">
                    ${c.has_recording && c.recording_id ? `
                      <span class="recording-badge synced" title="Recording synced">
                        <span class="rec-icon">●</span> Synced
                      </span>
                      <button class="btn btn-xs btn-outline play-recording-btn" data-recording-id="${c.recording_id}">▶</button>
                    ` : `
                      <span class="recording-badge not-synced" title="No recording">
                        <span class="rec-icon">○</span> No Rec
                      </span>
                    `}
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        `}
      </div>

      ${lead.activities && lead.activities.length > 0 ? `
        <div class="activity-log-section">
          <h5>Activity Log</h5>
          ${lead.activities.map(a => `
            <div class="activity-item">
              <div class="activity-icon">${this.getActivityIcon(a.type)}</div>
              <div class="activity-content">
                <p>${a.description}</p>
                <span class="activity-meta">${a.created_by} • ${new Date(a.created_at).toLocaleDateString('en', { day: 'numeric', month: 'short' })}</span>
              </div>
            </div>
          `).join('')}
        </div>
      ` : ''}
    `;

    // DC Protocol N001: lazy-load VGK banner (non-blocking, 200ms after render)
    setTimeout(() => vgkBannerService.load(leadId, companyId, 'sl-mob-vgk-banner'), 200);

    document.getElementById('editLeadBtn')?.addEventListener('click', () => this.showEditLeadModal(lead));
    document.getElementById('updateStatusBtn')?.addEventListener('click', () => {
      (document.getElementById('newStatus') as HTMLSelectElement).value = lead.status.toLowerCase();
      this.showModal('statusModal');
    });
    document.getElementById('scheduleFollowupBtn')?.addEventListener('click', () => this.showModal('followupModal'));
    document.getElementById('logActivityBtn')?.addEventListener('click', () => this.showModal('activityModal'));
    document.getElementById('addNoteBtn')?.addEventListener('click', () => {
      (document.getElementById('noteContent') as HTMLTextAreaElement).value = '';
      this.showModal('noteModal');
    });
    document.getElementById('updateDealBtn')?.addEventListener('click', () => {
      (document.getElementById('dealTotal') as HTMLInputElement).value = (lead.deal_value_total || '').toString();
      (document.getElementById('dealReceived') as HTMLInputElement).value = (lead.deal_value_received || '').toString();
      // DC-CFV-EDIT-001: show confirmed final override input for MR10001/MR10025 only
      const _cfvAuthState = authService.getAuthState();
      const _cfvEmpCode = (_cfvAuthState?.user as any)?.emp_code || '';
      const _cfvGroup = document.getElementById('cfvOverrideGroup');
      const _cfvInput = document.getElementById('dealConfirmedFinal') as HTMLInputElement;
      if (_cfvGroup) _cfvGroup.style.display = ['MR10001','MR10025'].includes(_cfvEmpCode) ? '' : 'none';
      if (_cfvInput) _cfvInput.value = lead.confirmed_final_value != null ? lead.confirmed_final_value.toString() : '';
      this.showModal('dealModal');
    });
    document.getElementById('createTaskBtn')?.addEventListener('click', () => {
      (document.getElementById('taskTitle') as HTMLInputElement).value = `Follow-up: ${lead.name}`;
      (document.getElementById('taskDescription') as HTMLTextAreaElement).value = `Lead: ${lead.name}\nMobile: ${lead.phone}\nCategory: ${lead.category}`;
      this.showModal('taskModal');
    });
    document.getElementById('deleteLeadBtn')?.addEventListener('click', () => this.showModal('deleteModal'));

    document.getElementById('addDealBtnDetail')?.addEventListener('click', () => this.showAddDealModal());
    document.getElementById('addTxnBtnDetail')?.addEventListener('click', () => this.showAddTransactionModal());

    document.querySelectorAll('.play-recording-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const recId = btn.getAttribute('data-recording-id');
        if (recId) this.playCallRecording(parseInt(recId), btn as HTMLElement);
      });
    });

    this.showModal('detailModal');
  }

  private getActivityIcon(type: string): string {
    const icons: Record<string, string> = {
      call: '📞', email: '📧', meeting: '🤝', whatsapp: '💬', site_visit: '🏠', note: '📝'
    };
    return icons[type] || '📋';
  }

  private playCallRecording(recordingId: number, btnEl: HTMLElement): void {
    const existingPlayer = document.getElementById('mobileAudioPlayer');
    if (existingPlayer) existingPlayer.remove();

    const container = btnEl.closest('.call-record-item');
    if (!container) return;

    const playerDiv = document.createElement('div');
    playerDiv.id = 'mobileAudioPlayer';
    playerDiv.className = 'audio-player-inline';
    playerDiv.innerHTML = `
      <audio controls autoplay style="width:100%;height:36px;" src="/api/v1/call-tracking/recordings/${recordingId}/stream">
        Your browser does not support audio playback.
      </audio>
      <button class="btn btn-xs btn-outline close-player-btn" onclick="document.getElementById('mobileAudioPlayer')?.remove()">✕</button>
    `;
    container.after(playerDiv);
  }

  private getSortIcon(column: string): string {
    if (this.sortColumn !== column) return '<span class="sort-icon">↕</span>';
    return this.sortDirection === 'asc' 
      ? '<span class="sort-icon active">↑</span>' 
      : '<span class="sort-icon active">↓</span>';
  }

  private handleSort(column: string): void {
    if (this.sortColumn === column) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortColumn = column;
      this.sortDirection = 'asc';
    }
    this.updateContent();
  }

  private sortLeads(leads: Lead[]): Lead[] {
    return [...leads].sort((a, b) => {
      let valA: any, valB: any;
      
      switch (this.sortColumn) {
        case 'name': valA = a.name?.toLowerCase() || ''; valB = b.name?.toLowerCase() || ''; break;
        case 'phone': valA = a.phone || ''; valB = b.phone || ''; break;
        case 'category': valA = a.category?.toLowerCase() || ''; valB = b.category?.toLowerCase() || ''; break;
        case 'source': valA = a.source?.toLowerCase() || ''; valB = b.source?.toLowerCase() || ''; break;
        case 'status': valA = a.status?.toLowerCase() || ''; valB = b.status?.toLowerCase() || ''; break;
        case 'priority': 
          const priorityOrder = { urgent: 4, high: 3, normal: 2, low: 1 };
          valA = priorityOrder[a.priority?.toLowerCase() as keyof typeof priorityOrder] || 0;
          valB = priorityOrder[b.priority?.toLowerCase() as keyof typeof priorityOrder] || 0;
          break;
        case 'handler': valA = a.handler_name?.toLowerCase() || ''; valB = b.handler_name?.toLowerCase() || ''; break;
        case 'created_at': valA = new Date(a.created_at || 0).getTime(); valB = new Date(b.created_at || 0).getTime(); break;
        case 'next_followup': valA = new Date(a.next_followup || 0).getTime(); valB = new Date(b.next_followup || 0).getTime(); break;
        case 'deal_value_total': valA = a.deal_value_total || 0; valB = b.deal_value_total || 0; break;
        default: valA = 0; valB = 0;
      }
      
      if (valA < valB) return this.sortDirection === 'asc' ? -1 : 1;
      if (valA > valB) return this.sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }

  private showAddLeadModal(): void {
    this.selectedLead = null;
    (document.getElementById('leadFormTitle') as HTMLElement).textContent = 'Add New Lead';
    (document.getElementById('leadName') as HTMLInputElement).value = '';
    (document.getElementById('leadMobile') as HTMLInputElement).value = '';
    (document.getElementById('leadEmail') as HTMLInputElement).value = '';
    (document.getElementById('leadCategory') as HTMLSelectElement).value = '';
    (document.getElementById('leadPriority') as HTMLSelectElement).value = 'normal';
    (document.getElementById('leadSource') as HTMLSelectElement).value = '';
    (document.getElementById('leadAddress') as HTMLTextAreaElement).value = '';
    (document.getElementById('leadNotes') as HTMLTextAreaElement).value = '';
    (document.getElementById('saveLeadBtn') as HTMLButtonElement).textContent = 'Create Lead';
    const mnrInput = document.getElementById('leadMnrHandlerId') as HTMLInputElement;
    const guruInput = document.getElementById('leadGuruId') as HTMLInputElement;
    const nsSearch = document.getElementById('leadNetworkSearch') as HTMLInputElement;
    const nsSelected = document.getElementById('leadNetworkSelected') as HTMLElement;
    const nsGuruRow = document.getElementById('leadGuruRow') as HTMLElement;
    if (mnrInput) mnrInput.value = '';
    if (guruInput) guruInput.value = '';
    if (nsSearch) nsSearch.value = '';
    if (nsSelected) nsSelected.style.display = 'none';
    if (nsGuruRow) nsGuruRow.style.display = 'none';
    this.showModal('leadFormModal');
    this.attachPincodeLookup();
    this.setupNetworkAssignment();
  }

  private attachPincodeLookup(): void {
    const pincodeInput = document.getElementById('leadPincode') as HTMLInputElement;
    if (pincodeInput) {
      pincodeInput.addEventListener('input', () => {
        if (pincodeInput.value.length === 6) {
          this.lookupPincode(pincodeInput);
        }
      });
    }
  }

  private setupNetworkAssignment(): void {
    const searchInput = document.getElementById('leadNetworkSearch') as HTMLInputElement;
    const dropdown = document.getElementById('leadNetworkDropdown') as HTMLElement;
    const handlerIdInput = document.getElementById('leadMnrHandlerId') as HTMLInputElement;
    const guruIdInput = document.getElementById('leadGuruId') as HTMLInputElement;
    const selectedBox = document.getElementById('leadNetworkSelected') as HTMLElement;
    const selectedText = document.getElementById('leadNetworkSelectedText') as HTMLElement;
    const guruRow = document.getElementById('leadGuruRow') as HTMLElement;
    const guruName = document.getElementById('leadGuruName') as HTMLElement;
    const clearBtn = document.getElementById('leadNetworkClearBtn') as HTMLButtonElement;

    if (!searchInput) return;

    let debounceTimer: ReturnType<typeof setTimeout>;

    searchInput.addEventListener('input', () => {
      const q = searchInput.value.trim();
      clearTimeout(debounceTimer);
      if (q.length < 2) { dropdown.style.display = 'none'; dropdown.innerHTML = ''; return; }
      debounceTimer = setTimeout(async () => {
        try {
          const res = await apiService.get(`/crm/network-search?type=mnr&q=${encodeURIComponent(q)}`);
          const items: any[] = res.results || res.data || [];
          if (!items.length) {
            dropdown.innerHTML = '<div style="padding: 12px 16px; color: #a8c0d8; font-size: 13px;">No results found</div>';
          } else {
            dropdown.innerHTML = items.map(item => `
              <div class="ns-item" data-id="${item.id}" data-name="${item.name}" data-type="${item.type}" data-sponsor-id="${item.sponsor_id || ''}" data-sponsor-name="${item.sponsor_name || ''}" style="padding: 12px 16px; cursor: pointer; border-bottom: 1px solid rgba(255,255,255,0.06); display: flex; gap: 10px; align-items: center;">
                <span style="background: ${item.type === 'vgk' ? '#7c3aed' : '#0ea5e9'}; color: white; font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 6px;">${(item.type || 'MNR').toUpperCase()}</span>
                <span style="color: #e6f1ff; font-size: 14px;">${item.display || item.name}</span>
              </div>`).join('');
            dropdown.querySelectorAll('.ns-item').forEach(el => {
              el.addEventListener('click', () => {
                const id = (el as HTMLElement).dataset.id!;
                const name = (el as HTMLElement).dataset.name!;
                const type = (el as HTMLElement).dataset.type!;
                const sId = (el as HTMLElement).dataset.sponsorId || '';
                const sName = (el as HTMLElement).dataset.sponsorName || '';
                handlerIdInput.value = id;
                searchInput.value = '';
                dropdown.style.display = 'none';
                dropdown.innerHTML = '';
                selectedText.textContent = `${type.toUpperCase()} ${id} — ${name}`;
                selectedBox.style.display = 'block';
                if (sId) {
                  guruIdInput.value = sId;
                  guruName.textContent = `${sId}${sName ? ' — ' + sName : ''}`;
                  guruRow.style.display = 'block';
                } else {
                  guruIdInput.value = '';
                  guruRow.style.display = 'none';
                }
              });
            });
          }
          dropdown.style.display = 'block';
        } catch { dropdown.style.display = 'none'; }
      }, 350);
    });

    document.addEventListener('click', (e) => {
      if (!searchInput.contains(e.target as Node) && !dropdown.contains(e.target as Node)) {
        dropdown.style.display = 'none';
      }
    }, { once: false });

    clearBtn?.addEventListener('click', () => {
      handlerIdInput.value = '';
      guruIdInput.value = '';
      searchInput.value = '';
      selectedBox.style.display = 'none';
      guruRow.style.display = 'none';
    });
  }

  private showEditLeadModal(lead: Lead): void {
    this.selectedLead = lead;
    (document.getElementById('leadFormTitle') as HTMLElement).textContent = 'Edit Lead';
    (document.getElementById('leadName') as HTMLInputElement).value = lead.name || '';
    (document.getElementById('leadMobile') as HTMLInputElement).value = lead.phone || '';
    (document.getElementById('leadEmail') as HTMLInputElement).value = lead.email || '';
    (document.getElementById('leadCategory') as HTMLSelectElement).value = lead.category_id?.toString() || lead.category || '';
    (document.getElementById('leadPriority') as HTMLSelectElement).value = lead.priority?.toLowerCase() || 'normal';
    (document.getElementById('leadSource') as HTMLSelectElement).value = lead.source || '';
    (document.getElementById('leadAddress') as HTMLTextAreaElement).value = lead.address || '';
    (document.getElementById('leadNotes') as HTMLTextAreaElement).value = lead.notes || '';
    (document.getElementById('saveLeadBtn') as HTMLButtonElement).textContent = 'Update Lead';
    // DC-VGK-BRAND-INCENTIVE-001: populate solar brand dropdown if Solar category
    const isSolarLead = (lead.category || '').toLowerCase().includes('solar');
    const solarBrandSection = document.getElementById('solarBrandSection') as HTMLElement;
    if (solarBrandSection) solarBrandSection.style.display = isSolarLead ? 'block' : 'none';
    const solarBrandSel = document.getElementById('leadSolarBrandId') as HTMLSelectElement;
    if (isSolarLead && solarBrandSel && solarBrandSel.options.length <= 1) {
      apiService.get<{success:boolean;brands?:{id:number;brand_name:string}[]}>('/vgk/brands?active_only=true').then(r => {
        if (r.data?.brands) {
          r.data.brands.forEach(b => {
            const o = document.createElement('option');
            o.value = String(b.id);
            o.textContent = b.brand_name;
            solarBrandSel.appendChild(o);
          });
          solarBrandSel.value = lead.solar_brand_id ? String(lead.solar_brand_id) : '';
        }
      }).catch(() => {/* non-fatal */});
    } else if (isSolarLead && solarBrandSel) {
      solarBrandSel.value = lead.solar_brand_id ? String(lead.solar_brand_id) : '';
    }
    const mnrInput = document.getElementById('leadMnrHandlerId') as HTMLInputElement;
    const guruInput = document.getElementById('leadGuruId') as HTMLInputElement;
    const nsSearch = document.getElementById('leadNetworkSearch') as HTMLInputElement;
    const nsSelected = document.getElementById('leadNetworkSelected') as HTMLElement;
    const nsSelectedText = document.getElementById('leadNetworkSelectedText') as HTMLElement;
    const nsGuruRow = document.getElementById('leadGuruRow') as HTMLElement;
    const nsGuruName = document.getElementById('leadGuruName') as HTMLElement;
    if (mnrInput) mnrInput.value = lead.mnr_handler_id || '';
    if (guruInput) guruInput.value = lead.guru_id || '';
    if (nsSearch) nsSearch.value = '';
    if (nsSelected && lead.mnr_handler_id) {
      nsSelectedText.textContent = `${lead.mnr_handler_id}${lead.mnr_handler_name ? ' — ' + lead.mnr_handler_name : ''}`;
      nsSelected.style.display = 'block';
      if (lead.guru_id && nsGuruRow) {
        nsGuruName.textContent = `${lead.guru_id}${lead.guru_name ? ' — ' + lead.guru_name : ''}`;
        nsGuruRow.style.display = 'block';
      } else if (nsGuruRow) {
        nsGuruRow.style.display = 'none';
      }
    } else if (nsSelected) {
      nsSelected.style.display = 'none';
      if (nsGuruRow) nsGuruRow.style.display = 'none';
    }
    this.hideModal('detailModal');
    this.showModal('leadFormModal');
    this.attachPincodeLookup();
    this.setupNetworkAssignment();
  }

  private async saveLead(): Promise<void> {
    // Get all form field values
    const name = (document.getElementById('leadName') as HTMLInputElement).value.trim();
    const phone = (document.getElementById('leadMobile') as HTMLInputElement).value.trim();
    const email = (document.getElementById('leadEmail') as HTMLInputElement).value.trim();
    const categoryId = (document.getElementById('leadCategory') as HTMLSelectElement).value;
    const priority = (document.getElementById('leadPriority') as HTMLSelectElement).value;
    const source = (document.getElementById('leadSource') as HTMLSelectElement).value;
    const address = (document.getElementById('leadAddress') as HTMLTextAreaElement)?.value?.trim();
    const description = (document.getElementById('leadNotes') as HTMLTextAreaElement)?.value?.trim();
    const phonePrimaryWhatsapp = (document.getElementById('leadPhoneWhatsapp') as HTMLInputElement)?.checked;
    const alternatePhone = (document.getElementById('leadMobileSecondary') as HTMLInputElement)?.value?.trim();
    const phoneSecondaryWhatsapp = (document.getElementById('leadPhoneSecondaryWhatsapp') as HTMLInputElement)?.checked;
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
      alert('Please fill required fields: Name, Mobile');
      return;
    }

    if (phone.length !== 10 || !/^\d{10}$/.test(phone)) {
      alert('Please enter a valid 10-digit mobile number');
      return;
    }

    const isEditing = this.selectedLead !== null;
    const btn = document.getElementById('saveLeadBtn') as HTMLButtonElement;
    if (btn) { btn.disabled = true; btn.textContent = isEditing ? 'Updating...' : 'Creating...'; }

    try {
      // DC Protocol (Feb 2026): Use selected company if available, otherwise fall back to user's base company
      const { authService } = await import('../services/auth.service');
      const authState = authService.getAuthState();
      const user = authState?.user;
      const companyId = this.selectedCompanyId ?? (user?.company_id || user?.base_company_id || 1);
      
      // Build payload with correct API field names matching LeadCreate schema
      const payload: any = {
        name,
        phone,  // API expects 'phone' not 'mobile'
        email: email || null,
        category_id: categoryId ? parseInt(categoryId) : null,
        priority: priority || 'medium',
        status: 'new',
        description: description || null,  // API expects 'description' not 'notes'
        source: source || 'staff_app',
        phone_primary_whatsapp: phonePrimaryWhatsapp || false,
        alternate_phone: alternatePhone || null,
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
        tags: tags || null,
        company_id: companyId,
        mnr_handler_id: (document.getElementById('leadMnrHandlerId') as HTMLInputElement)?.value || null,
        guru_id: (document.getElementById('leadGuruId') as HTMLInputElement)?.value || null,
        solar_brand_id: (() => { const v = (document.getElementById('leadSolarBrandId') as HTMLSelectElement)?.value; return v ? parseInt(v) || null : null; })()
      };

      // DC-DEDUP-002: Pre-flight duplicate phone check for new lead creation
      if (!isEditing && (phone || alternatePhone)) {
        try {
          const dupParams = new URLSearchParams({ company_id: String(companyId) });
          if (phone) dupParams.append('phone', phone);
          if (alternatePhone) dupParams.append('alt_phone', alternatePhone);
          const dupCheck = await apiService.get<any>(`/crm/leads/check-duplicate?${dupParams}`);
          if (dupCheck && dupCheck.duplicate) {
            const dLead = dupCheck.lead || {};
            const dOwner = dupCheck.owner;
            const dActive = dupCheck.owner_active !== false;
            const dOwnerName = (dOwner && dOwner.name) || 'Unassigned';
            const dLeadId = dLead.id || '';
            const dLeadName = dLead.name || 'Unnamed';
            if (dActive) {
              alert(`⚠️ Duplicate Mobile Found\n\nLead #${dLeadId} — ${dLeadName}\nAssigned to: ${dOwnerName} (Active)\n\nYou cannot create a duplicate lead for an active employee's contact.`);
            } else {
              alert(`⚠️ Duplicate Mobile Found\n\nLead #${dLeadId} — ${dLeadName}\nAssigned to: ${dOwnerName} (INACTIVE)\n\nOpen the web app to view and reassign this lead to an active staff member.`);
            }
            return;
          }
        } catch (dupErr) {
          console.warn('[DC-DEDUP-002] Mobile duplicate pre-check skipped:', dupErr);
        }
      }

      // DC-HCI-001: If editing and the ground source partner may have changed,
      // preview income correction entries and confirm before saving.
      if (isEditing && this.selectedLead?.associated_partner_id) {
        const _hciNewHandler = (document.getElementById('leadMnrHandlerId') as HTMLInputElement)?.value || null;
        const _hciOldHandler = this.selectedLead.mnr_handler_id;
        const _hciNewPartner = (document.getElementById('leadAssociatedPartnerId') as HTMLInputElement)?.value || null;
        const _hciOldPartner = String(this.selectedLead.associated_partner_id || '');
        const _partnerChanged = _hciNewPartner && _hciNewPartner !== _hciOldPartner && _hciOldPartner;
        const _handlerChanged = _hciNewHandler && _hciNewHandler !== _hciOldHandler && _hciOldPartner;
        if (_partnerChanged || _handlerChanged) {
          try {
            const _hciPreview = await apiService.get<any>(
              `/crm/leads/${this.selectedLead.id}/income-correction-preview?company_id=${companyId}`
            );
            if (_hciPreview?.data?.has_entries) {
              const _pd = _hciPreview.data;
              const _cancelCount = (_pd.cancellable || []).length;
              const _paidCount = (_pd.adjustable_paid || []).length;
              let _msg = `⚠️ Ground Source Change\n\nThis will trigger income correction for Lead #${this.selectedLead.id}:\n`;
              if (_cancelCount) _msg += `• ${_cancelCount} entr${_cancelCount === 1 ? 'y' : 'ies'} will be CANCELLED (wallet reversed)\n`;
              if (_paidCount) _msg += `• ${_paidCount} PAID entr${_paidCount === 1 ? 'y' : 'ies'} → ADJUSTMENT entries\n`;
              _msg += `\nProceed?`;
              const _confirmed = confirm(_msg);
              if (!_confirmed) return;
            }
          } catch (_hciErr) {
            console.warn('[DC-HCI-001] Mobile preview check skipped:', _hciErr);
          }
        }
      }

      let response;
      if (isEditing) {
        response = await apiService.put(`/crm/unified-my-leads/${this.selectedLead!.id}/full-update`, payload);
      } else {
        response = await apiService.post('/crm/unified-my-leads', payload);
      }

      if (response.success) {
        alert(isEditing ? 'Lead updated successfully!' : 'Lead created successfully!');
        this.hideModal('leadFormModal');
        await this.loadLeads();
      } else {
        alert(response.error || (isEditing ? 'Failed to update lead' : 'Failed to create lead'));
      }
    } catch (error: any) {
      alert(error.message || (isEditing ? 'Failed to update lead' : 'Failed to create lead'));
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = isEditing ? 'Update Lead' : 'Create Lead'; }
    }
  }

  private async saveFollowup(): Promise<void> {
    if (!this.selectedLead) return;

    const date = (document.getElementById('followupDate') as HTMLInputElement).value;
    const time = (document.getElementById('followupTime') as HTMLInputElement).value;
    const notes = (document.getElementById('followupNotes') as HTMLTextAreaElement).value.trim();

    if (!date) {
      alert('Please select a follow-up date');
      return;
    }

    const btn = document.getElementById('saveFollowupBtn') as HTMLButtonElement;
    if (btn) { btn.disabled = true; btn.textContent = 'Scheduling...'; }

    try {
      const response = await apiService.post(`/crm/leads/${this.selectedLead.id}/followup`, {
        followup_date: date,
        followup_time: time || null,
        notes: notes || null
      });

      if (response.success) {
        alert('Follow-up scheduled!');
        this.hideModal('followupModal');
        await this.loadLeads();
        this.hideModal('detailModal');
      } else {
        alert(response.error || 'Failed to schedule follow-up');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to schedule follow-up');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'Schedule'; }
    }
  }

  private async saveStatus(): Promise<void> {
    if (!this.selectedLead) return;

    const status = (document.getElementById('newStatus') as HTMLSelectElement).value;
    const remarks = (document.getElementById('statusRemarks') as HTMLTextAreaElement).value.trim();

    const btn = document.getElementById('saveStatusBtn') as HTMLButtonElement;
    if (btn) { btn.disabled = true; btn.textContent = 'Updating...'; }

    try {
      const response = await apiService.put(`/crm/leads/${this.selectedLead.id}`, {
        status,
        status_remarks: remarks || null
      });

      if (response.success) {
        alert('Status updated!');
        this.hideModal('statusModal');
        await this.loadLeads();
        this.hideModal('detailModal');
      } else {
        alert(response.error || 'Failed to update status');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to update status');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'Update Status'; }
    }
  }

  private async saveActivity(): Promise<void> {
    if (!this.selectedLead) return;

    const type = (document.getElementById('activityType') as HTMLSelectElement).value;
    const description = (document.getElementById('activityDescription') as HTMLTextAreaElement).value.trim();

    if (!description) {
      alert('Please enter activity description');
      return;
    }

    const btn = document.getElementById('saveActivityBtn') as HTMLButtonElement;
    if (btn) { btn.disabled = true; btn.textContent = 'Logging...'; }

    try {
      const response = await apiService.post(`/crm/leads/${this.selectedLead.id}/activity`, {
        activity_type: type,
        description
      });

      if (response.success) {
        alert('Activity logged!');
        this.hideModal('activityModal');
        await this.loadLeads();
        this.showLeadDetails(this.selectedLead.id);
      } else {
        alert(response.error || 'Failed to log activity');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to log activity');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'Log Activity'; }
    }
  }

  private async saveNote(): Promise<void> {
    if (!this.selectedLead) return;

    const content = (document.getElementById('noteContent') as HTMLTextAreaElement).value.trim();

    if (!content) {
      alert('Please enter note content');
      return;
    }

    const btn = document.getElementById('saveNoteBtn') as HTMLButtonElement;
    if (btn) { btn.disabled = true; btn.textContent = 'Saving...'; }

    try {
      const response = await apiService.post(`/crm/leads/${this.selectedLead.id}/notes`, {
        content
      });

      if (response.success) {
        alert('Note added!');
        this.hideModal('noteModal');
        await this.loadLeads();
        this.showLeadDetails(this.selectedLead.id);
      } else {
        alert(response.error || 'Failed to add note');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to add note');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'Save Note'; }
    }
  }

  private async saveDealValue(): Promise<void> {
    if (!this.selectedLead) return;

    const total = parseFloat((document.getElementById('dealTotal') as HTMLInputElement).value) || 0;
    const received = parseFloat((document.getElementById('dealReceived') as HTMLInputElement).value) || 0;

    const btn = document.getElementById('saveDealBtn') as HTMLButtonElement;
    if (btn) { btn.disabled = true; btn.textContent = 'Updating...'; }

    try {
      // DC-CFV-EDIT-001: include confirmed_final_value override for MR10001/MR10025
      const _svAuthState = authService.getAuthState();
      const _svEmpCode = (_svAuthState?.user as any)?.emp_code || '';
      const _cfvInEl = document.getElementById('dealConfirmedFinal') as HTMLInputElement;
      const _cfvVal = _cfvInEl?.value !== '' ? parseFloat(_cfvInEl?.value || '') : null;
      const _cfvPayload = (['MR10001','MR10025'].includes(_svEmpCode) && !isNaN(_cfvVal as number) && _cfvVal !== null)
        ? { confirmed_final_value: _cfvVal } : {};
      // DC-TXN-DEAL-SYNC-001 (Jun 2026): deal_value_received is derived server-side from
      // validated transactions — do not send from client to prevent overwrite.
      const response = await apiService.put(`/crm/leads/${this.selectedLead.id}`, {
        deal_value_total: total,
        ..._cfvPayload
      });

      if (response.success) {
        alert('Deal value updated!');
        this.hideModal('dealModal');
        await this.loadLeads();
        this.showLeadDetails(this.selectedLead.id);
      } else {
        alert(response.error || 'Failed to update deal value');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to update deal value');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'Update'; }
    }
  }

  private async createTask(): Promise<void> {
    if (!this.selectedLead) return;

    const title = (document.getElementById('taskTitle') as HTMLInputElement).value.trim();
    const description = (document.getElementById('taskDescription') as HTMLTextAreaElement).value.trim();
    const dueDate = (document.getElementById('taskDueDate') as HTMLInputElement).value;
    const priority = (document.getElementById('taskPriority') as HTMLSelectElement).value;

    if (!title) {
      alert('Please enter task title');
      return;
    }

    const btn = document.getElementById('saveTaskBtn') as HTMLButtonElement;
    if (btn) { btn.disabled = true; btn.textContent = 'Creating...'; }

    try {
      const response = await apiService.post(`/crm/leads/${this.selectedLead.id}/create-task`, {
        title,
        description: description || null,
        due_date: dueDate || null,
        priority
      });

      if (response.success) {
        alert('Task created successfully!');
        this.hideModal('taskModal');
        this.hideModal('detailModal');
      } else {
        alert(response.error || 'Failed to create task');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to create task');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'Create Task'; }
    }
  }

  private async deleteLead(): Promise<void> {
    if (!this.selectedLead) return;

    const btn = document.getElementById('confirmDeleteBtn') as HTMLButtonElement;
    if (btn) { btn.disabled = true; btn.textContent = 'Deleting...'; }

    try {
      const response = await apiService.delete(`/crm/leads/${this.selectedLead.id}`);

      if (response.success) {
        alert('Lead deleted!');
        this.hideModal('deleteModal');
        this.hideModal('detailModal');
        await this.loadLeads();
      } else {
        alert(response.error || 'Failed to delete lead');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to delete lead');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'Delete'; }
    }
  }

  private getLeadCompanyId(lead?: Lead | null): number {
    const l = lead || this.selectedLead;
    if (l?.company_id) return l.company_id;
    if (this.selectedCompanyId) return this.selectedCompanyId;
    const authState = authService.getAuthState();
    const user = authState?.user as any;
    return user?.company_id || user?.base_company_id || 1;
  }

  private async loadRevenueCategories(companyId: number): Promise<void> {
    try {
      const resp = await apiService.get(`/signup-categories/list?company_id=${companyId}`);
      if ((resp.data as any)?.categories) this.revenueCategories = (resp.data as any).categories;
      else if (Array.isArray(resp.data)) this.revenueCategories = resp.data as any[];
      else this.revenueCategories = [];
    } catch {
      this.revenueCategories = [];
    }
  }

  private async showAddDealModal(): Promise<void> {
    if (!this.selectedLead) return;
    const companyId = this.getLeadCompanyId();
    await this.loadRevenueCategories(companyId);

    const catSelect = document.getElementById('dealCategory') as HTMLSelectElement;
    if (catSelect) {
      catSelect.innerHTML = '<option value="">Select category...</option>' +
        this.revenueCategories.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
    }
    (document.getElementById('newDealValue') as HTMLInputElement).value = '';
    (document.getElementById('newDealDate') as HTMLInputElement).value = new Date().toISOString().split('T')[0];
    (document.getElementById('newDealNotes') as HTMLTextAreaElement).value = '';
    this.showModal('addDealModal');
  }

  private async showAddTransactionModal(): Promise<void> {
    if (!this.selectedLead) return;

    const dealSelect = document.getElementById('txnDeal') as HTMLSelectElement;
    if (dealSelect) {
      dealSelect.innerHTML = '<option value="">No specific deal</option>' +
        this.leadDeals.map(d => `<option value="${d.id}">${d.deal_code} - ${d.category_name || 'Deal'} (₹${d.deal_value_total.toLocaleString()})</option>`).join('');
    }
    (document.getElementById('txnAmount') as HTMLInputElement).value = '';
    const now = new Date();
    const localISO = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    (document.getElementById('txnDate') as HTMLInputElement).value = localISO;
    (document.getElementById('txnType') as HTMLSelectElement).value = 'partial';
    (document.getElementById('txnMode') as HTMLSelectElement).value = 'cash';
    (document.getElementById('txnReference') as HTMLInputElement).value = '';
    (document.getElementById('txnNotes') as HTMLTextAreaElement).value = '';
    this.showModal('addTxnModal');
  }

  private async saveNewDeal(): Promise<void> {
    if (!this.selectedLead) return;

    const categoryId = (document.getElementById('dealCategory') as HTMLSelectElement).value;
    const dealValue = parseFloat((document.getElementById('newDealValue') as HTMLInputElement).value) || 0;
    const dealDate = (document.getElementById('newDealDate') as HTMLInputElement).value;
    const notes = (document.getElementById('newDealNotes') as HTMLTextAreaElement).value.trim();

    if (!categoryId) {
      alert('Please select a revenue category');
      return;
    }

    const btn = document.getElementById('saveAddDealBtn') as HTMLButtonElement;
    if (btn) { btn.disabled = true; btn.textContent = 'Creating...'; }

    const companyId = this.getLeadCompanyId();
    try {
      const response = await apiService.post(`/crm/leads/${this.selectedLead.id}/deals?company_id=${companyId}`, {
        revenue_category_id: parseInt(categoryId),
        deal_value_total: dealValue,
        deal_value_received: 0,
        deal_date: dealDate || null,
        notes: notes || null,
        company_id: companyId
      });

      if (response.success !== false) {
        alert('Deal created!');
        this.hideModal('addDealModal');
        await this.loadLeads();
        await this.showLeadDetails(this.selectedLead.id);
      } else {
        alert(response.error || 'Failed to create deal');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to create deal');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'Create Deal'; }
    }
  }

  private async saveNewTransaction(): Promise<void> {
    if (!this.selectedLead) return;

    const amount = parseFloat((document.getElementById('txnAmount') as HTMLInputElement).value);
    const txnDate = (document.getElementById('txnDate') as HTMLInputElement).value;
    const txnType = (document.getElementById('txnType') as HTMLSelectElement).value;
    const txnMode = (document.getElementById('txnMode') as HTMLSelectElement).value;
    const dealId = (document.getElementById('txnDeal') as HTMLSelectElement).value;
    const reference = (document.getElementById('txnReference') as HTMLInputElement).value.trim();
    const notes = (document.getElementById('txnNotes') as HTMLTextAreaElement).value.trim();

    if (!amount || amount <= 0) {
      alert('Please enter a valid amount');
      return;
    }
    if (!txnDate) {
      alert('Please select a transaction date');
      return;
    }

    const btn = document.getElementById('saveAddTxnBtn') as HTMLButtonElement;
    if (btn) { btn.disabled = true; btn.textContent = 'Recording...'; }

    const companyId = this.getLeadCompanyId();
    try {
      const payload: any = {
        transaction_date: new Date(txnDate).toISOString(),
        amount,
        transaction_type: txnType,
        payment_mode: txnMode,
        reference_number: reference || null,
        notes: notes || null,
        deal_id: dealId ? parseInt(dealId) : null
      };

      const response = await apiService.post(`/crm/leads/${this.selectedLead.id}/transactions?company_id=${companyId}`, payload);

      if (response.success !== false) {
        alert((response.data as any)?.message || response.error || 'Transaction recorded!');
        this.hideModal('addTxnModal');
        await this.loadLeads();
        await this.showLeadDetails(this.selectedLead.id);
      } else {
        alert(response.error || 'Failed to record transaction');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to record transaction');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'Record Transaction'; }
    }
  }
}
