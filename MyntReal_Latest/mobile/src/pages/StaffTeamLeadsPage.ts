/**
 * Staff Team Leads Page
 * DC Protocol: DC_MOBILE_STAFF_TEAM_LEADS_001
 * Full web parity with Primary Owner/Handler sections, filters, bulk actions, and data table
 */

import { apiService } from '../services/api.service';
import { authService } from '../services/auth.service';
import { PageHeader } from '../components/PageHeader';
import { routerService } from '../services/router.service';
import { vgkBannerService } from '../services/vgk-banner.service';

interface Company {
  id: number;
  company_code: string;
  company_name: string;
}

interface TeamMember {
  id: number;
  emp_code: string;
  full_name: string;
}

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
  source: string | null;
  status: string;
  priority: string;
  company_name?: string;
  created_at: string;
  updated_at?: string;
  completed_at?: string | null;
  last_interacted_at: string | null;
  next_followup: string | null;
  primary_owner_name: string | null;
  telecaller_name: string | null;
  field_staff_name: string | null;
  handler_name: string | null;
  deal_value: number;
  deal_value_total: number;
  deal_value_received: number;
  deal_value_balance: number;
  days_since_created: number;
  role_type?: string;
  address?: string | null;
  area?: string | null;
  city?: string | null;
  state?: string | null;
  pincode?: string | null;
  requirements?: string | null;
  looking_for?: string | null;
  budget_min?: number | null;
  budget_max?: number | null;
  notes?: string | null;
  mnr_handler_id?: string | null;
  mnr_handler_name?: string | null;
  guru_id?: string | null;
  guru_name?: string | null;
  confirmed_final_value?: number | null;
}

interface OwnerStats {
  total: number;
  new: number;
  progress: number;
  won: number;
  lost: number;
  on_hold: number;
  revenue: number;
  collected: number;
  balance: number;
}

interface LeadSourceStats {
  company_leads_count: number;
  self_leads_count: number;
}

interface FilterTab {
  id: string;
  label: string;
  count: number;
}

const LEAD_STATUSES = ['new', 'contacted', 'qualified', 'proposal', 'negotiation', 'won', 'lost', 'on_hold'];
const LEAD_PRIORITIES = ['low', 'normal', 'high', 'urgent'];
const LEAD_CATEGORIES = ['EV', 'Real Estate', 'Insurance', 'MNR', 'Other'];
const QUICK_FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'today', label: "Today's Leads" },
  { id: 'overdue', label: 'Overdue' },
  { id: 'followup_today', label: 'Follow-up Today' },
  { id: 'this_week', label: 'This Week' },
  { id: 'future', label: 'Future Leads' },
  { id: 'no_followup', label: 'No Followup' }
];
const ROLE_FILTERS = [
  { id: '', label: 'All Roles' },
  { id: 'primary_holder', label: 'As Primary Holder' },
  { id: 'handler', label: 'As Handler' }
];
const DAYS_SINCE_OPTIONS = [
  { id: '', label: 'Days Since: All' },
  { id: 'lt6', label: 'Less than 6 days' },
  { id: '6-15', label: '6-15 days' },
  { id: '15-30', label: '15-30 days' },
  { id: 'gt30', label: 'Above 30 days' }
];

export class StaffTeamLeadsPage {
  private container: HTMLElement;
  private loading: boolean = true;
  private leads: Lead[] = [];
  private companies: Company[] = [];
  private teamMembers: TeamMember[] = [];
  
  private selectedCompanyId: number | null = null;
  private selectedMemberId: number | null = null;
  private empStatus: string = 'all';
  private handlerSearch: string = '';
  private activeFilterTab: string = 'all';
  
  private startDate: string = '';
  private endDate: string = '';
  private searchQuery: string = '';
  private statusFilter: string = '';
  private priorityFilter: string = '';
  private categoryFilter: string = '';
  private quickFilter: string = 'all';
  private daysSinceFilter: string = '';
  private roleFilter: string = '';
  private telecallerFilter: string = '';
  private fieldStaffFilter: string = '';
  
  private asOwnerStats: OwnerStats = { total: 0, new: 0, progress: 0, won: 0, lost: 0, on_hold: 0, revenue: 0, collected: 0, balance: 0 };
  private asHandlerStats: OwnerStats = { total: 0, new: 0, progress: 0, won: 0, lost: 0, on_hold: 0, revenue: 0, collected: 0, balance: 0 };
  private leadSourceStats: LeadSourceStats = { company_leads_count: 0, self_leads_count: 0 };
  
  private filterTabs: FilterTab[] = [
    { id: 'all', label: 'All My Leads', count: 0 },
    { id: 'telecaller', label: 'As Telecaller', count: 0 },
    { id: 'field_staff', label: 'As Field Staff', count: 0 },
    { id: 'mnr_handler', label: 'As MNR Handler', count: 0 },
    { id: 'fresh', label: 'Fresh Leads', count: 0 },
    { id: 'self', label: 'Self Leads', count: 0 }
  ];
  
  private selectedLeads: number[] = [];
  private selectedLead: Lead | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadFiltersData();
    await this.loadTeamLeads();
  }

  private async loadFiltersData(): Promise<void> {
    try {
      // DC Protocol (Feb 2026): Use correct CRM endpoints
      const companiesRes = await apiService.get<any>('/crm/my-companies');
      const respAny = companiesRes as any;
      if (companiesRes.success) {
        this.companies = respAny.companies || companiesRes.data?.companies || companiesRes.data || [];
      }
      // Team members will be loaded from team-leads response
    } catch (error) {
      console.error('[StaffTeamLeads] Failed to load filters:', error);
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
      console.error('[StaffTeamLeads] Pincode lookup failed:', error);
    }
  }

  private async loadTeamLeads(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const params = new URLSearchParams();
      // DC Protocol: company_id is optional - if null, API returns all companies
      if (this.selectedCompanyId) params.append('company_id', this.selectedCompanyId.toString());
      if (this.selectedMemberId) params.append('team_member_id', this.selectedMemberId.toString());
      params.append('emp_status', this.empStatus);
      if (this.activeFilterTab !== 'all') params.append('role_filter', this.activeFilterTab);
      if (this.startDate) params.append('start_date', this.startDate);
      if (this.endDate) params.append('end_date', this.endDate);
      if (this.searchQuery) params.append('search', this.searchQuery);
      if (this.statusFilter) params.append('status', this.statusFilter);
      if (this.priorityFilter) params.append('priority', this.priorityFilter);
      if (this.categoryFilter) params.append('category', this.categoryFilter);
      // DC Protocol (Feb 2026): Add quick filter, days since filter, role filter and handler search
      if (this.quickFilter && this.quickFilter !== 'all') params.append('quick_filter', this.quickFilter);
      if (this.daysSinceFilter) params.append('days_since', this.daysSinceFilter);
      if (this.roleFilter) params.append('role_filter', this.roleFilter);
      if (this.handlerSearch) params.append('handler_search', this.handlerSearch);
      
      const response = await apiService.get<any>(`/crm/team-leads?${params.toString()}`);
      if (response.success && response.data) {
        // DC Protocol (Feb 2026): API returns nested data structure
        // data: { leads: [...], team_members: [...], as_owner_stats: {...}, as_handler_stats: {...}, tab_counts: {...}, pagination: {...} }
        const data = response.data;
        
        // Extract leads from nested structure
        let rawLeads = Array.isArray(data.leads) ? data.leads : (Array.isArray(data) ? data : []);
        // Client-side telecaller / field staff filter
        if (this.telecallerFilter) rawLeads = rawLeads.filter((l: any) => (l.telecaller_name || '').toLowerCase().includes(this.telecallerFilter));
        if (this.fieldStaffFilter) rawLeads = rawLeads.filter((l: any) => (l.field_staff_name || '').toLowerCase().includes(this.fieldStaffFilter));
        this.leads = rawLeads;
        
        // Parse stats from nested data
        if (data.as_owner_stats) {
          this.asOwnerStats = data.as_owner_stats;
        }
        if (data.as_handler_stats) {
          this.asHandlerStats = data.as_handler_stats;
        }
        
        // Parse team members from nested data
        if (data.team_members && Array.isArray(data.team_members)) {
          this.teamMembers = data.team_members;
        }
        
        // Parse tab counts
        const tabCounts = data.tab_counts || {};
        this.filterTabs = this.filterTabs.map(tab => ({
          ...tab,
          count: tabCounts[tab.id] || 0
        }));
        
        // Lead source stats
        this.leadSourceStats = {
          company_leads_count: data.pagination?.total || this.leads.length,
          self_leads_count: tabCounts.self || 0
        };
      }
    } catch (error) {
      console.error('[StaffTeamLeads] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Team Leads', showBack: true, rightAction: { icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>', onClick: () => (window as any).__teamLeadsAddLead?.() } })}
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
      
      <!-- Bulk Actions Modal -->
      <div class="modal-overlay" id="bulkModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Bulk Actions</h4>
            <button class="modal-close" id="closeBulkModal">&times;</button>
          </div>
          <div class="modal-body">
            <p class="selected-count"><span id="selectedCount">0</span> leads selected</p>
            <div class="bulk-actions-grid">
              <button class="bulk-action-btn" data-action="reassign">
                <span class="bulk-icon">👤</span>
                <span>Reassign</span>
              </button>
              <button class="bulk-action-btn" data-action="status">
                <span class="bulk-icon">📋</span>
                <span>Change Status</span>
              </button>
              <button class="bulk-action-btn" data-action="priority">
                <span class="bulk-icon">⚡</span>
                <span>Change Priority</span>
              </button>
            </div>
          </div>
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

      <!-- Add/Edit Lead Modal - Enhanced Design (Feb 2026) -->
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
            <button class="modal-close" id="closeLeadFormModal" style="background: rgba(255, 255, 255, 0.2); border: none; color: white; width: 36px; height: 36px; border-radius: 10px; font-size: 22px; cursor: pointer; display: flex; align-items: center; justify-content: center;">&times;</button>
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
                    ${LEAD_CATEGORIES.map(c => `<option value="${c}">${c}</option>`).join('')}
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
                  <option value="Self Lead">Self Lead</option>
                  <option value="Direct">Direct</option>
                  <option value="Referral">Referral</option>
                  <option value="Website">Website</option>
                  <option value="Social Media">Social Media</option>
                  <option value="Cold Call">Cold Call</option>
                </select>
              </div>
            </div>
            
            <div class="form-section" style="margin-bottom: 20px;">
              <div class="section-title" style="font-size: 12px; font-weight: 600; color: #10b981; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid rgba(16, 185, 129, 0.2);">Additional Details</div>
              <div class="form-group" style="margin-bottom: 16px;">
                <label style="display: flex; align-items: center; gap: 6px; color: #a8c0d8; font-size: 13px; font-weight: 500; margin-bottom: 8px;">Address</label>
                <textarea id="leadAddress" class="form-textarea" rows="2" placeholder="Full address" style="width: 100%; padding: 14px 16px; border-radius: 12px; border: 2px solid rgba(255, 255, 255, 0.08); background: rgba(13, 27, 42, 0.6) !important; color: #e6f1ff !important; font-size: 15px; box-sizing: border-box; resize: vertical; min-height: 70px;"></textarea>
              </div>
              <div class="form-group" style="margin-bottom: 16px;">
                <label style="display: flex; align-items: center; gap: 6px; color: #a8c0d8; font-size: 13px; font-weight: 500; margin-bottom: 8px;">Notes</label>
                <textarea id="leadNotes" class="form-textarea" rows="2" placeholder="Additional notes or requirements..." style="width: 100%; padding: 14px 16px; border-radius: 12px; border: 2px solid rgba(255, 255, 255, 0.08); background: rgba(13, 27, 42, 0.6) !important; color: #e6f1ff !important; font-size: 15px; box-sizing: border-box; resize: vertical; min-height: 70px;"></textarea>
              </div>
            </div>

            <div class="form-section" style="margin-bottom: 20px;">
              <div class="section-title" style="font-size: 12px; font-weight: 600; color: #8b5cf6; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid rgba(139, 92, 246, 0.2);">Network Assignment (Optional)</div>
              <div class="form-group" style="margin-bottom: 12px; position: relative;">
                <label style="display: flex; align-items: center; gap: 6px; color: #a8c0d8; font-size: 13px; font-weight: 500; margin-bottom: 8px;">MNR/VGK Handler</label>
                <input type="text" id="leadNetworkSearch" class="form-input" placeholder="Search by MNR/VGK ID or name..." autocomplete="off" style="width: 100%; padding: 14px 16px; border-radius: 12px; border: 2px solid rgba(139, 92, 246, 0.3); background: rgba(13, 27, 42, 0.6) !important; color: #e6f1ff !important; font-size: 15px; box-sizing: border-box;">
                <input type="hidden" id="leadMnrHandlerId">
                <input type="hidden" id="leadGuruId">
                <div id="leadNetworkDropdown" style="display: none; position: absolute; top: 100%; left: 0; right: 0; background: #1a2f4a; border: 1px solid rgba(139, 92, 246, 0.4); border-radius: 10px; max-height: 180px; overflow-y: auto; z-index: 200; margin-top: 4px; box-shadow: 0 8px 24px rgba(0,0,0,0.4);"></div>
              </div>
              <div id="leadNetworkSelected" style="display: none; background: rgba(139, 92, 246, 0.1); border: 1px solid rgba(139, 92, 246, 0.3); border-radius: 10px; padding: 10px 14px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <span id="leadNetworkSelectedText" style="color: #c4b5fd; font-weight: 600; font-size: 14px;"></span>
                  <button id="leadNetworkClearBtn" style="background: none; border: none; color: #f87171; cursor: pointer; font-size: 20px; line-height: 1; padding: 0 4px;">×</button>
                </div>
                <div id="leadGuruRow" style="display: none; color: #a8c0d8; font-size: 12px; margin-top: 4px;">Guru: <span id="leadGuruName" style="color: #93c5fd;"></span></div>
              </div>
            </div>
          </div>
          <div class="modal-footer" style="padding: 20px 24px; border-top: 1px solid rgba(255, 255, 255, 0.08); display: flex; gap: 12px; background: rgba(13, 27, 42, 0.5); border-radius: 0 0 20px 20px;">
            <button class="btn btn-secondary" id="cancelLeadFormBtn" style="flex: 1; padding: 16px 20px; background: rgba(255, 255, 255, 0.08); border: 2px solid rgba(255, 255, 255, 0.15); color: #a8c0d8; border-radius: 12px; font-size: 15px; font-weight: 600; cursor: pointer;">Cancel</button>
            <button class="btn btn-primary" id="saveLeadBtn" style="flex: 1.5; padding: 16px 20px; background: linear-gradient(135deg, #10b981 0%, #047857 100%); border: none; color: white; border-radius: 12px; font-size: 15px; font-weight: 700; cursor: pointer; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.35);">Create Lead</button>
          </div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: 'Team Leads', showBack: true });
    this.attachModalListeners();
  }

  private attachModalListeners(): void {
    // DC Protocol: Register global handler for PageHeader add button
    (window as any).__teamLeadsAddLead = () => this.showAddLeadModal();
    
    document.getElementById('closeBulkModal')?.addEventListener('click', () => this.hideModal('bulkModal'));
    document.getElementById('closeDetailModal')?.addEventListener('click', () => this.hideModal('detailModal'));
    document.getElementById('closeLeadFormModal')?.addEventListener('click', () => this.hideModal('leadFormModal'));
    document.getElementById('cancelLeadFormBtn')?.addEventListener('click', () => this.hideModal('leadFormModal'));
    document.getElementById('saveLeadBtn')?.addEventListener('click', () => this.saveLead());
    
    document.querySelectorAll('.bulk-action-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const action = btn.getAttribute('data-action');
        if (action) this.handleBulkAction(action);
      });
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
    });

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
    // DC Protocol (Feb 2026): Use category name string to match select options
    (document.getElementById('leadCategory') as HTMLSelectElement).value = lead.category || '';
    (document.getElementById('leadPriority') as HTMLSelectElement).value = lead.priority?.toLowerCase() || 'normal';
    (document.getElementById('leadSource') as HTMLSelectElement).value = lead.source || '';
    (document.getElementById('leadAddress') as HTMLTextAreaElement).value = lead.address || '';
    (document.getElementById('leadNotes') as HTMLTextAreaElement).value = lead.notes || '';
    (document.getElementById('saveLeadBtn') as HTMLButtonElement).textContent = 'Update Lead';
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
      // DC Protocol (Feb 2026): Get company_id - use selected company or user's base company
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
        description: description || null,
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
        guru_id: (document.getElementById('leadGuruId') as HTMLInputElement)?.value || null
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

      let response;
      if (isEditing) {
        response = await apiService.put(`/crm/unified-my-leads/${this.selectedLead!.id}/full-update`, payload);
      } else {
        response = await apiService.post('/crm/unified-my-leads', payload);
      }
      
      if (response.success) {
        alert(isEditing ? 'Lead updated successfully!' : 'Lead created successfully!');
        this.hideModal('leadFormModal');
        await this.loadTeamLeads();
      } else {
        alert(response.error || (isEditing ? 'Failed to update lead' : 'Failed to create lead'));
      }
    } catch (error: any) {
      alert(error.message || (isEditing ? 'Failed to update lead' : 'Failed to create lead'));
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = isEditing ? 'Update Lead' : 'Create Lead'; }
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

    content.innerHTML = `
      <div class="team-leads-page">
        <!-- Top Filters -->
        <div class="top-filters card">
          <div class="filter-row">
            <div class="filter-item">
              <label>Company</label>
              <select id="companyFilter" class="form-select">
                <option value="" ${!this.selectedCompanyId ? 'selected' : ''}>All Companies</option>
                ${this.companies.map(c => 
                  `<option value="${c.id}" ${c.id === this.selectedCompanyId ? 'selected' : ''}>${c.company_name}</option>`
                ).join('')}
              </select>
            </div>
            <div class="filter-item">
              <label>Team Member</label>
              <select id="memberFilter" class="form-select">
                <option value="">All Team Members</option>
                ${this.teamMembers.map(m => 
                  `<option value="${m.id}" ${m.id === this.selectedMemberId ? 'selected' : ''}>${m.full_name}</option>`
                ).join('')}
              </select>
            </div>
          </div>
          <div class="filter-row">
            <div class="filter-item">
              <label>Start Date</label>
              <input type="date" id="startDateFilter" class="form-input" value="${this.startDate}">
            </div>
            <div class="filter-item">
              <label>End Date</label>
              <input type="date" id="endDateFilter" class="form-input" value="${this.endDate}">
            </div>
          </div>
          <div class="filter-row">
            <div class="filter-item">
              <label>Quick Filter</label>
              <select id="quickFilterSelect" class="form-select">
                ${QUICK_FILTERS.map(f => 
                  `<option value="${f.id}" ${this.quickFilter === f.id ? 'selected' : ''}>${f.label}</option>`
                ).join('')}
              </select>
            </div>
            <div class="filter-item">
              <label>Role Filter</label>
              <select id="roleFilterSelect" class="form-select">
                ${ROLE_FILTERS.map(f => 
                  `<option value="${f.id}" ${this.roleFilter === f.id ? 'selected' : ''}>${f.label}</option>`
                ).join('')}
              </select>
            </div>
            <div class="filter-item">
              <label>Category</label>
              <select id="categoryFilterSelect" class="form-select">
                <option value="" ${!this.categoryFilter ? 'selected' : ''}>All Categories</option>
                ${LEAD_CATEGORIES.map(c => 
                  `<option value="${c}" ${this.categoryFilter === c ? 'selected' : ''}>${c}</option>`
                ).join('')}
              </select>
            </div>
          </div>
          <div class="filter-row">
            <div class="filter-item">
              <label>Team Filter</label>
              <select id="empStatusFilter" class="form-select">
                <option value="all" ${this.empStatus === 'all' ? 'selected' : ''}>All (Self + Team)</option>
                <option value="active_with_leads" ${this.empStatus === 'active_with_leads' ? 'selected' : ''}>Active + With Leads</option>
                <option value="active" ${this.empStatus === 'active' ? 'selected' : ''}>Active Only</option>
              </select>
            </div>
            <div class="filter-item">
              <label>Days Since</label>
              <select id="daysSinceFilter" class="form-select">
                ${DAYS_SINCE_OPTIONS.map(d => 
                  `<option value="${d.id}" ${this.daysSinceFilter === d.id ? 'selected' : ''}>${d.label}</option>`
                ).join('')}
              </select>
            </div>
          </div>
          <div class="filter-row">
            <div class="filter-item full-width">
              <label>Handler Search</label>
              <input type="text" id="handlerSearch" class="form-input" placeholder="MNR/Partner ID..." value="${this.handlerSearch}">
            </div>
          </div>
          <div class="filter-row">
            <div class="filter-item">
              <label>🎤 Tele Caller</label>
              <input type="text" id="telecallerFilterInput" class="form-input" placeholder="Name..." value="${this.telecallerFilter}">
            </div>
            <div class="filter-item">
              <label>👤 Field Staff</label>
              <input type="text" id="fieldStaffFilterInput" class="form-input" placeholder="Name..." value="${this.fieldStaffFilter}">
            </div>
          </div>
        </div>

        <!-- Filter Tabs -->
        <div class="filter-tabs-scroll">
          ${this.filterTabs.map(tab => `
            <button class="filter-tab ${this.activeFilterTab === tab.id ? 'active' : ''}" data-tab="${tab.id}">
              ${tab.label} <span class="tab-count">${tab.count}</span>
            </button>
          `).join('')}
        </div>

        <!-- Lead Source Stats - DC Protocol (Feb 2026): Web-Mobile Parity -->
        <div class="lead-source-stats">
          <div class="source-stat company-stat">
            <span class="source-icon">🏢</span>
            <span class="source-value">${this.leadSourceStats.company_leads_count}</span>
            <span class="source-label">Company Leads</span>
          </div>
          <div class="source-stat self-stat">
            <span class="source-icon">👤</span>
            <span class="source-value">${this.leadSourceStats.self_leads_count}</span>
            <span class="source-label">Self Leads</span>
          </div>
        </div>

        <!-- Stats Sections -->
        <div class="stats-sections">
          <!-- As Primary Owner -->
          <div class="stats-section owner-section">
            <div class="stats-header">As Primary Owner</div>
            <div class="stats-row">
              <div class="stat-item"><span class="stat-val">${this.asOwnerStats.total}</span><span class="stat-lbl">Total</span></div>
              <div class="stat-item"><span class="stat-val">${this.asOwnerStats.new}</span><span class="stat-lbl">New</span></div>
              <div class="stat-item"><span class="stat-val">${this.asOwnerStats.progress}</span><span class="stat-lbl">Progress</span></div>
              <div class="stat-item"><span class="stat-val success">${this.asOwnerStats.won}</span><span class="stat-lbl">Won</span></div>
              <div class="stat-item"><span class="stat-val danger">${this.asOwnerStats.lost}</span><span class="stat-lbl">Lost</span></div>
              <div class="stat-item"><span class="stat-val warning">${this.asOwnerStats.on_hold}</span><span class="stat-lbl">On Hold</span></div>
            </div>
            <div class="stats-row revenue-row">
              <div class="stat-item"><span class="stat-val currency">₹${this.formatCurrency(this.asOwnerStats.revenue)}</span><span class="stat-lbl">Revenue</span></div>
              <div class="stat-item"><span class="stat-val currency success">₹${this.formatCurrency(this.asOwnerStats.collected)}</span><span class="stat-lbl">Collected</span></div>
              <div class="stat-item"><span class="stat-val currency warning">₹${this.formatCurrency(this.asOwnerStats.balance)}</span><span class="stat-lbl">Balance</span></div>
            </div>
          </div>

          <!-- As Handler -->
          <div class="stats-section handler-section">
            <div class="stats-header">As Handler (TC/FS/MNR)</div>
            <div class="stats-row">
              <div class="stat-item"><span class="stat-val">${this.asHandlerStats.total}</span><span class="stat-lbl">Total</span></div>
              <div class="stat-item"><span class="stat-val">${this.asHandlerStats.new}</span><span class="stat-lbl">New</span></div>
              <div class="stat-item"><span class="stat-val">${this.asHandlerStats.progress}</span><span class="stat-lbl">Progress</span></div>
              <div class="stat-item"><span class="stat-val success">${this.asHandlerStats.won}</span><span class="stat-lbl">Won</span></div>
              <div class="stat-item"><span class="stat-val danger">${this.asHandlerStats.lost}</span><span class="stat-lbl">Lost</span></div>
              <div class="stat-item"><span class="stat-val warning">${this.asHandlerStats.on_hold}</span><span class="stat-lbl">On Hold</span></div>
            </div>
            <div class="stats-row revenue-row">
              <div class="stat-item"><span class="stat-val currency">₹${this.formatCurrency(this.asHandlerStats.revenue)}</span><span class="stat-lbl">Revenue</span></div>
              <div class="stat-item"><span class="stat-val currency success">₹${this.formatCurrency(this.asHandlerStats.collected)}</span><span class="stat-lbl">Collected</span></div>
              <div class="stat-item"><span class="stat-val currency warning">₹${this.formatCurrency(this.asHandlerStats.balance)}</span><span class="stat-lbl">Balance</span></div>
            </div>
          </div>
        </div>

        <!-- Bulk Actions Bar -->
        ${this.selectedLeads.length > 0 ? `
          <div class="bulk-actions-bar card">
            <span>${this.selectedLeads.length} leads selected</span>
            <div class="bulk-btns">
              <button class="btn btn-sm btn-secondary" id="clearSelection">Clear</button>
              <button class="btn btn-sm btn-primary" id="showBulkActions">Actions</button>
            </div>
          </div>
        ` : ''}

        <!-- Leads Table Section -->
        <div class="leads-section card">
          <div class="section-header">
            <h4>All Leads</h4>
            <div class="header-actions">
              <button class="btn btn-sm btn-success" id="addLeadBtn">+ Add Lead</button>
            </div>
          </div>

          <!-- Search & Filters -->
          <div class="table-filters">
            <div class="search-row">
              <input type="text" id="searchInput" class="form-input" placeholder="Search name/phone/pincode..." value="${this.searchQuery}">
            </div>
            <div class="filter-row">
              <select id="statusFilter" class="form-select">
                <option value="">All Status</option>
                ${LEAD_STATUSES.map(s => `<option value="${s}" ${this.statusFilter === s ? 'selected' : ''}>${s.charAt(0).toUpperCase() + s.slice(1)}</option>`).join('')}
              </select>
              <select id="priorityFilter" class="form-select">
                <option value="">All Priority</option>
                ${LEAD_PRIORITIES.map(p => `<option value="${p}" ${this.priorityFilter === p ? 'selected' : ''}>${p.charAt(0).toUpperCase() + p.slice(1)}</option>`).join('')}
              </select>
              <button class="btn btn-primary btn-sm" id="applyTableFilter">Filter</button>
              <button class="btn btn-secondary btn-sm" id="resetTableFilter">Reset</button>
            </div>
          </div>

          <!-- Data Table -->
          ${this.leads.length > 0 ? `
            <div class="table-responsive">
              <table class="data-table leads-table">
                <thead>
                  <tr>
                    <th class="checkbox-col"><input type="checkbox" id="selectAll"></th>
                    <th>#</th>
                    <th>Date</th>
                    <th>Lead</th>
                    <th>Cat</th>
                    <th>Role</th>
                    <th>Co.</th>
                    <th>Sts</th>
                    <th>Pri</th>
                    <th>Owner</th>
                    <th>Tele</th>
                    <th>Field</th>
                    <th>Done</th>
                    <th>Last Act</th>
                    <th>Follow</th>
                    <th>Days</th>
                    <th>Act</th>
                  </tr>
                </thead>
                <tbody>
                  ${this.leads.map((lead, idx) => this.renderLeadRow(lead, idx + 1)).join('')}
                </tbody>
              </table>
            </div>
          ` : `
            <div class="empty-state">
              <div class="empty-icon">📋</div>
              <p>No leads found</p>
              <span>Try adjusting your filters</span>
            </div>
          `}
        </div>
      </div>
    `;

    this.attachEventListeners();
  }

  private renderLeadRow(lead: Lead, sno: number): string {
    const statusClass = lead.status.toLowerCase().replace(' ', '-');
    const priorityClass = lead.priority?.toLowerCase() || 'normal';
    const isSelected = this.selectedLeads.includes(lead.id);
    const phone = lead.phone || '';
    const whatsappNumber = phone.replace(/\D/g, '');
    
    const leadDate = lead.created_at ? new Date(lead.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' }) : '-';
    const lastInteracted = lead.last_interacted_at ? new Date(lead.last_interacted_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }) : '-';
    const nextFollowup = lead.next_followup ? new Date(lead.next_followup).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }) : '-';
    const completedDate = lead.completed_at ? new Date(lead.completed_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' }) : '—';
    
    return `
      <tr class="${isSelected ? 'selected' : ''}" data-lead-id="${lead.id}">
        <td><input type="checkbox" class="lead-checkbox" data-id="${lead.id}" ${isSelected ? 'checked' : ''}></td>
        <td>${sno}</td>
        <td class="date-cell">${leadDate}</td>
        <td class="lead-cell">
          <div class="lead-name">${lead.name}</div>
          <div class="lead-contact-links">
            <a href="tel:${phone}" class="mobile-link" onclick="event.stopPropagation()">${phone || '-'}</a>
            ${phone ? `<a href="https://wa.me/91${whatsappNumber}" class="whatsapp-link" target="_blank" onclick="event.stopPropagation()">💬</a>` : ''}
          </div>
        </td>
        <td>${lead.category_name || lead.category || '-'}</td>
        <td><span class="role-badge">${lead.role_type || 'Owner'}</span></td>
        <td>${lead.company_name || '-'}</td>
        <td><span class="status-badge ${statusClass}">${lead.status}</span></td>
        <td><span class="priority-badge ${priorityClass}">${lead.priority || 'Normal'}</span></td>
        <td class="owner-cell">${lead.primary_owner_name || '-'}</td>
        <td class="owner-cell" style="font-size:11px;">${lead.telecaller_name || '—'}</td>
        <td class="owner-cell" style="font-size:11px;">${lead.field_staff_name || '—'}</td>
        <td class="date-cell" style="color:#10b981;">${completedDate}</td>
        <td class="date-cell">${lastInteracted}</td>
        <td class="date-cell ${lead.next_followup && new Date(lead.next_followup) < new Date() ? 'overdue' : ''}">${nextFollowup}</td>
        <td class="days-cell">${lead.days_since_created || 0}</td>
        <td class="actions-cell">
          <a href="tel:${phone}" class="action-btn call-btn" onclick="event.stopPropagation()" title="Call">📞</a>
          <a href="https://wa.me/91${whatsappNumber}" class="action-btn whatsapp-btn" target="_blank" onclick="event.stopPropagation()" title="WhatsApp">💬</a>
          <button class="action-btn view-btn" data-id="${lead.id}" title="View">👁</button>
          <button class="action-btn edit-btn" data-id="${lead.id}" title="Edit">✏️</button>
        </td>
      </tr>
    `;
  }

  private formatCurrency(value: number): string {
    if (value >= 10000000) return (value / 10000000).toFixed(1) + 'Cr';
    if (value >= 100000) return (value / 100000).toFixed(1) + 'L';
    if (value >= 1000) return (value / 1000).toFixed(1) + 'K';
    return value.toFixed(0);
  }

  private attachEventListeners(): void {
    document.getElementById('companyFilter')?.addEventListener('change', (e) => {
      this.selectedCompanyId = parseInt((e.target as HTMLSelectElement).value) || null;
      this.loadTeamLeads();
    });

    document.getElementById('memberFilter')?.addEventListener('change', (e) => {
      this.selectedMemberId = parseInt((e.target as HTMLSelectElement).value) || null;
      this.loadTeamLeads();
    });

    document.getElementById('empStatusFilter')?.addEventListener('change', (e) => {
      this.empStatus = (e.target as HTMLSelectElement).value;
      this.loadTeamLeads();
    });

    // DC Protocol (Feb 2026): Add quick filter, category, and days since filter listeners
    document.getElementById('quickFilterSelect')?.addEventListener('change', (e) => {
      this.quickFilter = (e.target as HTMLSelectElement).value;
      this.loadTeamLeads();
    });

    document.getElementById('roleFilterSelect')?.addEventListener('change', (e) => {
      this.roleFilter = (e.target as HTMLSelectElement).value;
      this.loadTeamLeads();
    });

    document.getElementById('categoryFilterSelect')?.addEventListener('change', (e) => {
      this.categoryFilter = (e.target as HTMLSelectElement).value;
      this.loadTeamLeads();
    });

    document.getElementById('daysSinceFilter')?.addEventListener('change', (e) => {
      this.daysSinceFilter = (e.target as HTMLSelectElement).value;
      this.loadTeamLeads();
    });

    // DC Protocol (Feb 2026): Date filters for Team Leads
    document.getElementById('startDateFilter')?.addEventListener('change', (e) => {
      this.startDate = (e.target as HTMLInputElement).value;
      this.loadTeamLeads();
    });

    document.getElementById('endDateFilter')?.addEventListener('change', (e) => {
      this.endDate = (e.target as HTMLInputElement).value;
      this.loadTeamLeads();
    });

    document.getElementById('handlerSearch')?.addEventListener('keyup', (e) => {
      if ((e as KeyboardEvent).key === 'Enter') {
        this.handlerSearch = (e.target as HTMLInputElement).value;
        this.loadTeamLeads();
      }
    });

    // Add Lead button
    document.getElementById('addLeadBtn')?.addEventListener('click', () => {
      this.showAddLeadModal();
    });

    document.querySelectorAll('.filter-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        const tabId = tab.getAttribute('data-tab');
        if (tabId && tabId !== this.activeFilterTab) {
          this.activeFilterTab = tabId;
          this.loadTeamLeads();
        }
      });
    });

    document.getElementById('applyTableFilter')?.addEventListener('click', () => {
      this.searchQuery = (document.getElementById('searchInput') as HTMLInputElement)?.value || '';
      this.statusFilter = (document.getElementById('statusFilter') as HTMLSelectElement)?.value || '';
      this.priorityFilter = (document.getElementById('priorityFilter') as HTMLSelectElement)?.value || '';
      this.telecallerFilter = (document.getElementById('telecallerFilterInput') as HTMLInputElement)?.value?.trim().toLowerCase() || '';
      this.fieldStaffFilter = (document.getElementById('fieldStaffFilterInput') as HTMLInputElement)?.value?.trim().toLowerCase() || '';
      this.loadTeamLeads();
    });

    document.getElementById('resetTableFilter')?.addEventListener('click', () => {
      this.searchQuery = '';
      this.statusFilter = '';
      this.priorityFilter = '';
      this.telecallerFilter = '';
      this.fieldStaffFilter = '';
      const tcEl = document.getElementById('telecallerFilterInput') as HTMLInputElement;
      const fsEl = document.getElementById('fieldStaffFilterInput') as HTMLInputElement;
      if (tcEl) tcEl.value = '';
      if (fsEl) fsEl.value = '';
      this.loadTeamLeads();
    });

    document.getElementById('selectAll')?.addEventListener('change', (e) => {
      const isChecked = (e.target as HTMLInputElement).checked;
      if (isChecked) {
        this.selectedLeads = this.leads.map(l => l.id);
      } else {
        this.selectedLeads = [];
      }
      this.updateContent();
    });

    document.querySelectorAll('.lead-checkbox').forEach(cb => {
      cb.addEventListener('change', (e) => {
        const id = parseInt((e.target as HTMLInputElement).getAttribute('data-id') || '0');
        const isChecked = (e.target as HTMLInputElement).checked;
        if (isChecked && !this.selectedLeads.includes(id)) {
          this.selectedLeads.push(id);
        } else if (!isChecked) {
          this.selectedLeads = this.selectedLeads.filter(lid => lid !== id);
        }
        this.updateContent();
      });
    });

    document.getElementById('clearSelection')?.addEventListener('click', () => {
      this.selectedLeads = [];
      this.updateContent();
    });

    document.getElementById('showBulkActions')?.addEventListener('click', () => {
      document.getElementById('selectedCount')!.textContent = this.selectedLeads.length.toString();
      this.showModal('bulkModal');
    });

    // Row click to show lead details
    document.querySelectorAll('.leads-table tbody tr').forEach(row => {
      row.addEventListener('click', (e) => {
        if ((e.target as HTMLElement).closest('.action-btn, .lead-checkbox, a')) return;
        const leadId = row.getAttribute('data-lead-id');
        if (leadId) this.showLeadDetail(parseInt(leadId));
      });
    });

    document.querySelectorAll('.view-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const id = parseInt(btn.getAttribute('data-id') || '0');
        this.showLeadDetail(id);
      });
    });

    document.querySelectorAll('.edit-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const id = parseInt(btn.getAttribute('data-id') || '0');
        const lead = this.leads.find(l => l.id === id);
        if (lead) {
          this.showEditLeadModal(lead);
        }
      });
    });

    document.getElementById('addLeadBtn')?.addEventListener('click', () => {
      this.showAddLeadModal();
    });
    
    // DC Protocol: Header Add button - use correct selector for PageHeader action button
    const headerAddBtn = document.getElementById('headerActionBtn');
    if (headerAddBtn) {
      headerAddBtn.onclick = () => this.showAddLeadModal();
    }
  }

  private async showLeadDetail(leadId: number): Promise<void> {
    const lead = this.leads.find(l => l.id === leadId);
    if (!lead) return;

    const body = document.getElementById('detailBody');
    if (!body) return;

    let callHistory: any[] = [];
    let callSummary: any = null;
    try {
      const callResp = await apiService.get(`/call-tracking/lead/${leadId}/calls?per_page=50`);
      if (callResp) {
        callHistory = (callResp.data as any[]) || [];
        callSummary = (callResp as any).summary || null;
      }
    } catch (e) {
      console.warn('Failed to load call history', e);
    }

    body.innerHTML = `
      <div class="lead-detail">
        <div class="lead-header-info">
          <div class="lead-avatar">${lead.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}</div>
          <div>
            <h3>${lead.name}</h3>
            <p>${lead.phone}</p>
            ${lead.email ? `<p>${lead.email}</p>` : ''}
          </div>
        </div>

        <!-- DC Protocol N001: VGK Member Status Banner (lazy-loaded) -->
        <div id="stl-mob-vgk-banner" style="margin:10px 0"></div>

        <div class="detail-grid">
          <div class="detail-row"><span class="label">Category:</span><span class="value">${lead.category}</span></div>
          <div class="detail-row"><span class="label">Status:</span><span class="status-badge ${lead.status}">${lead.status}</span></div>
          <div class="detail-row"><span class="label">Priority:</span><span class="priority-badge ${lead.priority}">${lead.priority}</span></div>
          <div class="detail-row"><span class="label">Company:</span><span class="value">${lead.company_name || '-'}</span></div>
          <div class="detail-row"><span class="label">Source:</span><span class="value">${lead.source || '-'}</span></div>
          <div class="detail-row"><span class="label">Lead Owner:</span><span class="value">${lead.primary_owner_name || '-'}</span></div>
          <div class="detail-row"><span class="label">Telecaller:</span><span class="value">${lead.telecaller_name || '-'}</span></div>
          <div class="detail-row"><span class="label">Field Staff:</span><span class="value">${lead.field_staff_name || '-'}</span></div>
          <div class="detail-row"><span class="label">Value:</span><span class="value currency">₹${this.formatCurrency(lead.confirmed_final_value ?? lead.deal_value_total ?? 0)}${lead.confirmed_final_value != null ? ' 🔒' : ''}</span></div>
          <div class="detail-row"><span class="label">Received:</span><span class="value success">₹${this.formatCurrency(lead.deal_value_received || 0)}</span></div>
          <div class="detail-row"><span class="label">Balance:</span><span class="value warning">₹${this.formatCurrency(lead.deal_value_balance || 0)}</span></div>
        </div>

        <div class="call-history-section-mobile card" style="margin-top: 16px;">
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

        <div class="detail-actions" style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px;">
          <button class="btn btn-primary" id="detailEditBtn" style="flex: 1; min-width: 120px;">Edit</button>
          <button class="btn btn-info" id="detailFollowupBtn" style="flex: 1; min-width: 120px;">Follow-up</button>
          <button class="btn btn-warning" id="detailStatusBtn" style="flex: 1; min-width: 120px;">Status</button>
          <button class="btn btn-secondary" onclick="window.location.href='tel:${lead.phone}'" style="flex: 1; min-width: 100px;">Call</button>
          <button class="btn btn-success" onclick="window.open('https://wa.me/91${lead.phone}', '_blank')" style="flex: 1; min-width: 100px;">WhatsApp</button>
        </div>
      </div>
    `;

    this.selectedLead = lead;

    // DC Protocol N001: lazy-load VGK banner (non-blocking, 200ms after render)
    const _stlVgkCid = this.selectedCompanyId;
    if (_stlVgkCid) {
      setTimeout(() => vgkBannerService.load(leadId, _stlVgkCid, 'stl-mob-vgk-banner'), 200);
    }

    document.getElementById('detailEditBtn')?.addEventListener('click', () => {
      this.hideModal('detailModal');
      this.showEditLeadModal(lead);
    });

    document.getElementById('detailFollowupBtn')?.addEventListener('click', () => {
      this.hideModal('detailModal');
      routerService.navigate('staff-leads' as any, { leadId: lead.id.toString(), action: 'followup' });
    });

    document.getElementById('detailStatusBtn')?.addEventListener('click', () => {
      this.hideModal('detailModal');
      routerService.navigate('staff-leads' as any, { leadId: lead.id.toString(), action: 'status' });
    });

    document.querySelectorAll('.play-recording-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const recId = btn.getAttribute('data-recording-id');
        if (recId) this.playCallRecording(parseInt(recId), btn as HTMLElement);
      });
    });

    this.showModal('detailModal');
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

  private handleBulkAction(action: string): void {
    this.hideModal('bulkModal');
    console.log(`Bulk action ${action} for leads:`, this.selectedLeads);
  }
}
