/**
 * Staff CRM Dashboard Page
 * DC Protocol: DC_MOBILE_STAFF_CRM_001
 * Full web parity with 4 tabs: My Performance, Team Performance, Team Breakdown, All Performance
 * Includes filters: Date, Source, Category, Company, Team Manager
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import { routerService } from '../services/router.service';

interface Company {
  id: number;
  company_code: string;
  company_name: string;
}

interface Category {
  id: number;
  name: string;
}

interface Source {
  id: number;
  name: string;
}

interface Manager {
  id: number;
  employee_id: string;
  name: string;
}

interface PerformanceRow {
  sno: number;
  employee_id: string;
  employee_name: string;
  overall: {
    new_leads: number;
    overall_leads: number;
    self_generated_leads: number;
  };
  status_wise: {
    in_progress: number;
    deal_closed: number;
    on_hold: number;
    lost_leads: number;
  };
  revenue: {
    generated: number;
    lost: number;
  };
}

interface BreakdownRow {
  sno: number;
  employee_id: number;
  emp_code: string;
  employee_name: string;
  reporting_manager: string | null;
  avg_daily_talk_time: number;
  total_calls: number;
  as_primary_owner: {
    new: number;
    contacted: number;
    qualified: number;
    won: number;
    lost: number;
    on_hold: number;
    total: number;
    revenue_total: number;
    revenue_received: number;
    revenue_balance: number;
  };
  as_handler: {
    new: number;
    contacted: number;
    qualified: number;
    won: number;
    lost: number;
    on_hold: number;
    total: number;
    revenue_total: number;
    revenue_received: number;
    revenue_balance: number;
  };
}

interface PerformanceTotals {
  new_leads: number;
  overall_leads: number;
  self_generated_leads: number;
  in_progress: number;
  deal_closed: number;
  on_hold: number;
  lost_leads: number;
  revenue_generated: number;
  revenue_lost: number;
}

interface QuickStats {
  total: number;
  new: number;
  in_progress: number;
  won: number;
  lost: number;
  on_hold: number;
  today_followups: number;
  overdue: number;
}

export class StaffCRMPage {
  private container: HTMLElement;
  private loading: boolean = true;
  // DC Protocol (Feb 2026): Removed 'team' and 'all' tabs to match web - only 'my' and 'breakdown' remain
  private activeTab: 'my' | 'breakdown' = 'my';
  
  private companies: Company[] = [];
  private categories: Category[] = [];
  private sources: Source[] = [];
  private managers: Manager[] = [];
  private departments: Array<{id: number; name: string}> = [];
  
  private selectedCompanyId: number | null = null;
  private startDate: string = '';
  private endDate: string = '';
  private selectedSourceId: number | null = null;
  private selectedCategoryId: number | null = null;
  private selectedManagerId: number | null = null;
  private selectedDepartmentId: number | null = null;
  private employeeSearch: string = '';
  
  private performanceData: PerformanceRow[] = [];
  private breakdownData: BreakdownRow[] = [];
  private totals: PerformanceTotals | null = null;
  private quickStats: QuickStats | null = null;
  private isLeader: boolean = false;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    try {
      await this.loadFiltersData();
      await this.loadPerformanceData();
    } catch (error) {
      console.error('[StaffCRM] Initialization failed:', error);
      this.loading = false;
      this.updateContent();
    }
  }

  private async loadFiltersData(): Promise<void> {
    try {
      // DC Protocol (Feb 2026): Load companies first to get company_id for other filters
      const companiesRes = await apiService.get<any>('/staff/accounts/companies');
      
      if (companiesRes.success && companiesRes.data) {
        this.companies = companiesRes.data.companies || companiesRes.data || [];
        if (this.companies.length > 0 && !this.selectedCompanyId) {
          this.selectedCompanyId = this.companies[0].id;
        }
      }
      
      // DC Protocol (Feb 2026): Load categories and sources with company_id
      // Sources endpoint requires company_id, categories accepts optional company_id
      if (this.selectedCompanyId) {
        const [categoriesRes, sourcesRes, profileRes] = await Promise.all([
          apiService.get<any>(`/crm/signup/categories?company_id=${this.selectedCompanyId}`),
          apiService.get<any>(`/crm/sources?company_id=${this.selectedCompanyId}`),
          apiService.get<any>('/staff/auth/me')
        ]);
        
        if (categoriesRes.success && categoriesRes.data) {
          this.categories = categoriesRes.data.data || categoriesRes.data.categories || categoriesRes.data || [];
        }
        if (sourcesRes.success && sourcesRes.data) {
          this.sources = sourcesRes.data.data || sourcesRes.data || [];
        }
        // DC Protocol (Feb 2026): Pre-determine isLeader from profile to show Team Breakdown tab
        if (profileRes.success && profileRes.data) {
          this.isLeader = profileRes.data.is_leader || profileRes.data.has_direct_reports || false;
        }
      }
    } catch (error) {
      console.error('[StaffCRM] Failed to load filters:', error);
    }
    
    this.updateFiltersUI();
    
    // DC Protocol (Feb 2026): Load departments for breakdown filter
    if (this.selectedCompanyId) {
      await this.loadDepartments();
    }
  }

  private async loadDepartments(): Promise<void> {
    if (!this.selectedCompanyId) {
      this.departments = [];
      return;
    }
    try {
      const response = await apiService.get<any>(`/staff/departments?company_id=${this.selectedCompanyId}`);
      if (response.success && response.data) {
        this.departments = response.data.departments || response.data || [];
      }
    } catch (error) {
      console.error('[StaffCRM] Failed to load departments:', error);
      this.departments = [];
    }
  }

  private async loadPerformanceData(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const scope = this.activeTab === 'breakdown' ? 'team' : this.activeTab;
      
      if (this.activeTab === 'breakdown') {
        const params = new URLSearchParams();
        params.append('company_id', this.selectedCompanyId?.toString() || 'all');
        if (this.startDate) params.append('start_date', this.startDate);
        if (this.endDate) params.append('end_date', this.endDate);
        if (this.selectedManagerId) params.append('manager_id', this.selectedManagerId.toString());
        if (this.selectedDepartmentId) params.append('department_id', this.selectedDepartmentId.toString());
        if (this.employeeSearch) params.append('employee_search', this.employeeSearch);
        
        const response = await apiService.get<any>(`/crm/team-performance-breakdown?${params.toString()}`);
        if (response.success && response.data) {
          this.breakdownData = response.data.performance || [];
          this.isLeader = response.data.is_leader || false;
        }
      } else {
        const params = new URLSearchParams();
        params.append('scope', scope);
        if (this.selectedCompanyId) params.append('company_id', this.selectedCompanyId.toString());
        if (this.startDate) params.append('start_date', this.startDate);
        if (this.endDate) params.append('end_date', this.endDate);
        if (this.selectedSourceId) params.append('source_id', this.selectedSourceId.toString());
        if (this.selectedCategoryId) params.append('category_id', this.selectedCategoryId.toString());
        if (this.selectedManagerId) params.append('manager_id', this.selectedManagerId.toString());
        
        const response = await apiService.get<any>(`/crm/performance-summary?${params.toString()}`);
        if (response.success && response.data) {
          this.performanceData = response.data.performance || [];
          this.totals = response.data.totals || null;
          this.managers = response.data.available_managers || [];
          this.isLeader = response.data.is_leader || false;
        }
      }
      
      const statsRes = await apiService.get<any>('/crm/my-dashboard');
      if (statsRes.success && statsRes.data) {
        this.quickStats = {
          total: statsRes.data.total_leads || 0,
          new: statsRes.data.new_leads || 0,
          in_progress: statsRes.data.in_progress || 0,
          won: statsRes.data.converted || 0,
          lost: statsRes.data.lost || 0,
          on_hold: statsRes.data.on_hold || 0,
          today_followups: statsRes.data.today_followups || 0,
          overdue: statsRes.data.overdue || 0
        };
      }
    } catch (error) {
      console.error('[StaffCRM] Failed to load performance:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'My CRM Dashboard', showBack: true })}
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: 'My CRM Dashboard', showBack: true });
  }

  private updateFiltersUI(): void {
    const companySelect = document.getElementById('companyFilter') as HTMLSelectElement;
    if (companySelect) {
      companySelect.innerHTML = this.companies.map(c => 
        `<option value="${c.id}" ${c.id === this.selectedCompanyId ? 'selected' : ''}>${c.company_name}</option>`
      ).join('');
    }
    
    const categorySelect = document.getElementById('categoryFilter') as HTMLSelectElement;
    if (categorySelect) {
      categorySelect.innerHTML = `<option value="">All Categories</option>` + 
        this.categories.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
    }
    
    const sourceSelect = document.getElementById('sourceFilter') as HTMLSelectElement;
    if (sourceSelect) {
      sourceSelect.innerHTML = `<option value="">All Sources</option>` + 
        this.sources.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
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
      <div class="crm-dashboard">
        <!-- Company Selector -->
        <div class="company-selector card-sm">
          <label>Company:</label>
          <select id="companyFilter" class="form-select">
            ${this.companies.map(c => 
              `<option value="${c.id}" ${c.id === this.selectedCompanyId ? 'selected' : ''}>${c.company_name}</option>`
            ).join('')}
          </select>
        </div>

        <!-- Tab Navigation - DC Protocol (Feb 2026): Only 'my' and 'breakdown' tabs to match web -->
        <div class="crm-tabs">
          <button class="tab-btn ${this.activeTab === 'my' ? 'active' : ''}" data-tab="my">
            <span class="tab-icon">👤</span> My Performance
          </button>
          ${this.isLeader ? `
          <button class="tab-btn ${this.activeTab === 'breakdown' ? 'active' : ''}" data-tab="breakdown">
            <span class="tab-icon">📊</span> Team Breakdown
          </button>
          ` : ''}
        </div>

        <!-- Filters Section -->
        <div class="filter-section card">
          <div class="filter-header">
            <span class="filter-icon">🔍</span> Filter Performance
            <button class="reset-btn" id="resetFilters">↺ Reset</button>
          </div>
          <div class="filter-grid">
            <div class="filter-item">
              <label>From Date</label>
              <input type="date" id="startDate" class="form-input" value="${this.startDate}">
            </div>
            <div class="filter-item">
              <label>To Date</label>
              <input type="date" id="endDate" class="form-input" value="${this.endDate}">
            </div>
            <div class="filter-item">
              <label>Source</label>
              <select id="sourceFilter" class="form-select">
                <option value="">All Sources</option>
                ${this.sources.map(s => `<option value="${s.id}" ${s.id === this.selectedSourceId ? 'selected' : ''}>${s.name}</option>`).join('')}
              </select>
            </div>
            <div class="filter-item">
              <label>Category</label>
              <select id="categoryFilter" class="form-select">
                <option value="">All Categories</option>
                ${this.categories.map(c => `<option value="${c.id}" ${c.id === this.selectedCategoryId ? 'selected' : ''}>${c.name}</option>`).join('')}
              </select>
            </div>
            ${this.activeTab === 'breakdown' ? `
              <div class="filter-item">
                <label>Department</label>
                <select id="departmentFilter" class="form-select">
                  <option value="">All Departments</option>
                  ${this.departments.map(d => `<option value="${d.id}" ${d.id === this.selectedDepartmentId ? 'selected' : ''}>${d.name}</option>`).join('')}
                </select>
              </div>
            ` : ''}
            ${this.activeTab !== 'my' && this.managers.length > 0 ? `
              <div class="filter-item">
                <label>Team Manager</label>
                <select id="managerFilter" class="form-select">
                  <option value="">All Managers</option>
                  ${this.managers.map(m => `<option value="${m.id}" ${m.id === this.selectedManagerId ? 'selected' : ''}>${m.name}</option>`).join('')}
                </select>
              </div>
            ` : ''}
          </div>
          <button class="btn btn-primary apply-btn" id="applyFilters">
            🔍 Apply Filters
          </button>
        </div>

        <!-- Performance Table Section -->
        ${this.activeTab === 'breakdown' ? this.renderBreakdownTable() : this.renderPerformanceTable()}

        <!-- Quick Stats Cards -->
        ${this.renderQuickStats()}

        <!-- Quick Actions -->
        <h4 class="section-title">Quick Actions</h4>
        <div class="crm-actions">
          <button class="action-card card" data-page="staff-leads">
            <span class="action-icon">👥</span>
            <span>My Leads</span>
          </button>
          <button class="action-card card" data-page="staff-team-leads">
            <span class="action-icon">📊</span>
            <span>Team Leads</span>
          </button>
        </div>
      </div>
    `;

    this.attachEventListeners();
  }

  private renderPerformanceTable(): string {
    const data = this.performanceData;
    
    return `
      <div class="performance-section card">
        <div class="section-header">
          <h4>${this.getTabTitle()} Summary</h4>
          <span class="employee-count">${data.length} employees</span>
        </div>
        
        ${data.length > 0 ? `
          <div class="table-responsive">
            <table class="data-table performance-table">
              <thead>
                <tr>
                  <th rowspan="2" class="sticky-col">#</th>
                  <th rowspan="2" class="sticky-col-2">Employee Name</th>
                  <th colspan="3" class="header-group overall">OVERALL</th>
                  <th colspan="4" class="header-group status">STATUS WISE</th>
                  <th colspan="2" class="header-group revenue">REVENUE</th>
                </tr>
                <tr>
                  <th class="sub-header">New Leads</th>
                  <th class="sub-header">Overall Leads</th>
                  <th class="sub-header">Self Generated</th>
                  <th class="sub-header">In Progress</th>
                  <th class="sub-header">Deal Closed</th>
                  <th class="sub-header">On Hold</th>
                  <th class="sub-header">Lost</th>
                  <th class="sub-header">Generated</th>
                  <th class="sub-header">Lost</th>
                </tr>
              </thead>
              <tbody>
                ${data.map(row => `
                  <tr>
                    <td class="sticky-col">${row.sno}</td>
                    <td class="sticky-col-2">
                      <div class="employee-cell">
                        <span class="emp-name">${row.employee_name}</span>
                        <span class="emp-code">${row.employee_id}</span>
                      </div>
                    </td>
                    <td class="num-cell">${row.overall.new_leads}</td>
                    <td class="num-cell">${row.overall.overall_leads}</td>
                    <td class="num-cell">${row.overall.self_generated_leads}</td>
                    <td class="num-cell">${row.status_wise.in_progress}</td>
                    <td class="num-cell success">${row.status_wise.deal_closed}</td>
                    <td class="num-cell warning">${row.status_wise.on_hold}</td>
                    <td class="num-cell danger">${row.status_wise.lost_leads}</td>
                    <td class="num-cell currency success">₹${this.formatCurrency(row.revenue.generated)}</td>
                    <td class="num-cell currency danger">₹${this.formatCurrency(row.revenue.lost)}</td>
                  </tr>
                `).join('')}
              </tbody>
              ${this.totals ? `
                <tfoot>
                  <tr class="totals-row">
                    <td colspan="2" class="sticky-col">TOTAL</td>
                    <td class="num-cell">${this.totals.new_leads}</td>
                    <td class="num-cell">${this.totals.overall_leads}</td>
                    <td class="num-cell">${this.totals.self_generated_leads}</td>
                    <td class="num-cell">${this.totals.in_progress}</td>
                    <td class="num-cell success">${this.totals.deal_closed}</td>
                    <td class="num-cell warning">${this.totals.on_hold}</td>
                    <td class="num-cell danger">${this.totals.lost_leads}</td>
                    <td class="num-cell currency success">₹${this.formatCurrency(this.totals.revenue_generated)}</td>
                    <td class="num-cell currency danger">₹${this.formatCurrency(this.totals.revenue_lost)}</td>
                  </tr>
                </tfoot>
              ` : ''}
            </table>
          </div>
        ` : `
          <div class="empty-state">
            <div class="empty-icon">📊</div>
            <p>No Performance Data</p>
            <span>Apply filters to view performance summary</span>
          </div>
        `}
      </div>
    `;
  }

  private renderBreakdownTable(): string {
    const data = this.breakdownData;
    
    return `
      <div class="performance-section card">
        <div class="section-header">
          <h4>Team Performance Breakdown</h4>
          <span class="employee-count">${data.length} employees</span>
        </div>
        
        ${data.length > 0 ? `
          <div class="table-responsive">
            <table class="data-table breakdown-table">
              <thead>
                <tr>
                  <th rowspan="2" class="sticky-col">#</th>
                  <th rowspan="2" class="sticky-col-2">Employee</th>
                  <th colspan="9" class="header-group primary-owner">AS PRIMARY OWNER</th>
                  <th colspan="9" class="header-group handler">AS HANDLER (TC/FS/MNR)</th>
                  <th rowspan="2" class="sub-header talk-time">Avg Daily<br>Talk Time</th>
                </tr>
                <tr>
                  <!-- Primary Owner columns -->
                  <th class="sub-header">Total</th>
                  <th class="sub-header">New</th>
                  <th class="sub-header">Progress</th>
                  <th class="sub-header">Won</th>
                  <th class="sub-header">Lost</th>
                  <th class="sub-header">On Hold</th>
                  <th class="sub-header">Revenue</th>
                  <th class="sub-header">Collected</th>
                  <th class="sub-header">Balance</th>
                  <!-- Handler columns -->
                  <th class="sub-header">Total</th>
                  <th class="sub-header">New</th>
                  <th class="sub-header">Progress</th>
                  <th class="sub-header">Won</th>
                  <th class="sub-header">Lost</th>
                  <th class="sub-header">On Hold</th>
                  <th class="sub-header">Revenue</th>
                  <th class="sub-header">Collected</th>
                  <th class="sub-header">Balance</th>
                </tr>
              </thead>
              <tbody>
                ${data.map(row => `
                  <tr>
                    <td class="sticky-col">${row.sno}</td>
                    <td class="sticky-col-2">
                      <div class="employee-cell">
                        <span class="emp-name">${row.employee_name}</span>
                        <span class="emp-code">${row.emp_code || row.employee_id}</span>
                        ${row.reporting_manager ? `<span class="emp-manager">RM: ${row.reporting_manager}</span>` : ''}
                      </div>
                    </td>
                    <!-- Primary Owner -->
                    <td class="num-cell">${row.as_primary_owner.total}</td>
                    <td class="num-cell">${row.as_primary_owner.new}</td>
                    <td class="num-cell">${row.as_primary_owner.contacted + row.as_primary_owner.qualified}</td>
                    <td class="num-cell success">${row.as_primary_owner.won}</td>
                    <td class="num-cell danger">${row.as_primary_owner.lost}</td>
                    <td class="num-cell warning">${row.as_primary_owner.on_hold}</td>
                    <td class="num-cell currency">&#8377;${this.formatCurrency(row.as_primary_owner.revenue_total)}</td>
                    <td class="num-cell currency success">&#8377;${this.formatCurrency(row.as_primary_owner.revenue_received)}</td>
                    <td class="num-cell currency warning">&#8377;${this.formatCurrency(row.as_primary_owner.revenue_balance)}</td>
                    <!-- Handler -->
                    <td class="num-cell">${row.as_handler.total}</td>
                    <td class="num-cell">${row.as_handler.new}</td>
                    <td class="num-cell">${row.as_handler.contacted + row.as_handler.qualified}</td>
                    <td class="num-cell success">${row.as_handler.won}</td>
                    <td class="num-cell danger">${row.as_handler.lost}</td>
                    <td class="num-cell warning">${row.as_handler.on_hold}</td>
                    <td class="num-cell currency">&#8377;${this.formatCurrency(row.as_handler.revenue_total)}</td>
                    <td class="num-cell currency success">&#8377;${this.formatCurrency(row.as_handler.revenue_received)}</td>
                    <td class="num-cell currency warning">&#8377;${this.formatCurrency(row.as_handler.revenue_balance)}</td>
                    <!-- Talk Time -->
                    <td class="num-cell talk-time">${this.fmtTalkTime(row.avg_daily_talk_time || 0)}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        ` : `
          <div class="empty-state">
            <div class="empty-icon">📊</div>
            <p>No Breakdown Data</p>
            <span>Apply filters to view team breakdown</span>
          </div>
        `}
      </div>
    `;
  }

  private renderQuickStats(): string {
    if (!this.quickStats) return '';
    
    return `
      <div class="quick-stats-grid">
        <div class="stat-card total">
          <span class="stat-value">${this.quickStats.total}</span>
          <span class="stat-label">Total Leads</span>
        </div>
        <div class="stat-card new">
          <span class="stat-value">${this.quickStats.new}</span>
          <span class="stat-label">New</span>
        </div>
        <div class="stat-card progress">
          <span class="stat-value">${this.quickStats.in_progress}</span>
          <span class="stat-label">In Progress</span>
        </div>
        <div class="stat-card won">
          <span class="stat-value">${this.quickStats.won}</span>
          <span class="stat-label">Won</span>
        </div>
        <div class="stat-card lost">
          <span class="stat-value">${this.quickStats.lost}</span>
          <span class="stat-label">Lost</span>
        </div>
        <div class="stat-card hold">
          <span class="stat-value">${this.quickStats.on_hold}</span>
          <span class="stat-label">On Hold</span>
        </div>
        <div class="stat-card followup">
          <span class="stat-value">${this.quickStats.today_followups}</span>
          <span class="stat-label">Today's Followups</span>
        </div>
        <div class="stat-card overdue">
          <span class="stat-value">${this.quickStats.overdue}</span>
          <span class="stat-label">Overdue</span>
        </div>
      </div>
    `;
  }

  private getTabTitle(): string {
    // DC Protocol (Feb 2026): Only 'my' and 'breakdown' tabs remain
    switch (this.activeTab) {
      case 'my': return 'My Performance';
      case 'breakdown': return 'Team Breakdown';
      default: return 'Performance';
    }
  }

  private formatCurrency(value: number): string {
    if (value >= 10000000) {
      return (value / 10000000).toFixed(1) + 'Cr';
    } else if (value >= 100000) {
      return (value / 100000).toFixed(1) + 'L';
    } else if (value >= 1000) {
      return (value / 1000).toFixed(1) + 'K';
    }
    return value.toFixed(0);
  }

  private fmtTalkTime(seconds: number): string {
    if (!seconds || seconds <= 0) return '—';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}h ${m}m`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
  }

  private attachEventListeners(): void {
    document.querySelectorAll('.crm-tabs .tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        // DC Protocol (Feb 2026): Only 'my' and 'breakdown' tabs remain
        const tab = btn.getAttribute('data-tab') as 'my' | 'breakdown';
        if (tab && tab !== this.activeTab) {
          this.activeTab = tab;
          this.loadPerformanceData();
        }
      });
    });

    document.getElementById('companyFilter')?.addEventListener('change', async (e) => {
      this.selectedCompanyId = parseInt((e.target as HTMLSelectElement).value) || null;
      // DC Protocol (Feb 2026): Reset filters and reload sources/departments/categories when company changes
      this.selectedDepartmentId = null;
      this.selectedSourceId = null;
      this.selectedCategoryId = null;
      
      // Reload sources and categories for new company
      if (this.selectedCompanyId) {
        try {
          const [categoriesRes, sourcesRes] = await Promise.all([
            apiService.get<any>(`/crm/signup/categories?company_id=${this.selectedCompanyId}`),
            apiService.get<any>(`/crm/sources?company_id=${this.selectedCompanyId}`)
          ]);
          if (categoriesRes.success && categoriesRes.data) {
            this.categories = categoriesRes.data.data || categoriesRes.data.categories || categoriesRes.data || [];
          }
          if (sourcesRes.success && sourcesRes.data) {
            this.sources = sourcesRes.data.data || sourcesRes.data || [];
          }
        } catch (error) {
          console.error('[StaffCRM] Failed to reload filters:', error);
        }
        await this.loadDepartments();
      }
      
      this.updateContent();
    });

    document.getElementById('startDate')?.addEventListener('change', (e) => {
      this.startDate = (e.target as HTMLInputElement).value;
    });

    document.getElementById('endDate')?.addEventListener('change', (e) => {
      this.endDate = (e.target as HTMLInputElement).value;
    });

    document.getElementById('sourceFilter')?.addEventListener('change', (e) => {
      this.selectedSourceId = parseInt((e.target as HTMLSelectElement).value) || null;
    });

    document.getElementById('categoryFilter')?.addEventListener('change', (e) => {
      this.selectedCategoryId = parseInt((e.target as HTMLSelectElement).value) || null;
    });

    document.getElementById('managerFilter')?.addEventListener('change', (e) => {
      this.selectedManagerId = parseInt((e.target as HTMLSelectElement).value) || null;
    });

    // DC Protocol (Feb 2026): Department filter for breakdown tab
    document.getElementById('departmentFilter')?.addEventListener('change', (e) => {
      this.selectedDepartmentId = parseInt((e.target as HTMLSelectElement).value) || null;
    });

    document.getElementById('applyFilters')?.addEventListener('click', () => {
      this.loadPerformanceData();
    });

    document.getElementById('resetFilters')?.addEventListener('click', () => {
      this.startDate = '';
      this.endDate = '';
      this.selectedSourceId = null;
      this.selectedCategoryId = null;
      this.selectedManagerId = null;
      this.selectedDepartmentId = null;
      this.employeeSearch = '';
      this.loadPerformanceData();
    });

    document.querySelectorAll('[data-page]').forEach(btn => {
      btn.addEventListener('click', () => {
        const page = btn.getAttribute('data-page');
        if (page) routerService.navigate(page as any);
      });
    });
  }
}
