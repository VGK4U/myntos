/**
 * Staff Bank-Wise Leads Page (Mobile View)
 * DC Protocol: DC_MOBILE_STAFF_BANK_LEADS_002
 * Comprehensive mobile interface for Field Staff Leads / Bank-Wise pipeline tracking
 * Complete parity with web staff_bank_wise_leads.html with eye toggle & direct call
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import { routerService } from '../services/router.service';
import { unifiedWAModal } from '../components/UnifiedWAModal';

interface BankLead {
  id: number;
  customer_name?: string;
  name?: string;
  phone_number?: string;
  customer_phone?: string;
  phone?: string;
  phone_primary_whatsapp?: boolean;
  city?: string;
  district?: string;
  city_district?: string;
  area?: string;
  address?: string;
  bank_name?: string;
  bank_branch?: string;
  bank_loan_account_no?: string;
  solar_pipeline_status?: string;
  solar_pipeline_stage?: string;
  stage?: string;
  status?: string;
  deal_value?: number;
  deal_value_total?: number;
  deal_value_received?: number;
  deal_value_balance?: number;
  loan_amount?: number;
  sanctioned_amount?: number;
  disbursed_amount?: number;
  system_capacity_kw?: number;
  capacity_kw?: number;
  capacity?: string;
  subsidy_amount?: number;
  stage_days?: number;
  days_in_stage?: number;
  days_active?: number;
  ground_source_name?: string;
  ground_source_phone?: string;
  ground_source_id?: string;
  ground_source_upliner?: string;
  upliner_name?: string;
  upliner_phone?: string;
  telecaller_name?: string;
  ground_support_name?: string;
  ground_support_phone?: string;
  field_staff_name?: string;
  handler_name?: string;
  uport_staff_name?: string;
  brand_name?: string;
  remarks?: string;
  notes?: string;
  google_maps_url?: string;
  updated_at?: string;
  created_at?: string;
}

export class StaffBankWiseLeadsPage {
  private container: HTMLElement;
  private leads: BankLead[] = [];
  private rawData: any = null;
  private currentTab: string = 'bank-files'; // 'bank-files' | 'balance-pending' | 'net-meter-pending' | 'electricity-bill-change' | 'branch-summary' | 'ground-source-summary'
  private isLoading: boolean = false;
  private isManager: boolean = false;
  
  // Filter state
  private selectedBank: string = 'ALL';
  private selectedStage: string = 'ALL';
  private selectedBucket: string = 'ALL';
  private selectedMember: string = 'ALL';
  private selectedUpliner: string = 'ALL';
  private selectedCity: string = 'ALL';
  private selectedArea: string = 'ALL';
  private selectedTelecaller: string = 'ALL';
  private selectedGroundSupport: string = 'ALL';
  private searchQuery: string = '';
  private expandedLeadIds: Set<number> = new Set();
  private expandedGroupIds: Set<string> = new Set();
  private revealedPhones: Set<string> = new Set(); // Stores phone keys that have been unmasked by the user
  private showFilterModal: boolean = false;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadLeads();
  }

  private isBankLead(l: BankLead): boolean {
    const stage = (l.solar_pipeline_stage || l.solar_pipeline_status || l.stage || l.status || '').toLowerCase();
    return stage === 'pending_with_bank' || stage === 'at bank' || stage === 'at_bank' || stage.includes('bank');
  }

  private isBalancePendingLead(l: BankLead): boolean {
    const stage = (l.solar_pipeline_stage || l.solar_pipeline_status || l.stage || l.status || '').toLowerCase();
    return stage === 'balance_pending' || stage === 'bal pending' || stage === 'bal_pending' || stage.includes('balance');
  }

  private isNetMeterPendingLead(l: BankLead): boolean {
    const stage = (l.solar_pipeline_stage || l.solar_pipeline_status || l.stage || l.status || '').toLowerCase();
    return stage === 'net_meter_pending' || stage === 'net_meter' || stage === 'net meter' || stage === 'net_metering_pending' || stage.includes('net_meter') || stage.includes('net meter');
  }

  private isElectricityBillChangeLead(l: BankLead): boolean {
    const stage = (l.solar_pipeline_stage || l.solar_pipeline_status || l.stage || l.status || '').toLowerCase();
    return stage === 'electricity_bill_change' || stage === 'electricity_bill' || stage === 'eb_name_change' || stage.includes('electricity') || stage.includes('eb_name') || stage.includes('bill_change');
  }

  private getActiveLeads(): BankLead[] {
    if (this.currentTab === 'balance-pending') {
      return this.leads.filter(l => this.isBalancePendingLead(l));
    } else if (this.currentTab === 'net-meter-pending') {
      return this.leads.filter(l => this.isNetMeterPendingLead(l));
    } else if (this.currentTab === 'electricity-bill-change') {
      return this.leads.filter(l => this.isElectricityBillChangeLead(l));
    } else if (this.currentTab === 'branch-summary' || this.currentTab === 'ground-source-summary') {
      return this.leads;
    }
    return this.leads.filter(l => this.isBankLead(l));
  }

  private async loadLeads(): Promise<void> {
    this.isLoading = true;
    this.renderLoadingState();

    try {
      const queryParams = new URLSearchParams();
      if (this.selectedBank !== 'ALL') queryParams.append('bank_name', this.selectedBank);
      if (this.selectedStage !== 'ALL') queryParams.append('stage_filter', this.selectedStage);
      if (this.selectedBucket !== 'ALL') queryParams.append('bucket_filter', this.selectedBucket);
      if (this.selectedMember !== 'ALL') queryParams.append('member_filter', this.selectedMember);
      if (this.selectedUpliner !== 'ALL') queryParams.append('upliner_filter', this.selectedUpliner);
      if (this.selectedCity !== 'ALL') queryParams.append('city_filter', this.selectedCity);
      if (this.selectedArea !== 'ALL') queryParams.append('area_filter', this.selectedArea);
      if (this.selectedTelecaller !== 'ALL') queryParams.append('telecaller_filter', this.selectedTelecaller);
      if (this.selectedGroundSupport !== 'ALL') queryParams.append('ground_support_filter', this.selectedGroundSupport);
      if (this.searchQuery.trim()) queryParams.append('search', this.searchQuery.trim());

      const url = `/crm/bank-wise-leads${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
      const response = await apiService.get<any>(url);

      if (response.success && response.data) {
        this.rawData = response.data;
        this.leads = response.data.leads || [];
        this.isManager = !!response.data.is_manager;
      } else {
        this.leads = [];
      }
    } catch (error) {
      console.error('[StaffBankWiseLeadsPage] Error loading bank leads:', error);
      this.leads = [];
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  private formatCurrency(amount?: number | null): string {
    if (amount == null || isNaN(amount)) return '₹0';
    if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(2)} Cr`;
    if (amount >= 100000) return `₹${(amount / 100000).toFixed(2)} L`;
    return `₹${amount.toLocaleString('en-IN')}`;
  }

  private escapeHtml(text?: string | null): string {
    if (!text) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  /**
   * Masks a phone number (e.g., 9876543210 -> 98••••3210 or ••••••3210)
   * unless unmasked by the user via the Eye icon toggle
   */
  private maskPhone(phone: string, phoneKey: string): { displayText: string; isRevealed: boolean } {
    if (!phone || phone.trim() === '' || phone === '—' || phone === 'null') {
      return { displayText: '—', isRevealed: false };
    }
    const clean = phone.replace(/[^0-9+]/g, '');
    const isRevealed = this.revealedPhones.has(phoneKey);
    if (isRevealed) {
      return { displayText: phone, isRevealed: true };
    }
    if (clean.length <= 4) {
      return { displayText: '••••', isRevealed: false };
    }
    const last4 = clean.slice(-4);
    const prefix = clean.length > 8 ? clean.slice(0, 2) : '';
    return { displayText: `${prefix}••••••${last4}`, isRevealed: false };
  }

  private render(): void {
    const activeLeads = this.getActiveLeads();
    
    // Tab counts
    const bankLeadsCount = this.leads.filter(l => this.isBankLead(l)).length;
    const balanceCount = this.leads.filter(l => this.isBalancePendingLead(l)).length;
    const netMeterCount = this.leads.filter(l => this.isNetMeterPendingLead(l)).length;
    const ebCount = this.leads.filter(l => this.isElectricityBillChangeLead(l)).length;

    // Aggregate metrics for active leads
    let totalDealValue = 0;
    let b0_7 = 0, b8_15 = 0, b16_30 = 0, b31_60 = 0, bGt60 = 0;

    activeLeads.forEach(l => {
      const val = (this.currentTab === 'balance-pending') 
        ? ((l.deal_value_balance !== undefined && l.deal_value_balance !== null) ? l.deal_value_balance : (l.deal_value || 0))
        : (l.deal_value || l.loan_amount || l.deal_value_total || 0);
      totalDealValue += val;
      const days = l.stage_days || l.days_in_stage || l.days_active || 0;
      if (days <= 7) b0_7++;
      else if (days <= 15) b8_15++;
      else if (days <= 30) b16_30++;
      else if (days <= 60) b31_60++;
      else bGt60++;
    });

    this.container.innerHTML = `
      <div class="page-container bank-leads-page">
        ${PageHeader.render({ 
          title: 'Field staff leads', 
          showBack: true
        })}

        <!-- Top Navigation Banner -->
        <div class="bl-banner">
          <div class="bl-banner-info">
            <h3 class="bl-banner-title">
              <i class="fas fa-university me-2" style="color:#60a5fa;"></i>Field staff leads
              ${this.isManager ? '<span class="bl-role-badge manager">Sales & Leadership View</span>' : '<span class="bl-role-badge staff">Assigned Files</span>'}
            </h3>
            <p class="bl-banner-sub">Real-time bank processing, sanction, net-metering &amp; balance pipelines</p>
          </div>
          <button class="bl-refresh-btn" id="refreshBankLeadsBtn" title="Refresh">
            <i class="fas fa-sync-alt ${this.isLoading ? 'fa-spin' : ''}"></i>
          </button>
        </div>

        <!-- Horizontal Tabs Scroll -->
        <div class="bl-tabs-container">
          <div class="bl-tabs-scroll">
            <button class="bl-tab-btn ${this.currentTab === 'bank-files' ? 'active' : ''}" data-tab="bank-files">
              <i class="fas fa-university me-1"></i> Bank Files <span class="bl-tab-badge">${bankLeadsCount}</span>
            </button>
            <button class="bl-tab-btn warning ${this.currentTab === 'balance-pending' ? 'active' : ''}" data-tab="balance-pending">
              <i class="fas fa-rupee-sign me-1"></i> Balance Pending <span class="bl-tab-badge">${balanceCount}</span>
            </button>
            <button class="bl-tab-btn purple ${this.currentTab === 'net-meter-pending' ? 'active' : ''}" data-tab="net-meter-pending">
              <i class="fas fa-bolt me-1"></i> Net Meter <span class="bl-tab-badge">${netMeterCount}</span>
            </button>
            <button class="bl-tab-btn info ${this.currentTab === 'electricity-bill-change' ? 'active' : ''}" data-tab="electricity-bill-change">
              <i class="fas fa-file-invoice me-1"></i> EB Change <span class="bl-tab-badge">${ebCount}</span>
            </button>
            <button class="bl-tab-btn teal ${this.currentTab === 'branch-summary' ? 'active' : ''}" data-tab="branch-summary">
              <i class="fas fa-building me-1"></i> Branch Summary
            </button>
            <button class="bl-tab-btn emerald ${this.currentTab === 'ground-source-summary' ? 'active' : ''}" data-tab="ground-source-summary">
              <i class="fas fa-users me-1"></i> Ground Source
            </button>
          </div>
        </div>

        <!-- Metrics Grid -->
        <div class="bl-metrics-grid">
          <div class="bl-metric-card highlight">
            <span class="bl-metric-label">Active Files</span>
            <span class="bl-metric-val">${activeLeads.length}</span>
          </div>
          <div class="bl-metric-card highlight">
            <span class="bl-metric-label">${this.currentTab === 'balance-pending' ? 'Total Pending Bal' : 'Total Portfolio'}</span>
            <span class="bl-metric-val" style="color:#38bdf8;">${this.formatCurrency(totalDealValue)}</span>
          </div>
          <div class="bl-metric-card">
            <span class="bl-metric-label text-success">0-7 Days (Fresh)</span>
            <span class="bl-metric-val text-success">${b0_7}</span>
          </div>
          <div class="bl-metric-card">
            <span class="bl-metric-label text-info">8-15 Days (Active)</span>
            <span class="bl-metric-val text-info">${b8_15}</span>
          </div>
          <div class="bl-metric-card">
            <span class="bl-metric-label text-warning">16-30 Days</span>
            <span class="bl-metric-val text-warning">${b16_30}</span>
          </div>
          <div class="bl-metric-card">
            <span class="bl-metric-label text-orange" style="color:#f97316;">31-60 Days</span>
            <span class="bl-metric-val" style="color:#f97316;">${b31_60}</span>
          </div>
          <div class="bl-metric-card danger">
            <span class="bl-metric-label text-danger">>60 Days (Critical)</span>
            <span class="bl-metric-val text-danger">${bGt60}</span>
          </div>
        </div>

        <!-- Search & Filter Bar -->
        <div class="bl-search-bar">
          <div class="bl-search-input-wrap">
            <i class="fas fa-search bl-search-icon"></i>
            <input type="text" id="blSearchInput" class="bl-search-input" placeholder="Search customer, phone, bank, branch, upliner..." value="${this.escapeHtml(this.searchQuery)}">
            ${this.searchQuery ? '<button class="bl-clear-search" id="clearSearchBtn">✕</button>' : ''}
          </div>
          <button class="bl-filter-toggle-btn ${this.hasActiveFilters() ? 'active' : ''}" id="toggleFilterModalBtn">
            <i class="fas fa-filter"></i>
            <span>Filters</span>
            ${this.hasActiveFilters() ? '<span class="bl-filter-dot"></span>' : ''}
          </button>
        </div>

        <!-- Main Content Area -->
        <div class="bl-content-area" id="blContentArea">
          ${this.renderMainContent(activeLeads)}
        </div>

        <!-- Filter Modal Overlay -->
        ${this.showFilterModal ? this.renderFilterModal() : ''}
      </div>

      ${this.getStyles()}
    `;

    this.attachEventListeners();
  }

  private hasActiveFilters(): boolean {
    return this.selectedBank !== 'ALL' ||
      this.selectedStage !== 'ALL' ||
      this.selectedBucket !== 'ALL' ||
      this.selectedMember !== 'ALL' ||
      this.selectedUpliner !== 'ALL' ||
      this.selectedCity !== 'ALL' ||
      this.selectedTelecaller !== 'ALL' ||
      this.selectedGroundSupport !== 'ALL';
  }

  private renderMainContent(leads: BankLead[]): string {
    if (this.isLoading) {
      return `
        <div class="bl-empty-state">
          <i class="fas fa-circle-notch fa-spin fa-2x" style="color:#6366f1; margin-bottom:12px;"></i>
          <p>Loading field staff leads...</p>
        </div>
      `;
    }

    if (this.currentTab === 'branch-summary') {
      return this.renderBranchSummaryView();
    }

    if (this.currentTab === 'ground-source-summary') {
      return this.renderGroundSourceSummaryView();
    }

    if (leads.length === 0) {
      return `
        <div class="bl-empty-state">
          <i class="fas fa-folder-open fa-3x" style="color:rgba(255,255,255,0.2); margin-bottom:12px;"></i>
          <h4>No Leads Found</h4>
          <p>No active files match the selected tab and filter criteria.</p>
          ${this.hasActiveFilters() ? '<button class="bl-btn bl-btn-secondary" id="resetFiltersBtn">Reset Filters</button>' : ''}
        </div>
      `;
    }

    return `
      <div class="bl-leads-list">
        <div class="bl-leads-count-bar">
          <span>Showing <strong>${leads.length}</strong> active files</span>
        </div>
        ${leads.map((lead, idx) => this.renderLeadCard(lead, idx + 1)).join('')}
      </div>
    `;
  }

  private renderLeadCard(lead: BankLead, index: number): string {
    const isExpanded = this.expandedLeadIds.has(lead.id);
    const days = lead.stage_days || lead.days_in_stage || lead.days_active || 0;
    
    let daysBadgeClass = 'days-normal';
    if (days > 60) daysBadgeClass = 'days-danger';
    else if (days > 30) daysBadgeClass = 'days-warning';
    else if (days > 15) daysBadgeClass = 'days-info';

    const customerName = lead.customer_name || lead.name || 'Unnamed Client';
    const customerPhone = lead.phone_number || lead.customer_phone || lead.phone || '';
    const cleanCustomerPhone = customerPhone.replace(/[^0-9]/g, '');
    const customerPhoneKey = `cust_${lead.id}`;
    const custMask = this.maskPhone(customerPhone, customerPhoneKey);

    const bankName = lead.bank_name || 'Unassigned Bank';
    const bankBranch = lead.bank_branch || 'Main Branch';
    const stageName = (lead.solar_pipeline_stage || lead.solar_pipeline_status || lead.stage || lead.status || 'Pending').toUpperCase().replace(/_/g, ' ');
    
    const dealVal = lead.deal_value || lead.loan_amount || lead.deal_value_total || 0;
    const paidVal = lead.deal_value_received || 0;
    const balVal = (lead.deal_value_balance !== undefined && lead.deal_value_balance !== null) ? lead.deal_value_balance : (dealVal - paidVal);

    const capacity = lead.capacity_kw ? `${lead.capacity_kw} kW` : (lead.system_capacity_kw ? `${lead.system_capacity_kw} kW` : (lead.capacity || '—'));
    const location = lead.city_district || `${lead.city || ''} ${lead.area || ''}`.trim() || '—';

    // Ground Source info
    const gsName = lead.ground_source_name || 'Direct';
    const gsPhone = lead.ground_source_phone || '';
    const cleanGsPhone = gsPhone.replace(/[^0-9]/g, '');
    const gsPhoneKey = `gs_${lead.id}`;
    const gsMask = this.maskPhone(gsPhone, gsPhoneKey);

    // Upliner info
    const uplinerName = lead.upliner_name || lead.ground_source_upliner || '';
    const uplinerPhone = lead.upliner_phone || '';
    const cleanUplinerPhone = uplinerPhone.replace(/[^0-9]/g, '');
    const uplinerPhoneKey = `up_${lead.id}`;
    const uplinerMask = this.maskPhone(uplinerPhone, uplinerPhoneKey);

    // Ground Support info
    const gsStaffName = lead.ground_support_name || lead.field_staff_name || '—';
    const gsStaffPhone = lead.ground_support_phone || '';
    const cleanGsStaffPhone = gsStaffPhone.replace(/[^0-9]/g, '');
    const gsStaffPhoneKey = `fs_${lead.id}`;
    const gsStaffMask = this.maskPhone(gsStaffPhone, gsStaffPhoneKey);

    // Up-port & Telecaller
    const tcName = lead.telecaller_name || '—';
    const uportName = lead.uport_staff_name || '—';

    return `
      <div class="bl-card" data-lead-id="${lead.id}">
        <!-- Top Title & Badge Bar -->
        <div class="bl-card-header">
          <div class="bl-card-customer">
            <span class="bl-source-tag"><i class="fas fa-user-tag me-1"></i>${this.escapeHtml(gsName)}</span>
            <h4 class="bl-customer-name">
              <span class="bl-index-num">${index}.</span> ${this.escapeHtml(customerName)}
            </h4>
            <div class="bl-loc-line"><i class="fas fa-map-marker-alt me-1" style="color:#ef4444; font-size:11px;"></i>${this.escapeHtml(location)}</div>
          </div>
          <div class="bl-card-badge-wrap">
            <span class="bl-days-badge ${daysBadgeClass}">${days}d active</span>
            <span class="bl-stage-pill">${this.escapeHtml(stageName)}</span>
          </div>
        </div>

        <!-- Phone Section with Eye / View Toggle & Direct Call / WhatsApp -->
        <div class="bl-phone-action-box">
          <div class="bl-phone-left">
            <span class="bl-phone-lbl">Customer Contact:</span>
            <div class="bl-phone-val-wrap">
              <span class="bl-phone-display ${custMask.isRevealed ? 'revealed' : 'masked'}">${this.escapeHtml(custMask.displayText)}</span>
              ${customerPhone ? `
                <button class="bl-eye-toggle-btn toggle-phone-mask" data-phone-key="${customerPhoneKey}" title="${custMask.isRevealed ? 'Hide Number' : 'Reveal Number'}">
                  <i class="fas fa-eye${custMask.isRevealed ? '-slash text-warning' : ''}"></i>
                </button>
              ` : ''}
            </div>
          </div>

          ${customerPhone ? `
            <div class="bl-direct-call-actions">
              <a href="tel:${cleanCustomerPhone}" class="bl-btn-call" title="Direct Call">
                <i class="fas fa-phone-alt me-1"></i> Call
              </a>
              <button class="bl-btn-wa open-wa-modal" data-phone="${cleanCustomerPhone}" data-name="${this.escapeHtml(customerName)}" data-lead-id="${lead.id}" data-context="${this.escapeHtml(bankName)} (${this.escapeHtml(stageName)})" title="Send WhatsApp Message">
                <i class="fab fa-whatsapp"></i>
              </button>
            </div>
          ` : ''}
        </div>

        <!-- Key Financials & Details Grid -->
        <div class="bl-card-body">
          <div class="bl-info-grid">
            <div class="bl-info-item">
              <span class="bl-info-lbl">Bank &amp; Branch</span>
              <span class="bl-info-val highlight">
                <i class="fas fa-university me-1" style="color:#60a5fa;"></i>${this.escapeHtml(bankName)}
                <small style="display:block; color:#9ca3af; font-size:11px;">${this.escapeHtml(bankBranch)}</small>
              </span>
            </div>
            
            <div class="bl-info-item">
              <span class="bl-info-lbl">${this.currentTab === 'balance-pending' ? 'Balance Pending' : 'Total Deal Value'}</span>
              <span class="bl-info-val" style="color:#34d399; font-weight:700;">
                ${this.formatCurrency(this.currentTab === 'balance-pending' ? balVal : dealVal)}
              </span>
              ${this.currentTab === 'balance-pending' ? `
                <small style="display:block; color:#9ca3af; font-size:10px;">Total: ${this.formatCurrency(dealVal)} | Paid: ${this.formatCurrency(paidVal)}</small>
              ` : ''}
            </div>

            <div class="bl-info-item">
              <span class="bl-info-lbl">Capacity / Brand</span>
              <span class="bl-info-val">
                <i class="fas fa-solar-panel me-1" style="color:#fbbf24;"></i>${this.escapeHtml(capacity)}
                <small style="display:block; color:#9ca3af; font-size:11px;">Brand: ${this.escapeHtml(lead.brand_name || '—')}</small>
              </span>
            </div>

            <div class="bl-info-item">
              <span class="bl-info-lbl">Telecaller / Up-Port</span>
              <span class="bl-info-val">
                <i class="fas fa-headset me-1" style="color:#38bdf8;"></i>TC: ${this.escapeHtml(tcName)}
                <small style="display:block; color:#c084fc; font-size:11px;">Up: ${this.escapeHtml(uportName)}</small>
              </span>
            </div>
          </div>

          <!-- Expandable Complete Details -->
          ${isExpanded ? `
            <div class="bl-expanded-details">
              <!-- Ground Source & Upliner Direct Communication Box -->
              <div class="bl-nested-contact-box">
                <div class="bl-nested-title"><i class="fas fa-users-cog me-1" style="color:#f59e0b;"></i> Ground Source &amp; Upliner:</div>
                <div class="bl-nested-row">
                  <div>
                    <span class="bl-det-lbl">Source:</span> <strong>${this.escapeHtml(gsName)}</strong>
                    ${gsPhone ? `
                      <span class="bl-phone-display small ${gsMask.isRevealed ? 'revealed' : 'masked'} ms-1">${this.escapeHtml(gsMask.displayText)}</span>
                      <button class="bl-eye-toggle-btn mini toggle-phone-mask" data-phone-key="${gsPhoneKey}"><i class="fas fa-eye${gsMask.isRevealed ? '-slash' : ''}"></i></button>
                    ` : ''}
                  </div>
                  <div style="display:flex; gap:6px;">
                    ${gsPhone ? `<a href="tel:${cleanGsPhone}" class="bl-mini-call-btn source"><i class="fas fa-phone-alt me-1"></i>Call</a>` : ''}
                    ${gsPhone ? `<button class="bl-mini-call-btn source open-wa-modal" data-phone="${cleanGsPhone}" data-name="${this.escapeHtml(gsName)}" data-lead-id="${lead.id}" data-context="Ground Source: ${this.escapeHtml(customerName)}" style="background:#16a34a; border-color:#16a34a;"><i class="fab fa-whatsapp"></i></button>` : ''}
                  </div>
                </div>

                ${uplinerName && uplinerName !== '—' ? `
                  <div class="bl-nested-row mt-1">
                    <div>
                      <span class="bl-det-lbl">Upliner:</span> <strong>${this.escapeHtml(uplinerName)}</strong>
                      ${uplinerPhone ? `
                        <span class="bl-phone-display small ${uplinerMask.isRevealed ? 'revealed' : 'masked'} ms-1">${this.escapeHtml(uplinerMask.displayText)}</span>
                        <button class="bl-eye-toggle-btn mini toggle-phone-mask" data-phone-key="${uplinerPhoneKey}"><i class="fas fa-eye${uplinerMask.isRevealed ? '-slash' : ''}"></i></button>
                      ` : ''}
                    </div>
                    <div style="display:flex; gap:6px;">
                      ${uplinerPhone ? `<a href="tel:${cleanUplinerPhone}" class="bl-mini-call-btn upliner"><i class="fas fa-phone-alt me-1"></i>Call</a>` : ''}
                      ${uplinerPhone ? `<button class="bl-mini-call-btn upliner open-wa-modal" data-phone="${cleanUplinerPhone}" data-name="${this.escapeHtml(uplinerName)}" data-lead-id="${lead.id}" data-context="Upliner: ${this.escapeHtml(customerName)}" style="background:#16a34a; border-color:#16a34a;"><i class="fab fa-whatsapp"></i></button>` : ''}
                    </div>
                  </div>
                ` : ''}
              </div>

              <!-- Ground Support Staff -->
              <div class="bl-details-row">
                <span class="bl-det-lbl">Ground Support Staff:</span>
                <span class="bl-det-val">
                  ${this.escapeHtml(gsStaffName)}
                  ${gsStaffPhone ? `
                    <span class="bl-phone-display small ${gsStaffMask.isRevealed ? 'revealed' : 'masked'} ms-1">${this.escapeHtml(gsStaffMask.displayText)}</span>
                    <button class="bl-eye-toggle-btn mini toggle-phone-mask" data-phone-key="${gsStaffPhoneKey}"><i class="fas fa-eye${gsStaffMask.isRevealed ? '-slash' : ''}"></i></button>
                    <a href="tel:${cleanGsStaffPhone}" class="bl-mini-call-btn gs ms-1"><i class="fas fa-phone-alt"></i></a>
                    <button class="bl-mini-call-btn gs open-wa-modal ms-1" data-phone="${cleanGsStaffPhone}" data-name="${this.escapeHtml(gsStaffName)}" data-lead-id="${lead.id}" data-context="Ground Staff: ${this.escapeHtml(customerName)}" style="background:#16a34a; border-color:#16a34a;"><i class="fab fa-whatsapp"></i></button>
                  ` : ''}
                </span>
              </div>

              <div class="bl-details-row">
                <span class="bl-det-lbl">Area / Address:</span>
                <span class="bl-det-val">${this.escapeHtml(lead.area || lead.address || '—')}</span>
              </div>

              ${lead.remarks || lead.notes ? `
                <div class="bl-notes-box">
                  <span class="bl-det-lbl">Remarks / Notes:</span>
                  <p class="bl-notes-text">${this.escapeHtml(lead.remarks || lead.notes)}</p>
                </div>
              ` : ''}
            </div>
          ` : ''}
        </div>

        <!-- Card Action Footer (DISCOM, Bank Docs, Maps, CRM Lead, Expand) -->
        <div class="bl-card-footer">
          <div class="bl-doc-actions">
            <button class="bl-doc-btn discom open-doc-action" data-lead-id="${lead.id}" data-type="discom" title="Open DISCOM Docs">
              <i class="fas fa-bolt me-1"></i> DISCOM
            </button>
            <button class="bl-doc-btn bank open-doc-action" data-lead-id="${lead.id}" data-type="bank" title="Open Bank Docs">
              <i class="fas fa-university me-1"></i> Bank
            </button>
            ${lead.google_maps_url ? `
              <a href="${lead.google_maps_url}" target="_blank" class="bl-doc-btn map" title="Google Maps Location">
                <i class="fas fa-map-marker-alt me-1"></i> Map
              </a>
            ` : ''}
          </div>

          <div class="bl-expand-actions">
            <button class="bl-expand-btn toggle-lead-expand" data-lead-id="${lead.id}">
              <span>${isExpanded ? 'Less' : 'More Details'}</span>
              <i class="fas fa-chevron-${isExpanded ? 'up' : 'down'} ms-1"></i>
            </button>
            <button class="bl-action-btn view-crm-lead" data-lead-id="${lead.id}" title="Open Lead in CRM">
              <i class="fas fa-external-link-alt"></i>
            </button>
          </div>
        </div>
      </div>
    `;
  }

  private renderBranchSummaryView(): string {
    const branchMap = new Map<string, { bankName: string; branch: string; leads: BankLead[]; totalLoan: number }>();

    this.leads.forEach(l => {
      const bankName = l.bank_name || 'Unassigned';
      const branch = l.bank_branch || 'Main Branch';
      const key = `${bankName}:::${branch}`;

      if (!branchMap.has(key)) {
        branchMap.set(key, { bankName, branch, leads: [], totalLoan: 0 });
      }
      const group = branchMap.get(key)!;
      group.leads.push(l);
      group.totalLoan += (l.deal_value || l.loan_amount || l.deal_value_total || 0);
    });

    const groups = Array.from(branchMap.values()).sort((a, b) => b.leads.length - a.leads.length);

    if (groups.length === 0) {
      return `
        <div class="bl-empty-state">
          <i class="fas fa-university fa-3x" style="color:rgba(255,255,255,0.2); margin-bottom:12px;"></i>
          <h4>No Branch Data</h4>
          <p>No bank branch groupings found.</p>
        </div>
      `;
    }

    return `
      <div class="bl-summary-list">
        <div class="bl-leads-count-bar">
          <span>Showing <strong>${groups.length}</strong> Bank Branches</span>
        </div>
        ${groups.map(g => {
          const key = `${g.bankName}:::${g.branch}`;
          const isExp = this.expandedGroupIds.has(key);
          return `
            <div class="bl-summary-card">
              <div class="bl-summary-hdr toggle-group-expand" data-group-key="${this.escapeHtml(key)}">
                <div class="bl-sum-left">
                  <h4 class="bl-sum-title"><i class="fas fa-university me-2" style="color:#60a5fa;"></i>${this.escapeHtml(g.bankName)}</h4>
                  <span class="bl-sum-sub"><i class="fas fa-map-marker-alt me-1"></i>${this.escapeHtml(g.branch)}</span>
                </div>
                <div class="bl-sum-right">
                  <span class="bl-sum-badge count">${g.leads.length} files</span>
                  <span class="bl-sum-badge amount">${this.formatCurrency(g.totalLoan)}</span>
                  <i class="fas fa-chevron-${isExp ? 'up' : 'down'} ms-2" style="color:#9ca3af; font-size:12px;"></i>
                </div>
              </div>
              ${isExp ? `
                <div class="bl-summary-items">
                  ${g.leads.map(l => {
                    const phone = l.phone_number || l.customer_phone || l.phone || '';
                    const cleanPhone = phone.replace(/[^0-9]/g, '');
                    return `
                      <div class="bl-sum-subitem">
                        <div style="flex:1;">
                          <strong>${this.escapeHtml(l.customer_name || l.name || 'Client')}</strong>
                          <div style="font-size:11px; color:#9ca3af;">
                            ${this.escapeHtml(l.ground_source_name || 'Direct')} • ${this.escapeHtml(l.city_district || l.city || '')}
                          </div>
                        </div>
                        <div style="text-align:right; display:flex; align-items:center; gap:8px;">
                          <div>
                            <span style="color:#34d399; font-weight:700; font-size:13px;">${this.formatCurrency(l.deal_value || l.loan_amount || 0)}</span>
                            <div style="font-size:11px; color:#fbbf24;">${l.stage_days || 0}d active</div>
                          </div>
                          ${phone ? `<a href="tel:${cleanPhone}" class="bl-quick-btn call" title="Call"><i class="fas fa-phone"></i></a>` : ''}
                        </div>
                      </div>
                    `;
                  }).join('')}
                </div>
              ` : ''}
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  private renderGroundSourceSummaryView(): string {
    const gsMap = new Map<string, { memberName: string; upliner: string; phone: string; leads: BankLead[]; totalLoan: number }>();

    this.leads.forEach(l => {
      const memberName = l.ground_source_name || 'Unassigned / Direct';
      const upliner = l.upliner_name || l.ground_source_upliner || 'Direct';
      const phone = l.ground_source_phone || '';
      const key = memberName;

      if (!gsMap.has(key)) {
        gsMap.set(key, { memberName, upliner, phone, leads: [], totalLoan: 0 });
      }
      const group = gsMap.get(key)!;
      group.leads.push(l);
      group.totalLoan += (l.deal_value || l.loan_amount || l.deal_value_total || 0);
    });

    const groups = Array.from(gsMap.values()).sort((a, b) => b.leads.length - a.leads.length);

    if (groups.length === 0) {
      return `
        <div class="bl-empty-state">
          <i class="fas fa-users fa-3x" style="color:rgba(255,255,255,0.2); margin-bottom:12px;"></i>
          <h4>No Ground Source Data</h4>
          <p>No ground source partner groupings found.</p>
        </div>
      `;
    }

    return `
      <div class="bl-summary-list">
        <div class="bl-leads-count-bar">
          <span>Showing <strong>${groups.length}</strong> Ground Source Members</span>
        </div>
        ${groups.map(g => {
          const key = g.memberName;
          const isExp = this.expandedGroupIds.has(key);
          const cleanPhone = g.phone.replace(/[^0-9]/g, '');
          return `
            <div class="bl-summary-card">
              <div class="bl-summary-hdr toggle-group-expand" data-group-key="${this.escapeHtml(key)}">
                <div class="bl-sum-left">
                  <h4 class="bl-sum-title"><i class="fas fa-user-tag me-2" style="color:#f59e0b;"></i>${this.escapeHtml(g.memberName)}</h4>
                  <span class="bl-sum-sub">Upliner: ${this.escapeHtml(g.upliner)}</span>
                </div>
                <div class="bl-sum-right">
                  <span class="bl-sum-badge count">${g.leads.length} files</span>
                  <span class="bl-sum-badge amount">${this.formatCurrency(g.totalLoan)}</span>
                  ${g.phone ? `<a href="tel:${cleanPhone}" class="bl-quick-btn call" onclick="event.stopPropagation()" title="Call Member"><i class="fas fa-phone"></i></a>` : ''}
                  <i class="fas fa-chevron-${isExp ? 'up' : 'down'} ms-2" style="color:#9ca3af; font-size:12px;"></i>
                </div>
              </div>
              ${isExp ? `
                <div class="bl-summary-items">
                  ${g.leads.map(l => {
                    const custPhone = l.phone_number || l.customer_phone || l.phone || '';
                    const cleanCustPhone = custPhone.replace(/[^0-9]/g, '');
                    return `
                      <div class="bl-sum-subitem">
                        <div style="flex:1;">
                          <strong>${this.escapeHtml(l.customer_name || l.name || 'Client')}</strong>
                          <div style="font-size:11px; color:#9ca3af;">
                            ${this.escapeHtml(l.bank_name || 'Bank')} (${this.escapeHtml(l.bank_branch || 'Branch')}) • ${this.escapeHtml(l.city_district || l.city || '')}
                          </div>
                        </div>
                        <div style="text-align:right; display:flex; align-items:center; gap:8px;">
                          <div>
                            <span style="color:#34d399; font-weight:700; font-size:13px;">${this.formatCurrency(l.deal_value || l.loan_amount || 0)}</span>
                            <div style="font-size:11px; color:#fbbf24;">${l.stage_days || 0}d active</div>
                          </div>
                          ${custPhone ? `<a href="tel:${cleanCustPhone}" class="bl-quick-btn call" title="Call"><i class="fas fa-phone"></i></a>` : ''}
                        </div>
                      </div>
                    `;
                  }).join('')}
                </div>
              ` : ''}
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  private renderFilterModal(): string {
    const banks = this.rawData?.bank_summary || [];
    const members = this.rawData?.unique_members || [];
    const upliners = this.rawData?.unique_upliners || [];
    const cities = this.rawData?.unique_cities || [];
    const telecallers = this.rawData?.unique_telecallers || [];
    const groundSupports = this.rawData?.unique_ground_supports || [];

    return `
      <div class="bl-modal-overlay" id="filterModalOverlay">
        <div class="bl-modal">
          <div class="bl-modal-header">
            <h4><i class="fas fa-filter me-2"></i>Filter Field Staff Leads</h4>
            <button class="bl-modal-close" id="closeFilterModalBtn">✕</button>
          </div>
          <div class="bl-modal-body">
            <div class="bl-form-group">
              <label>Bank Name</label>
              <select id="modalBankSelect" class="bl-select">
                <option value="ALL" ${this.selectedBank === 'ALL' ? 'selected' : ''}>All Banks</option>
                ${banks.map((b: any) => `<option value="${this.escapeHtml(b.bank_name)}" ${this.selectedBank === b.bank_name ? 'selected' : ''}>${this.escapeHtml(b.bank_name)} (${b.total_files || b.count || 0})</option>`).join('')}
              </select>
            </div>

            <div class="bl-form-group">
              <label>Stage Age Bucket</label>
              <select id="modalBucketSelect" class="bl-select">
                <option value="ALL" ${this.selectedBucket === 'ALL' ? 'selected' : ''}>All Age Buckets</option>
                <option value="b_0_7" ${this.selectedBucket === 'b_0_7' ? 'selected' : ''}>0 - 7 Days (Fresh)</option>
                <option value="b_8_15" ${this.selectedBucket === 'b_8_15' ? 'selected' : ''}>8 - 15 Days (Active)</option>
                <option value="b_16_30" ${this.selectedBucket === 'b_16_30' ? 'selected' : ''}>16 - 30 Days (Follow-up)</option>
                <option value="b_31_60" ${this.selectedBucket === 'b_31_60' ? 'selected' : ''}>31 - 60 Days (Delayed)</option>
                <option value="b_gt_60" ${this.selectedBucket === 'b_gt_60' ? 'selected' : ''}>> 60 Days (Critical)</option>
              </select>
            </div>

            <div class="bl-form-group">
              <label>Ground Source Member</label>
              <select id="modalMemberSelect" class="bl-select">
                <option value="ALL" ${this.selectedMember === 'ALL' ? 'selected' : ''}>All Ground Sources</option>
                ${members.map((m: any) => `<option value="${this.escapeHtml(m.name || m)}" ${this.selectedMember === (m.name || m) ? 'selected' : ''}>${this.escapeHtml(m.name || m)}</option>`).join('')}
              </select>
            </div>

            <div class="bl-form-group">
              <label>Upliner</label>
              <select id="modalUplinerSelect" class="bl-select">
                <option value="ALL" ${this.selectedUpliner === 'ALL' ? 'selected' : ''}>All Upliners</option>
                ${upliners.map((u: any) => `<option value="${this.escapeHtml(u.name || u)}" ${this.selectedUpliner === (u.name || u) ? 'selected' : ''}>${this.escapeHtml(u.name || u)}</option>`).join('')}
              </select>
            </div>

            <div class="bl-form-group">
              <label>City / District</label>
              <select id="modalCitySelect" class="bl-select">
                <option value="ALL" ${this.selectedCity === 'ALL' ? 'selected' : ''}>All Cities / Districts</option>
                ${cities.map((c: any) => `<option value="${this.escapeHtml(c.name || c)}" ${this.selectedCity === (c.name || c) ? 'selected' : ''}>${this.escapeHtml(c.name || c)}</option>`).join('')}
              </select>
            </div>

            <div class="bl-form-group">
              <label>Telecaller</label>
              <select id="modalTelecallerSelect" class="bl-select">
                <option value="ALL" ${this.selectedTelecaller === 'ALL' ? 'selected' : ''}>All Telecallers</option>
                ${telecallers.map((t: any) => `<option value="${this.escapeHtml(t.name || t)}" ${this.selectedTelecaller === (t.name || t) ? 'selected' : ''}>${this.escapeHtml(t.name || t)}</option>`).join('')}
              </select>
            </div>

            <div class="bl-form-group">
              <label>Ground Support Staff</label>
              <select id="modalGroundSupportSelect" class="bl-select">
                <option value="ALL" ${this.selectedGroundSupport === 'ALL' ? 'selected' : ''}>All Ground Staff</option>
                ${groundSupports.map((g: any) => `<option value="${this.escapeHtml(g.name || g)}" ${this.selectedGroundSupport === (g.name || g) ? 'selected' : ''}>${this.escapeHtml(g.name || g)}</option>`).join('')}
              </select>
            </div>
          </div>
          <div class="bl-modal-footer">
            <button class="bl-btn bl-btn-secondary" id="resetModalFiltersBtn">Reset All</button>
            <button class="bl-btn bl-btn-primary" id="applyModalFiltersBtn">Apply Filters</button>
          </div>
        </div>
      </div>
    `;
  }

  private renderLoadingState(): void {
    const area = document.getElementById('blContentArea');
    if (area) {
      area.innerHTML = `
        <div class="bl-empty-state">
          <i class="fas fa-circle-notch fa-spin fa-2x" style="color:#6366f1; margin-bottom:12px;"></i>
          <p>Loading field staff leads...</p>
        </div>
      `;
    }
  }

  private attachEventListeners(): void {
    // Refresh Button
    document.getElementById('refreshBankLeadsBtn')?.addEventListener('click', () => {
      this.loadLeads();
    });

    // Tab buttons
    this.container.querySelectorAll('.bl-tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = (btn as HTMLElement).dataset.tab;
        if (tab) {
          this.currentTab = tab;
          this.render();
        }
      });
    });

    // Search input
    const searchInp = document.getElementById('blSearchInput') as HTMLInputElement;
    searchInp?.addEventListener('keyup', (e) => {
      if (e.key === 'Enter') {
        this.searchQuery = searchInp.value;
        this.loadLeads();
      }
    });
    document.getElementById('clearSearchBtn')?.addEventListener('click', () => {
      this.searchQuery = '';
      this.loadLeads();
    });

    // Toggle filter modal
    document.getElementById('toggleFilterModalBtn')?.addEventListener('click', () => {
      this.showFilterModal = true;
      this.render();
    });
    document.getElementById('closeFilterModalBtn')?.addEventListener('click', () => {
      this.showFilterModal = false;
      this.render();
    });
    document.getElementById('filterModalOverlay')?.addEventListener('click', (e) => {
      if ((e.target as HTMLElement).id === 'filterModalOverlay') {
        this.showFilterModal = false;
        this.render();
      }
    });

    // Apply modal filters
    document.getElementById('applyModalFiltersBtn')?.addEventListener('click', () => {
      this.selectedBank = (document.getElementById('modalBankSelect') as HTMLSelectElement)?.value || 'ALL';
      this.selectedBucket = (document.getElementById('modalBucketSelect') as HTMLSelectElement)?.value || 'ALL';
      this.selectedMember = (document.getElementById('modalMemberSelect') as HTMLSelectElement)?.value || 'ALL';
      this.selectedUpliner = (document.getElementById('modalUplinerSelect') as HTMLSelectElement)?.value || 'ALL';
      this.selectedCity = (document.getElementById('modalCitySelect') as HTMLSelectElement)?.value || 'ALL';
      this.selectedTelecaller = (document.getElementById('modalTelecallerSelect') as HTMLSelectElement)?.value || 'ALL';
      this.selectedGroundSupport = (document.getElementById('modalGroundSupportSelect') as HTMLSelectElement)?.value || 'ALL';
      this.showFilterModal = false;
      this.loadLeads();
    });

    // Reset modal filters
    document.getElementById('resetModalFiltersBtn')?.addEventListener('click', () => {
      this.selectedBank = 'ALL';
      this.selectedBucket = 'ALL';
      this.selectedMember = 'ALL';
      this.selectedUpliner = 'ALL';
      this.selectedCity = 'ALL';
      this.selectedTelecaller = 'ALL';
      this.selectedGroundSupport = 'ALL';
      this.searchQuery = '';
      this.showFilterModal = false;
      this.loadLeads();
    });

    document.getElementById('resetFiltersBtn')?.addEventListener('click', () => {
      this.selectedBank = 'ALL';
      this.selectedBucket = 'ALL';
      this.selectedMember = 'ALL';
      this.selectedUpliner = 'ALL';
      this.selectedCity = 'ALL';
      this.selectedTelecaller = 'ALL';
      this.selectedGroundSupport = 'ALL';
      this.searchQuery = '';
      this.loadLeads();
    });

    // Toggle eye button for revealing phone numbers
    this.container.querySelectorAll('.toggle-phone-mask').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const phoneKey = (btn as HTMLElement).dataset.phoneKey;
        if (phoneKey) {
          if (this.revealedPhones.has(phoneKey)) {
            this.revealedPhones.delete(phoneKey);
          } else {
            this.revealedPhones.add(phoneKey);
          }
          this.render();
        }
      });
    });

    // Expand / collapse lead details
    this.container.querySelectorAll('.toggle-lead-expand').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const leadId = parseInt((btn as HTMLElement).dataset.leadId || '0');
        if (leadId) {
          if (this.expandedLeadIds.has(leadId)) {
            this.expandedLeadIds.delete(leadId);
          } else {
            this.expandedLeadIds.add(leadId);
          }
          this.render();
        }
      });
    });

    // Expand / collapse group details
    this.container.querySelectorAll('.toggle-group-expand').forEach(el => {
      el.addEventListener('click', () => {
        const key = (el as HTMLElement).dataset.groupKey;
        if (key) {
          if (this.expandedGroupIds.has(key)) {
            this.expandedGroupIds.delete(key);
          } else {
            this.expandedGroupIds.add(key);
          }
          this.render();
        }
      });
    });

    // Open Doc actions (DISCOM & Bank)
    this.container.querySelectorAll('.open-doc-action').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const leadId = (btn as HTMLElement).dataset.leadId;
        const docType = (btn as HTMLElement).dataset.type;
        if (leadId) {
          routerService.navigate('staff-leads' as any, { lead_id: leadId, tab: docType === 'bank' ? 'bank_docs' : 'discom_docs' });
        }
      });
    });

    // Open CRM Lead
    this.container.querySelectorAll('.view-crm-lead').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const leadId = (btn as HTMLElement).dataset.leadId;
        if (leadId) {
          routerService.navigate('staff-leads' as any, { lead_id: leadId });
        }
      });
    });

    // Unified WhatsApp Send Modal (Scanned Bot Default + Signature Tracking)
    this.container.querySelectorAll('.open-wa-modal').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const phone = (btn as HTMLElement).dataset.phone || '';
        const name = (btn as HTMLElement).dataset.name || 'Customer';
        const leadId = (btn as HTMLElement).dataset.leadId || '';
        const context = (btn as HTMLElement).dataset.context || '';
        if (phone) {
          unifiedWAModal.open({
            phone,
            name,
            leadId,
            context
          });
        }
      });
    });
  }

  private getStyles(): string {
    return `
      <style>
        .bank-leads-page { padding-bottom: 90px; }
        
        .bl-banner {
          background: linear-gradient(135deg, #1e3a5f, #0f2240);
          border-radius: 12px;
          padding: 14px 16px;
          margin: 0 16px 12px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          color: #fff;
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .bl-banner-title {
          font-size: 16px;
          font-weight: 700;
          margin: 0;
          display: flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;
        }
        .bl-banner-sub {
          font-size: 11px;
          color: rgba(255,255,255,0.7);
          margin: 3px 0 0;
        }
        .bl-role-badge {
          font-size: 10px;
          font-weight: 700;
          padding: 2px 8px;
          border-radius: 12px;
          text-transform: uppercase;
        }
        .bl-role-badge.manager { background: #059669; color: #fff; }
        .bl-role-badge.staff { background: #2563eb; color: #fff; }
        .bl-refresh-btn {
          background: rgba(255,255,255,0.12);
          border: 1px solid rgba(255,255,255,0.2);
          color: #fff;
          width: 36px;
          height: 36px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
        }

        /* Tabs Scroll */
        .bl-tabs-container {
          padding: 0 16px;
          margin-bottom: 12px;
        }
        .bl-tabs-scroll {
          display: flex;
          gap: 8px;
          overflow-x: auto;
          padding-bottom: 4px;
          -webkit-overflow-scrolling: touch;
        }
        .bl-tabs-scroll::-webkit-scrollbar { display: none; }
        .bl-tab-btn {
          background: rgba(255,255,255,0.06);
          border: 1px solid rgba(255,255,255,0.12);
          border-radius: 20px;
          padding: 8px 14px;
          font-size: 12px;
          font-weight: 600;
          color: rgba(255,255,255,0.75);
          white-space: nowrap;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 4px;
          transition: all 0.2s;
        }
        .bl-tab-btn.active {
          background: #4f46e5;
          color: #fff;
          border-color: #6366f1;
          box-shadow: 0 2px 8px rgba(79,70,229,0.4);
        }
        .bl-tab-btn.warning.active {
          background: #d97706;
          border-color: #f59e0b;
        }
        .bl-tab-btn.purple.active {
          background: #7c3aed;
          border-color: #8b5cf6;
        }
        .bl-tab-btn.info.active {
          background: #0284c7;
          border-color: #38bdf8;
        }
        .bl-tab-btn.teal.active {
          background: #0d9488;
          border-color: #14b8a6;
        }
        .bl-tab-btn.emerald.active {
          background: #059669;
          border-color: #10b981;
        }
        .bl-tab-badge {
          background: rgba(0,0,0,0.25);
          border-radius: 10px;
          padding: 1px 6px;
          font-size: 10px;
        }

        /* Metrics Grid */
        .bl-metrics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(105px, 1fr));
          gap: 8px;
          padding: 0 16px;
          margin-bottom: 12px;
        }
        .bl-metric-card {
          background: rgba(255,255,255,0.05);
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 8px;
          padding: 8px 10px;
          display: flex;
          flex-direction: column;
        }
        .bl-metric-card.highlight {
          background: rgba(99,102,241,0.12);
          border-color: rgba(99,102,241,0.3);
        }
        .bl-metric-label {
          font-size: 10px;
          color: rgba(255,255,255,0.6);
          font-weight: 600;
          text-transform: uppercase;
          margin-bottom: 2px;
        }
        .bl-metric-val {
          font-size: 16px;
          font-weight: 800;
          color: #fff;
        }
        .text-success { color: #34d399 !important; }
        .text-info { color: #38bdf8 !important; }
        .text-warning { color: #fbbf24 !important; }
        .text-danger { color: #f87171 !important; }

        /* Search & Filter Bar */
        .bl-search-bar {
          display: flex;
          gap: 8px;
          padding: 0 16px;
          margin-bottom: 12px;
        }
        .bl-search-input-wrap {
          flex: 1;
          position: relative;
        }
        .bl-search-icon {
          position: absolute;
          left: 12px;
          top: 50%;
          transform: translateY(-50%);
          color: rgba(255,255,255,0.4);
          font-size: 13px;
        }
        .bl-search-input {
          width: 100%;
          background: rgba(255,255,255,0.08);
          border: 1px solid rgba(255,255,255,0.15);
          border-radius: 8px;
          padding: 10px 32px 10px 34px;
          font-size: 13px;
          color: #fff;
          box-sizing: border-box;
        }
        .bl-search-input:focus {
          outline: none;
          border-color: #6366f1;
          background: rgba(255,255,255,0.12);
        }
        .bl-clear-search {
          position: absolute;
          right: 10px;
          top: 50%;
          transform: translateY(-50%);
          background: none;
          border: none;
          color: rgba(255,255,255,0.5);
          cursor: pointer;
          font-size: 14px;
        }
        .bl-filter-toggle-btn {
          background: rgba(255,255,255,0.08);
          border: 1px solid rgba(255,255,255,0.15);
          border-radius: 8px;
          color: #fff;
          font-size: 13px;
          font-weight: 600;
          padding: 0 14px;
          display: flex;
          align-items: center;
          gap: 6px;
          cursor: pointer;
          position: relative;
        }
        .bl-filter-toggle-btn.active {
          background: rgba(99,102,241,0.25);
          border-color: #6366f1;
          color: #a5b4fc;
        }
        .bl-filter-dot {
          width: 8px;
          height: 8px;
          background: #ef4444;
          border-radius: 50%;
          position: absolute;
          top: 6px;
          right: 6px;
        }

        /* Leads List */
        .bl-leads-list {
          padding: 0 16px;
        }
        .bl-leads-count-bar {
          font-size: 12px;
          color: rgba(255,255,255,0.6);
          margin-bottom: 8px;
        }
        .bl-card {
          background: #1e293b;
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 12px;
          padding: 14px;
          margin-bottom: 14px;
          box-shadow: 0 2px 10px rgba(0,0,0,0.18);
        }
        .bl-card-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 8px;
          gap: 8px;
        }
        .bl-source-tag {
          display: inline-block;
          font-size: 11px;
          font-weight: 700;
          color: #f59e0b;
          margin-bottom: 2px;
        }
        .bl-customer-name {
          font-size: 15px;
          font-weight: 700;
          color: #fff;
          margin: 0 0 2px;
        }
        .bl-index-num {
          color: #94a3b8;
          font-size: 13px;
        }
        .bl-loc-line {
          font-size: 11px;
          color: rgba(255,255,255,0.65);
        }

        .bl-card-badge-wrap {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 4px;
        }
        .bl-days-badge {
          font-size: 11px;
          font-weight: 800;
          padding: 3px 8px;
          border-radius: 10px;
          white-space: nowrap;
        }
        .days-normal { background: #1e3a8a; color: #93c5fd; }
        .days-info { background: #0c4a6e; color: #7dd3fc; }
        .days-warning { background: #78350f; color: #fde68a; }
        .days-danger { background: #7f1d1d; color: #fca5a5; }

        .bl-stage-pill {
          font-size: 10px;
          font-weight: 700;
          background: rgba(255,255,255,0.08);
          color: #cbd5e1;
          padding: 2px 6px;
          border-radius: 6px;
          text-transform: uppercase;
        }

        /* Phone & Direct Call Box */
        .bl-phone-action-box {
          background: rgba(15, 23, 42, 0.6);
          border: 1px solid rgba(255,255,255,0.08);
          border-radius: 8px;
          padding: 8px 10px;
          margin-bottom: 10px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
        }
        .bl-phone-left {
          display: flex;
          flex-direction: column;
        }
        .bl-phone-lbl {
          font-size: 10px;
          color: rgba(255,255,255,0.5);
          font-weight: 600;
          text-transform: uppercase;
        }
        .bl-phone-val-wrap {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-top: 1px;
        }
        .bl-phone-display {
          font-size: 13px;
          font-weight: 700;
          letter-spacing: 0.5px;
        }
        .bl-phone-display.masked {
          color: #cbd5e1;
          font-family: monospace;
        }
        .bl-phone-display.revealed {
          color: #60a5fa;
        }
        .bl-phone-display.small {
          font-size: 11px;
        }
        .bl-eye-toggle-btn {
          background: rgba(255,255,255,0.1);
          border: 1px solid rgba(255,255,255,0.2);
          color: #cbd5e1;
          border-radius: 4px;
          padding: 2px 6px;
          font-size: 11px;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          justify-content: center;
        }
        .bl-eye-toggle-btn.mini {
          padding: 1px 4px;
          font-size: 9px;
        }
        .bl-direct-call-actions {
          display: flex;
          gap: 6px;
        }
        .bl-btn-call {
          background: #0284c7;
          color: #fff;
          font-size: 12px;
          font-weight: 700;
          padding: 6px 12px;
          border-radius: 6px;
          text-decoration: none;
          display: inline-flex;
          align-items: center;
          box-shadow: 0 2px 6px rgba(2,132,199,0.3);
        }
        .bl-btn-wa {
          background: #16a34a;
          color: #fff;
          font-size: 13px;
          width: 32px;
          height: 32px;
          border-radius: 6px;
          text-decoration: none;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 2px 6px rgba(22,163,74,0.3);
        }

        .bl-info-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.06);
          border-radius: 8px;
          padding: 10px;
          margin-bottom: 10px;
        }
        .bl-info-item {
          display: flex;
          flex-direction: column;
        }
        .bl-info-lbl {
          font-size: 10px;
          color: rgba(255,255,255,0.5);
          font-weight: 600;
          text-transform: uppercase;
          margin-bottom: 2px;
        }
        .bl-info-val {
          font-size: 12px;
          color: #fff;
          font-weight: 500;
        }
        .bl-info-val.highlight {
          color: #93c5fd;
        }

        /* Nested Contact & Expandable Box */
        .bl-expanded-details {
          background: rgba(0,0,0,0.25);
          border-radius: 8px;
          padding: 10px;
          margin-bottom: 10px;
          font-size: 12px;
        }
        .bl-nested-contact-box {
          background: rgba(245, 158, 11, 0.08);
          border: 1px solid rgba(245, 158, 11, 0.25);
          border-radius: 6px;
          padding: 8px;
          margin-bottom: 8px;
        }
        .bl-nested-title {
          font-size: 11px;
          font-weight: 700;
          color: #f59e0b;
          margin-bottom: 4px;
        }
        .bl-nested-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          font-size: 11px;
          color: #fff;
        }
        .bl-mini-call-btn {
          font-size: 10px;
          font-weight: 700;
          padding: 2px 8px;
          border-radius: 4px;
          text-decoration: none;
          display: inline-flex;
          align-items: center;
        }
        .bl-mini-call-btn.source { background: #f59e0b; color: #000; }
        .bl-mini-call-btn.upliner { background: #d97706; color: #fff; }
        .bl-mini-call-btn.gs { background: #10b981; color: #fff; }

        .bl-details-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 5px 0;
          border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .bl-details-row:last-child { border-bottom: none; }
        .bl-det-lbl { color: rgba(255,255,255,0.6); }
        .bl-det-val { color: #fff; font-weight: 600; text-align: right; }
        .bl-notes-box { margin-top: 6px; }
        .bl-notes-text { color: rgba(255,255,255,0.8); font-size: 11px; margin: 2px 0 0; }

        /* Card Footer & Document Action Buttons */
        .bl-card-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 8px;
          border-top: 1px solid rgba(255,255,255,0.08);
          padding-top: 10px;
          flex-wrap: wrap;
        }
        .bl-doc-actions {
          display: flex;
          gap: 6px;
        }
        .bl-doc-btn {
          padding: 5px 9px;
          border-radius: 6px;
          font-size: 11px;
          font-weight: 700;
          cursor: pointer;
          border: none;
          text-decoration: none;
          display: inline-flex;
          align-items: center;
        }
        .bl-doc-btn.discom { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }
        .bl-doc-btn.bank { background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4); }
        .bl-doc-btn.map { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }

        .bl-expand-actions {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .bl-expand-btn {
          background: none;
          border: none;
          color: #a5b4fc;
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
        }
        .bl-action-btn {
          background: rgba(99,102,241,0.2);
          border: 1px solid rgba(99,102,241,0.4);
          color: #a5b4fc;
          border-radius: 6px;
          padding: 6px 10px;
          font-size: 11px;
          font-weight: 600;
          cursor: pointer;
        }

        /* Summary Cards */
        .bl-summary-list { padding: 0 16px; }
        .bl-summary-card {
          background: #1e293b;
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 10px;
          margin-bottom: 10px;
          overflow: hidden;
        }
        .bl-summary-hdr {
          padding: 12px 14px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          cursor: pointer;
        }
        .bl-sum-title {
          font-size: 14px;
          font-weight: 700;
          color: #fff;
          margin: 0;
        }
        .bl-sum-sub {
          font-size: 11px;
          color: rgba(255,255,255,0.6);
        }
        .bl-sum-right {
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .bl-sum-badge {
          font-size: 11px;
          font-weight: 700;
          padding: 3px 8px;
          border-radius: 8px;
        }
        .bl-sum-badge.count { background: #3b82f6; color: #fff; }
        .bl-sum-badge.amount { background: #10b981; color: #fff; }
        .bl-quick-btn {
          width: 26px;
          height: 26px;
          border-radius: 50%;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          font-size: 11px;
          text-decoration: none;
        }
        .bl-quick-btn.call { background: #0284c7; color: #fff; }
        .bl-quick-btn.wa { background: #16a34a; color: #fff; }

        .bl-summary-items {
          background: rgba(0,0,0,0.25);
          border-top: 1px solid rgba(255,255,255,0.06);
          padding: 8px 12px;
        }
        .bl-sum-subitem {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 6px 0;
          border-bottom: 1px solid rgba(255,255,255,0.04);
        }
        .bl-sum-subitem:last-child { border-bottom: none; }

        /* Empty State */
        .bl-empty-state {
          text-align: center;
          padding: 40px 20px;
          color: rgba(255,255,255,0.6);
        }
        .bl-empty-state h4 { color: #fff; font-size: 16px; margin: 0 0 6px; }

        /* Modal */
        .bl-modal-overlay {
          position: fixed;
          inset: 0;
          background: rgba(0,0,0,0.7);
          z-index: 9999;
          display: flex;
          align-items: flex-end;
          justify-content: center;
        }
        .bl-modal {
          background: #1e293b;
          border-top-left-radius: 16px;
          border-top-right-radius: 16px;
          width: 100%;
          max-height: 85vh;
          display: flex;
          flex-direction: column;
          box-shadow: 0 -4px 20px rgba(0,0,0,0.3);
        }
        .bl-modal-header {
          padding: 16px;
          border-bottom: 1px solid rgba(255,255,255,0.1);
          display: flex;
          justify-content: space-between;
          align-items: center;
          color: #fff;
        }
        .bl-modal-header h4 { font-size: 15px; font-weight: 700; margin: 0; }
        .bl-modal-close {
          background: none;
          border: none;
          color: rgba(255,255,255,0.6);
          font-size: 18px;
          cursor: pointer;
        }
        .bl-modal-body {
          padding: 16px;
          overflow-y: auto;
          flex: 1;
        }
        .bl-form-group {
          margin-bottom: 14px;
        }
        .bl-form-group label {
          display: block;
          font-size: 12px;
          color: rgba(255,255,255,0.7);
          font-weight: 600;
          margin-bottom: 6px;
        }
        .bl-select {
          width: 100%;
          background: rgba(255,255,255,0.08);
          border: 1px solid rgba(255,255,255,0.18);
          border-radius: 8px;
          color: #fff;
          padding: 10px 12px;
          font-size: 13px;
        }
        .bl-select option { background: #1e293b; color: #fff; }
        .bl-modal-footer {
          padding: 14px 16px;
          border-top: 1px solid rgba(255,255,255,0.1);
          display: flex;
          gap: 10px;
        }
        .bl-btn {
          flex: 1;
          padding: 12px;
          border-radius: 8px;
          font-size: 13px;
          font-weight: 700;
          cursor: pointer;
          border: none;
        }
        .bl-btn-primary { background: #4f46e5; color: #fff; }
        .bl-btn-secondary { background: rgba(255,255,255,0.1); color: #fff; }
      </style>
    `;
  }
}
