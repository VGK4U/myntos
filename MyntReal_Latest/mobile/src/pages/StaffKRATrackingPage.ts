/**
 * Staff KRA Tracking Sheet Page
 * DC Protocol: DC_MOBILE_KRA_TRACKING_002
 * Track KRA progress across employees with INLINE EXPANSION
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface EmployeeKRA {
  employee_id: number;
  employee_name: string;
  emp_code?: string;
  department: string;
  assigned_kras: number;
  completed_kras: number;
  not_completed: number;
  approved: number;
  pending_review: number;
  rejected: number;
}

interface KRAInstance {
  id: number;
  template_name: string;
  instance_date: string;
  completion_status: string;
  manager_review_status: string;
  self_rating: number | null;
  manager_rating: number | null;
}

const SCOPE_OPTIONS = [
  { id: 'self', label: 'My KRAs Only' },
  { id: 'team', label: 'My Team' },
  { id: 'all', label: 'All Employees' }
];

export class StaffKRATrackingPage {
  private container: HTMLElement;
  private employees: EmployeeKRA[] = [];
  private loading: boolean = true;
  private dateFrom: string = '';
  private dateTo: string = '';
  private scope: 'self' | 'team' | 'all' = 'team';
  private employeeSearch: string = '';
  private expandedEmployeeId: number | null = null;
  private employeeKRAs: Map<number, KRAInstance[]> = new Map();
  private loadingKRAs: Set<number> = new Set();
  private isVGKOrEA: boolean = false;
  private hasTeam: boolean = false;

  constructor(container: HTMLElement) {
    this.container = container;
    const now = new Date();
    this.dateFrom = now.toISOString().split('T')[0];
    const twoDaysLater = new Date(now.getTime() + 2 * 24 * 60 * 60 * 1000);
    this.dateTo = twoDaysLater.toISOString().split('T')[0];
  }

  async init(): Promise<void> {
    this.render();
    await this.checkUserPermissions();
    await this.loadTracking();
  }

  private async checkUserPermissions(): Promise<void> {
    try {
      const response = await apiService.get<any>('/staff/auth/me');
      if (response.success && response.data) {
        const profile = response.data;
        // DC Protocol (Feb 2026): Check if user is VGK/EA/Key Leadership for 'all' scope access
        this.isVGKOrEA = profile.is_vgk || profile.is_admin || profile.is_leader || 
          (profile.role && (
            profile.role.hierarchy_level >= 150 ||
            ['HR', 'Executive Assistant', 'Key Leadership', 'VGK4U', 'Supreme'].includes(profile.role.role_name) ||
            ['hr', 'ea', 'kl', 'vgk4u', 'supreme'].includes(profile.role.role_code?.toLowerCase())
          ));
        this.hasTeam = profile.has_direct_reports || profile.is_manager || profile.is_leader || this.isVGKOrEA;
        
        console.log(`[StaffKRATracking] User permissions: isVGKOrEA=${this.isVGKOrEA}, hasTeam=${this.hasTeam}`);
        
        // Update scope options in UI
        this.updateScopeOptions();
      }
    } catch (error) {
      console.error('[StaffKRATracking] Failed to check permissions:', error);
    }
  }

  private updateScopeOptions(): void {
    const scopeSelect = document.getElementById('scopeFilter') as HTMLSelectElement;
    if (scopeSelect) {
      scopeSelect.innerHTML = this.getScopeOptionsHTML();
    }
  }

  private getScopeOptionsHTML(): string {
    const options: Array<{id: string, label: string}> = [
      { id: 'self', label: 'My KRAs Only' }
    ];
    
    // Add team option if user has team or is VGK/EA
    if (this.hasTeam || this.isVGKOrEA) {
      options.push({ id: 'team', label: 'My Team' });
    }
    
    // Add all option only for VGK/EA users
    if (this.isVGKOrEA) {
      options.push({ id: 'all', label: 'All Employees' });
    }
    
    return options.map(o => `<option value="${o.id}" ${this.scope === o.id ? 'selected' : ''}>${o.label}</option>`).join('');
  }

  private async loadTracking(): Promise<void> {
    this.loading = true;
    this.updateList();

    try {
      const params = new URLSearchParams();
      params.append('scope', this.scope);
      if (this.dateFrom) params.append('date_from', this.dateFrom);
      if (this.dateTo) params.append('date_to', this.dateTo);
      // DC Protocol (Feb 2026): Add employee search filter
      if (this.employeeSearch && this.employeeSearch.trim()) {
        params.append('search', this.employeeSearch.trim());
      }
      params.append('_t', Date.now().toString());

      const response = await apiService.get<any>(`/staff/kra/team-summary?${params.toString()}`);
      const data = response.data as any;
      if (response.success !== false && data) {
        if (data.employees) {
          this.employees = data.employees;
        } else if (data.employee_stats) {
          this.employees = Object.values(data.employee_stats);
        } else if (Array.isArray(data)) {
          this.employees = data;
        } else {
          this.employees = [];
        }
      } else {
        this.employees = [];
      }
    } catch (error: any) {
      console.error('[StaffKRATrackingPage] Failed to load:', error);
      if (error.message?.includes('403')) {
        this.scope = 'self';
        await this.loadTracking();
        return;
      }
      this.employees = [];
    }

    this.loading = false;
    this.updateList();
  }

  private async loadEmployeeKRAs(employeeId: number): Promise<void> {
    if (this.loadingKRAs.has(employeeId)) return;
    this.loadingKRAs.add(employeeId);

    try {
      const params = new URLSearchParams();
      if (this.dateFrom) params.append('date_from', this.dateFrom);
      if (this.dateTo) params.append('date_to', this.dateTo);
      params.append('employee_id', employeeId.toString());
      params.append('_t', Date.now().toString());

      const response = await apiService.get<any>(`/staff/kra/instances?${params.toString()}`);
      const data = response.data as any;
      if (response.success !== false && data) {
        const instances = data.instances || data || [];
        this.employeeKRAs.set(employeeId, instances);
      }
    } catch (error) {
      console.error('[StaffKRATrackingPage] Failed to load employee KRAs:', error);
      this.employeeKRAs.set(employeeId, []);
    }

    this.loadingKRAs.delete(employeeId);
    this.updateEmployeeDetail(employeeId);
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container kra-tracking-page">
        ${PageHeader.render({ title: 'KRA Tracking Sheet', showBack: true })}
        
        <div class="filters-card">
          <div class="date-filter-row">
            <div class="date-input-group">
              <label>From</label>
              <input type="date" id="dateFrom" class="form-input" value="${this.dateFrom}">
            </div>
            <div class="date-input-group">
              <label>To</label>
              <input type="date" id="dateTo" class="form-input" value="${this.dateTo}">
            </div>
            <button class="btn btn-sm btn-primary" id="applyFilter">Apply</button>
          </div>
          
          <div class="filter-row">
            <input type="text" id="employeeSearch" class="form-input" placeholder="Search employee by name..." value="${this.employeeSearch}">
          </div>
          
          <div class="filter-row">
            <select id="scopeFilter" class="form-select">
              ${this.getScopeOptionsHTML()}
            </select>
          </div>
        </div>

        <div class="list-container" id="trackingList">
          <div class="loading-state">Loading KRA data...</div>
        </div>
      </div>

      ${this.getStyles()}
    `;

    PageHeader.attachBackHandler();
    this.attachEventListeners();
  }

  private getStyles(): string {
    return `<style>
      .kra-tracking-page { padding-bottom: 80px; }
      .filters-card { margin: 0 16px 16px; padding: 16px; background: rgba(255,255,255,0.05); border-radius: 12px; }
      .date-filter-row { display: flex; gap: 12px; align-items: flex-end; margin-bottom: 12px; }
      .date-input-group { flex: 1; }
      .date-input-group label { display: block; font-size: 11px; color: rgba(255,255,255,0.6); margin-bottom: 4px; text-transform: uppercase; }
      .filter-row { margin-bottom: 12px; }
      .filter-row:last-child { margin-bottom: 0; }
      .form-input, .form-select { width: 100%; padding: 10px 12px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: #fff; font-size: 14px; }
      .form-select option { background: #1e293b; color: #fff; }
      .btn { padding: 10px 16px; border-radius: 8px; font-weight: 600; border: none; cursor: pointer; }
      .btn-sm { padding: 8px 12px; font-size: 13px; }
      .btn-primary { background: #4f46e5; color: #fff; }
      .btn-secondary { background: rgba(255,255,255,0.1); color: #fff; }
      .list-container { padding: 0 16px; }
      .employee-card-container { margin-bottom: 12px; }
      .employee-card { background: rgba(255,255,255,0.08); border-radius: 12px; padding: 16px; cursor: pointer; transition: all 0.2s; }
      .employee-card:hover { background: rgba(255,255,255,0.12); }
      .employee-card.expanded { border-radius: 12px 12px 0 0; background: rgba(79,70,229,0.2); border: 1px solid #4f46e5; border-bottom: none; }
      .employee-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
      .employee-info { display: flex; align-items: center; gap: 12px; }
      .employee-avatar { width: 44px; height: 44px; border-radius: 50%; background: linear-gradient(135deg, #6366f1, #8b5cf6); display: flex; align-items: center; justify-content: center; font-weight: 600; color: #fff; font-size: 14px; }
      .employee-name { font-weight: 600; color: #fff; font-size: 15px; }
      .employee-dept { font-size: 12px; color: rgba(255,255,255,0.6); }
      .expand-icon { color: rgba(255,255,255,0.5); transition: transform 0.3s; }
      .expand-icon.rotated { transform: rotate(180deg); }
      .completion-badge { width: 48px; height: 48px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px; }
      .completion-badge.excellent { background: #d1fae5; color: #065f46; }
      .completion-badge.good { background: #dbeafe; color: #1e40af; }
      .completion-badge.average { background: #fef3c7; color: #92400e; }
      .completion-badge.low { background: #fee2e2; color: #991b1b; }
      .kra-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 12px; }
      .stat-box { text-align: center; padding: 8px 4px; background: rgba(255,255,255,0.05); border-radius: 8px; }
      .stat-value { font-size: 16px; font-weight: 700; color: #fff; display: block; }
      .stat-label { font-size: 9px; color: rgba(255,255,255,0.5); text-transform: uppercase; }
      .stat-box.completed .stat-value { color: #4ade80; }
      .stat-box.pending .stat-value { color: #fbbf24; }
      .stat-box.approved .stat-value { color: #60a5fa; }
      .progress-bar { height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden; }
      .progress-fill { height: 100%; transition: width 0.3s; }
      .progress-fill.excellent { background: linear-gradient(90deg, #059669, #10b981); }
      .progress-fill.good { background: linear-gradient(90deg, #2563eb, #3b82f6); }
      .progress-fill.average { background: linear-gradient(90deg, #d97706, #f59e0b); }
      .progress-fill.low { background: linear-gradient(90deg, #dc2626, #ef4444); }
      .employee-inline-detail { display: none; background: rgba(30,41,59,0.98); border: 1px solid #4f46e5; border-top: none; border-radius: 0 0 12px 12px; padding: 16px; }
      .employee-inline-detail.show { display: block; }
      .detail-section-title { font-size: 13px; font-weight: 600; color: #fff; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
      .kra-instance-list { display: flex; flex-direction: column; gap: 8px; max-height: 300px; overflow-y: auto; }
      .kra-instance-item { background: rgba(255,255,255,0.05); border-radius: 8px; padding: 12px; display: flex; justify-content: space-between; align-items: center; }
      .kra-instance-info { flex: 1; }
      .kra-instance-name { font-size: 14px; color: #fff; font-weight: 500; }
      .kra-instance-date { font-size: 11px; color: rgba(255,255,255,0.5); }
      .kra-instance-status { display: flex; align-items: center; gap: 8px; }
      .status-dot { width: 8px; height: 8px; border-radius: 50%; }
      .status-dot.completed { background: #4ade80; }
      .status-dot.pending { background: #fbbf24; }
      .status-dot.approved { background: #60a5fa; }
      .status-dot.rejected { background: #ef4444; }
      .rating-badge { font-size: 12px; color: #fbbf24; }
      .inline-footer { display: flex; gap: 8px; margin-top: 16px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.1); }
      .inline-footer .btn { flex: 1; }
      .loading-state, .empty-state { text-align: center; padding: 40px; color: rgba(255,255,255,0.5); }
    </style>`;
  }

  private updateList(): void {
    const listContainer = document.getElementById('trackingList');
    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state"><i class="fas fa-spinner fa-spin"></i> Loading KRA data...</div>';
      return;
    }

    let filteredEmployees = this.employees;
    if (this.employeeSearch) {
      const searchLower = this.employeeSearch.toLowerCase();
      filteredEmployees = this.employees.filter(emp => 
        emp.employee_name?.toLowerCase().includes(searchLower)
      );
    }

    if (filteredEmployees.length === 0) {
      listContainer.innerHTML = '<div class="empty-state"><i class="fas fa-chart-bar"></i><p>No KRA tracking data found</p></div>';
      return;
    }

    listContainer.innerHTML = filteredEmployees.map(emp => this.renderEmployeeCard(emp)).join('');
    this.attachCardListeners();
  }

  private renderEmployeeCard(emp: EmployeeKRA): string {
    const total = emp.assigned_kras || 0;
    const completed = emp.completed_kras || 0;
    const completionRate = total > 0 ? Math.round((completed / total) * 100) : 0;
    const scoreClass = this.getScoreClass(completionRate);
    const isExpanded = this.expandedEmployeeId === emp.employee_id;

    return `
      <div class="employee-card-container" data-employee-id="${emp.employee_id}">
        <div class="employee-card ${isExpanded ? 'expanded' : ''}" data-employee-id="${emp.employee_id}">
          <div class="employee-header">
            <div class="employee-info">
              <div class="employee-avatar">${this.getInitials(emp.employee_name)}</div>
              <div>
                <div class="employee-name">${emp.employee_name}</div>
                <div class="employee-dept">${emp.department || 'N/A'}</div>
              </div>
            </div>
            <div style="display: flex; align-items: center; gap: 12px;">
              <div class="completion-badge ${scoreClass}">${completionRate}%</div>
              <i class="fas fa-chevron-down expand-icon ${isExpanded ? 'rotated' : ''}"></i>
            </div>
          </div>
          
          <div class="kra-stats">
            <div class="stat-box"><span class="stat-value">${total}</span><span class="stat-label">Assigned</span></div>
            <div class="stat-box completed"><span class="stat-value">${completed}</span><span class="stat-label">Completed</span></div>
            <div class="stat-box pending"><span class="stat-value">${emp.not_completed || 0}</span><span class="stat-label">Pending</span></div>
            <div class="stat-box approved"><span class="stat-value">${emp.approved || 0}</span><span class="stat-label">Approved</span></div>
          </div>
          
          <div class="progress-bar">
            <div class="progress-fill ${scoreClass}" style="width: ${completionRate}%"></div>
          </div>
        </div>
        
        <div class="employee-inline-detail ${isExpanded ? 'show' : ''}" id="detail-${emp.employee_id}">
          <div style="text-align: center; padding: 20px; color: rgba(255,255,255,0.5);">
            <i class="fas fa-spinner fa-spin"></i> Loading KRA instances...
          </div>
        </div>
      </div>
    `;
  }

  private updateEmployeeDetail(employeeId: number): void {
    const container = document.getElementById(`detail-${employeeId}`);
    if (!container) return;

    const kras = [...(this.employeeKRAs.get(employeeId) || [])].sort((a, b) => a.instance_date < b.instance_date ? -1 : a.instance_date > b.instance_date ? 1 : 0);
    
    if (kras.length === 0) {
      container.innerHTML = `
        <div class="detail-section-title"><i class="fas fa-list"></i> KRA Instances</div>
        <div style="text-align: center; padding: 20px; color: rgba(255,255,255,0.5);">No KRA instances found for this period</div>
        <div class="inline-footer"><button class="btn btn-secondary" data-action="collapse" data-id="${employeeId}">Close</button></div>
      `;
    } else {
      container.innerHTML = `
        <div class="detail-section-title"><i class="fas fa-list"></i> KRA Instances (${kras.length})</div>
        <div class="kra-instance-list">
          ${kras.map(kra => `
            <div class="kra-instance-item">
              <div class="kra-instance-info">
                <div class="kra-instance-name">${kra.template_name || 'KRA'}</div>
                <div class="kra-instance-date">${this.formatDate(kra.instance_date)}</div>
              </div>
              <div class="kra-instance-status">
                ${kra.self_rating ? `<span class="rating-badge">${'★'.repeat(kra.self_rating)}</span>` : ''}
                <span class="status-dot ${this.getStatusDotClass(kra.manager_review_status)}"></span>
              </div>
            </div>
          `).join('')}
        </div>
        <div class="inline-footer"><button class="btn btn-secondary" data-action="collapse" data-id="${employeeId}">Close</button></div>
      `;
    }

    container.querySelectorAll('[data-action="collapse"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.collapseDetail();
      });
    });
  }

  private attachEventListeners(): void {
    document.getElementById('applyFilter')?.addEventListener('click', () => {
      const fromInput = document.getElementById('dateFrom') as HTMLInputElement;
      const toInput = document.getElementById('dateTo') as HTMLInputElement;
      const searchInput = document.getElementById('employeeSearch') as HTMLInputElement;
      if (fromInput) this.dateFrom = fromInput.value;
      if (toInput) this.dateTo = toInput.value;
      if (searchInput) this.employeeSearch = searchInput.value.trim();
      this.expandedEmployeeId = null;
      this.employeeKRAs.clear();
      this.loadTracking();
    });
    
    document.getElementById('scopeFilter')?.addEventListener('change', (e) => {
      this.scope = (e.target as HTMLSelectElement).value as any;
      this.expandedEmployeeId = null;
      this.employeeKRAs.clear();
      this.loadTracking();
    });

    document.getElementById('employeeSearch')?.addEventListener('input', (e) => {
      this.employeeSearch = (e.target as HTMLInputElement).value.trim();
      this.updateList();
    });
  }

  private attachCardListeners(): void {
    document.querySelectorAll('.employee-card').forEach(card => {
      card.addEventListener('click', (e) => {
        const target = e.target as HTMLElement;
        if (target.closest('button')) return;
        const employeeId = parseInt(card.getAttribute('data-employee-id') || '0');
        this.toggleDetail(employeeId);
      });
    });

    document.querySelectorAll('[data-action="collapse"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.collapseDetail();
      });
    });
  }

  private async toggleDetail(employeeId: number): Promise<void> {
    if (this.expandedEmployeeId === employeeId) {
      this.collapseDetail();
    } else {
      this.expandedEmployeeId = employeeId;
      this.updateList();
      if (!this.employeeKRAs.has(employeeId)) {
        await this.loadEmployeeKRAs(employeeId);
      } else {
        this.updateEmployeeDetail(employeeId);
      }
    }
  }

  private collapseDetail(): void {
    this.expandedEmployeeId = null;
    this.updateList();
  }

  private getScoreClass(score: number): string {
    if (score >= 80) return 'excellent';
    if (score >= 60) return 'good';
    if (score >= 40) return 'average';
    return 'low';
  }

  private getStatusDotClass(status: string): string {
    switch (status) {
      case 'approved': case 'edited_by_manager': return 'approved';
      case 'rejected': return 'rejected';
      case 'pending_review': return 'pending';
      default: return 'pending';
    }
  }

  private getInitials(name: string): string {
    return name?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || '??';
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  }
}
