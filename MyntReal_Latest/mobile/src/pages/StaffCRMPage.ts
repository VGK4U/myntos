/**
 * Staff CRM Dashboard Page (Mobile View)
 * DC Protocol: DC_MOBILE_STAFF_CRM_002
 * Full Web Parity with 9 tabs:
 * 1. My Performance
 * 2. Team Performance (Staff-Wise Matrix with Unassigned & Inactive rows)
 * 3. Call Tracking & Logs (Staff Activity, 2-Hour Slots, Trend, Audio Player)
 * 4. Quality & QA Audits (Day/Range modes, Summary, Executive Scorecards)
 * 5. Auto Dialer (Periods, Dials, Answered, Attempts)
 * 6. Status Wise
 * 7. Category Wise
 * 8. Company Wise
 * 9. Earnings & Achievement Matrix
 * Plus: Interactive Count Drilldown Modal & Lead Communication History Modal
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import { routerService } from '../services/router.service';
import { callController } from '../services/call-controller';

interface Company {
  id: number;
  company_code: string;
  company_name: string;
}

interface Category {
  id: number;
  name: string;
}

interface Department {
  id: number;
  name: string;
}

export class StaffCRMPage {
  private container: HTMLElement;
  private loading: boolean = true;
  private activeTab: 'my' | 'team' | 'calls' | 'quality' | 'dialer' | 'status' | 'category' | 'company' | 'earnings' = 'my';

  // Filters State
  private companies: Company[] = [];
  private departments: Department[] = [];
  private categories: Category[] = [];
  private sources: string[] = [];
  
  private selectedCompanyId: string = '';
  private filterStartDate: string = '';
  private filterEndDate: string = '';
  private filterStatus: string = '';
  private filterDepartmentId: string = '';
  private filterCategoryId: string = '';
  private filterSource: string = '';
  private showFiltersDrawer: boolean = false;

  // Global Dashboard-v2 Data
  private dashData: any = null;
  private teamSelectedEmpIds: Set<number> | null = null;
  private showEmpSelectPanel: boolean = false;

  // Call Tracking Tab State
  private ctData: any = null;
  private ctSlotData: any = null;
  private ctCurrentRange: 'today' | 'yesterday' | 'this_week' | 'last_7' | 'this_month' | 'last_30' = 'last_7';
  private ctSubTab: 'staff' | 'slots' = 'staff';
  private ctSelectedStaffId: number | null = null;
  private ctSelectedStaffName: string = '';
  private ctDrilldownCalls: any[] = [];
  private currentAudioBlobUrl: string | null = null;

  // Quality QA Tab State
  private qaData: any = null;
  private qaMode: 'day' | 'range' = 'day';
  private qaDate: string = '';
  private qaRangeFrom: string = '';
  private qaRangeTo: string = '';
  private expandedQaMap: Record<number, boolean> = {};

  // Dialer Tab State
  private dialerData: any = null;
  private dialerPeriod: 'today' | 'week' | 'month' = 'today';

  // Earnings Tab State
  private earnMonth: number = new Date().getMonth() + 1;
  private earnYear: number = new Date().getFullYear();
  private earnCompanyId: string = '';
  private earnData: any[] | null = null;
  private earnLoading: boolean = false;

  // Interactive Count Drilldown Modal State
  private showDrilldownModal: boolean = false;
  private drilldownLoading: boolean = false;
  private drilldownTitle: string = '';
  private drilldownSubtitle: string = '';
  private drilldownParams: Record<string, any> | null = null;
  private drilldownCurrentPage: number = 1;
  private drilldownTotalPages: number = 1;
  private drilldownTotalCount: number = 0;
  private drilldownItems: any[] = [];
  private drilldownTelecallers: any[] = [];
  private drilldownSearch: string = '';
  private drilldownTelecallerId: string = '';

  // Lead History Modal State
  private showHistoryModal: boolean = false;
  private historyLoading: boolean = false;
  private historyLeadId: number | null = null;
  private historyLeadName: string = '';
  private historyActiveTab: 'calls' | 'wa' | 'notes' = 'calls';
  private historyCalls: any[] = [];
  private historyWhatsApp: any[] = [];
  private historyNotes: any[] = [];

  private readonly STATUS_COLS = [
    'new', 'contacted', 'interested', 'qualified', 'proposal',
    'loan_process', 'won', 'processing', 'completed', 'lost', 'on_hold'
  ];

  private readonly STATUS_LABELS: Record<string, string> = {
    new: 'New', contacted: 'Contacted', interested: 'Interested', qualified: 'Qualified',
    proposal: 'Proposal', loan_process: 'At Bank', won: 'Won', processing: 'Processing',
    completed: 'Completed', lost: 'Lost', on_hold: 'On Hold'
  };

  private readonly STANDARD_KEYS = [
    'contacted_today', 'avg_daily_leads', 'overdue',
    'new', 'contacted', 'interested', 'qualified', 'proposal', 'loan_process', 'won', 'processing', 'completed', 'lost', 'on_hold',
    'total', 'self_leads', 'company_leads', 'actual_revenue', 'deal_value', 'avg_daily_talk_time'
  ];

  constructor(container: HTMLElement) {
    this.container = container;
    const now = new Date();
    this.qaDate = now.toISOString().split('T')[0];
    const past7 = new Date();
    past7.setDate(past7.getDate() - 6);
    this.qaRangeFrom = past7.toISOString().split('T')[0];
    this.qaRangeTo = this.qaDate;
  }

  async init(): Promise<void> {
    this.render();
    try {
      await this.loadFiltersMasterData();
      await this.loadDashboardData();
    } catch (error) {
      console.error('[StaffCRMPage] Initialization failed:', error);
    } finally {
      this.loading = false;
      this.render();
    }
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     DATA FETCHING METHODS
     ═══════════════════════════════════════════════════════════════════════════ */

  private async loadFiltersMasterData(): Promise<void> {
    try {
      const [compRes, deptRes] = await Promise.all([
        apiService.get<any>('/staff/accounts/companies').catch(() => null),
        apiService.get<any>('/crm/departments-list').catch(() => null)
      ]);

      if (compRes?.success && compRes.data) {
        this.companies = Array.isArray(compRes.data) ? compRes.data : compRes.data.companies || [];
      }
      if (deptRes?.success && deptRes.data) {
        this.departments = Array.isArray(deptRes.data) ? deptRes.data : deptRes.data.departments || [];
      }

      await this.loadCategoriesAndSources();
    } catch (e) {
      console.warn('[StaffCRMPage] Error loading filter masters:', e);
    }
  }

  private async loadCategoriesAndSources(): Promise<void> {
    try {
      const catUrl = this.selectedCompanyId 
        ? `/signup-categories/list?company_id=${this.selectedCompanyId}` 
        : `/signup-categories/list`;
      const srcUrl = this.selectedCompanyId 
        ? `/crm/sources?company_id=${this.selectedCompanyId}` 
        : `/crm/sources`;

      const [catRes, srcRes] = await Promise.all([
        apiService.get<any>(catUrl).catch(() => null),
        apiService.get<any>(srcUrl).catch(() => null)
      ]);

      if (catRes?.success && catRes.data) {
        this.categories = Array.isArray(catRes.data) ? catRes.data : catRes.data.categories || [];
      }
      if (srcRes?.success && srcRes.data) {
        const raw = Array.isArray(srcRes.data) ? srcRes.data : srcRes.data.sources || [];
        const seen = new Set<string>();
        this.sources = raw.map((s: any) => (typeof s === 'string' ? s : s.name || s.source_name || '')).filter((s: string) => {
          if (!s || seen.has(s.toLowerCase())) return false;
          seen.add(s.toLowerCase());
          return true;
        });
      }
    } catch (e) {
      console.warn('[StaffCRMPage] Error loading categories/sources:', e);
    }
  }

  private buildQueryParams(): string {
    const p = new URLSearchParams();
    if (this.selectedCompanyId) p.set('company_id', this.selectedCompanyId);
    if (this.filterStartDate) p.set('start_date', this.filterStartDate);
    if (this.filterEndDate) p.set('end_date', this.filterEndDate);
    if (this.filterStatus) p.set('status', this.filterStatus);
    if (this.filterDepartmentId) p.set('department_id', this.filterDepartmentId);
    if (this.filterCategoryId) p.set('category_id', this.filterCategoryId);
    if (this.filterSource) p.set('source', this.filterSource);
    return p.toString();
  }

  private async loadDashboardData(): Promise<void> {
    this.loading = true;
    this.render();

    try {
      const qs = this.buildQueryParams();
      const url = qs ? `/crm/dashboard-v2?${qs}` : `/crm/dashboard-v2`;
      const res = await apiService.get<any>(url);

      if (res && res.success !== false) {
        this.dashData = res.data || res;
        this.teamSelectedEmpIds = null;
        this.checkTabPermissions();
      } else {
        console.error('[StaffCRMPage] loadDashboardData failed:', res?.error || res?.detail);
      }
    } catch (e) {
      console.error('[StaffCRMPage] Error loading dashboard:', e);
    } finally {
      this.loading = false;
      this.render();
    }
  }

  private checkTabPermissions(): void {
    if (!this.dashData) return;
    const canViewFin = Boolean(this.dashData.can_view_financials);
    const isLeaderOrAdmin = Boolean(this.dashData.is_leader || this.dashData.is_admin);

    if (['company', 'earnings'].includes(this.activeTab) && !canViewFin) {
      this.activeTab = 'my';
    }
    if (['team', 'status', 'category'].includes(this.activeTab) && !isLeaderOrAdmin) {
      this.activeTab = 'my';
    }
  }

  private async loadCallTrackingData(): Promise<void> {
    try {
      const [ovRes, slotRes] = await Promise.all([
        apiService.get<any>(`/call-tracking/management/overview?quick_range=${this.ctCurrentRange}`),
        apiService.get<any>(`/call-tracking/management/slot-breakdown?quick_range=${this.ctCurrentRange}`)
      ]);

      if (ovRes && ovRes.success) this.ctData = ovRes;
      if (slotRes && slotRes.success) this.ctSlotData = slotRes;
      this.render();
    } catch (e) {
      console.error('[StaffCRMPage] Call tracking error:', e);
    }
  }

  private async loadStaffCalls(staffId: number, staffName: string): Promise<void> {
    this.ctSelectedStaffId = staffId;
    this.ctSelectedStaffName = staffName;
    this.ctDrilldownCalls = [];
    this.render();

    try {
      const res = await apiService.get<any>(`/call-tracking/staff/${staffId}/calls?quick_range=${this.ctCurrentRange}&per_page=50`);
      if (res && res.success) {
        this.ctDrilldownCalls = (res.data && res.data.calls) || [];
      }
    } catch (e) {
      console.error('[StaffCRMPage] Error loading staff calls:', e);
    } finally {
      this.render();
    }
  }

  private async loadQualityReport(): Promise<void> {
    try {
      let url = '';
      if (this.qaMode === 'day') {
        url = `/call-quality/day-report?report_date=${this.qaDate}`;
        if (this.selectedCompanyId) url += `&company_id=${this.selectedCompanyId}`;
      } else {
        url = `/call-quality/range-report?date_from=${this.qaRangeFrom}&date_to=${this.qaRangeTo}`;
        if (this.selectedCompanyId) url += `&company_id=${this.selectedCompanyId}`;
      }
      const res = await apiService.get<any>(url);
      if (res && res.success !== false) {
        this.qaData = res.data || res;
      }
      this.render();
    } catch (e) {
      console.error('[StaffCRMPage] Error loading QA report:', e);
    }
  }

  private async loadDialerData(period: 'today' | 'week' | 'month' = 'today'): Promise<void> {
    this.dialerPeriod = period;
    try {
      const res = await apiService.get<any>(`/crm/dialer/analytics?period=${period}`);
      if (res && res.success) {
        this.dialerData = res;
      }
      this.render();
    } catch (e) {
      console.error('[StaffCRMPage] Dialer load error:', e);
    }
  }

  private async loadEarningsData(): Promise<void> {
    this.earnLoading = true;
    this.render();
    try {
      let url = `/staff/incentive-achievements?month=${this.earnMonth}&year=${this.earnYear}`;
      if (this.earnCompanyId) url += `&company_id=${this.earnCompanyId}`;
      const res = await apiService.get<any>(url);
      this.earnData = (res && res.data) || [];
    } catch (e) {
      console.error('[StaffCRMPage] Earnings load error:', e);
    } finally {
      this.earnLoading = false;
      this.render();
    }
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     DRILLDOWN & MODAL HANDLERS
     ═══════════════════════════════════════════════════════════════════════════ */

  public openCountDrilldown(
    empId: string | number,
    empName: string,
    metricType: string,
    metricVal: string = '',
    title: string = 'Leads Drilldown',
    extraOpts: Record<string, any> = {}
  ): void {
    this.drilldownParams = {
      emp_id: String(empId),
      emp_name: empName,
      metric_type: metricType,
      metric_val: metricVal || '',
      ...extraOpts
    };
    this.drilldownTitle = title;
    let sub = `Staff: ${empName}`;
    if (extraOpts?.category_name) sub = `Category: ${extraOpts.category_name}`;
    else if (extraOpts?.company_name) sub = `Company: ${extraOpts.company_name}`;
    this.drilldownSubtitle = `${sub} · Filter: ${metricType} ${metricVal ? '(' + metricVal + ')' : ''}`;

    this.drilldownCurrentPage = 1;
    this.drilldownSearch = '';
    this.drilldownTelecallerId = '';
    this.showDrilldownModal = true;

    // Pre-fill telecallers
    if (this.dashData?.team_performance?.employees) {
      this.drilldownTelecallers = this.dashData.team_performance.employees.map((e: any) => ({
        id: e.emp_id,
        name: e.name,
        emp_code: e.emp_code
      }));
    }

    this.render();
    this.fetchDrilldownLeads();
  }

  private async fetchDrilldownLeads(): Promise<void> {
    if (!this.drilldownParams) return;
    this.drilldownLoading = true;
    this.render();

    try {
      const p = new URLSearchParams();
      p.set('emp_id', this.drilldownParams.emp_id);
      p.set('metric_type', this.drilldownParams.metric_type);
      if (this.drilldownParams.metric_val) p.set('metric_val', this.drilldownParams.metric_val);
      p.set('page', String(this.drilldownCurrentPage));
      p.set('per_page', '20');

      if (this.drilldownParams.category_ids) {
        p.set('category_id', this.drilldownParams.category_ids);
      } else if (this.drilldownParams.category_name) {
        p.set('category_name', this.drilldownParams.category_name);
      }
      if (this.drilldownParams.company_id) {
        p.set('company_id', this.drilldownParams.company_id);
      }

      // Pass active global filters
      if (this.selectedCompanyId && !p.has('company_id')) p.set('company_id', this.selectedCompanyId);
      if (this.filterSource) p.set('source', this.filterSource);
      if (this.filterCategoryId && !p.has('category_id') && !p.has('category_name')) p.set('category_id', this.filterCategoryId);
      if (this.filterStartDate) p.set('start_date', this.filterStartDate);
      if (this.filterEndDate) p.set('end_date', this.filterEndDate);
      if (this.drilldownSearch) p.set('search', this.drilldownSearch);
      if (this.drilldownTelecallerId) p.set('telecaller_id', this.drilldownTelecallerId);

      const res = await apiService.get<any>(`/crm/dashboard-v2/drilldown?${p.toString()}`);
      if (res && res.success !== false) {
        const d = res.data || res;
        this.drilldownItems = d.items || [];
        this.drilldownTotalCount = d.total || 0;
        this.drilldownTotalPages = d.total_pages || 1;
        if (d.telecallers && d.telecallers.length) {
          this.drilldownTelecallers = d.telecallers;
        }
      } else {
        this.drilldownItems = [];
        this.drilldownTotalCount = 0;
      }
    } catch (e) {
      console.error('[StaffCRMPage] Drilldown error:', e);
      this.drilldownItems = [];
    } finally {
      this.drilldownLoading = false;
      this.render();
    }
  }

  public async openLeadHistory(leadId: number, leadName: string): Promise<void> {
    this.historyLeadId = leadId;
    this.historyLeadName = leadName;
    this.historyActiveTab = 'calls';
    this.showHistoryModal = true;
    this.historyLoading = true;
    this.historyCalls = [];
    this.historyWhatsApp = [];
    this.historyNotes = [];
    this.render();

    try {
      const res = await apiService.get<any>(`/crm/dashboard-v2/lead-history/${leadId}`);
      if (res && res.success !== false) {
        this.historyCalls = res.call_logs || [];
        this.historyWhatsApp = res.whatsapp_messages || [];
        this.historyNotes = res.notes || [];
      }
    } catch (e) {
      console.error('[StaffCRMPage] Error loading lead history:', e);
    } finally {
      this.historyLoading = false;
      this.render();
    }
  }

  private async playAudioStream(recordingId: number): Promise<void> {
    if (this.currentAudioBlobUrl) {
      try { URL.revokeObjectURL(this.currentAudioBlobUrl); } catch (_) {}
      this.currentAudioBlobUrl = null;
    }

    const token = await apiService.getToken();
    const baseUrl = apiService.getBaseUrl();
    const streamUrl = `${baseUrl}/call-tracking/recordings/${recordingId}/stream${token ? `?token=${encodeURIComponent(token)}` : ''}`;

    const player = document.getElementById('staffCrmAudioPlayer') as HTMLAudioElement;
    const playerContainer = document.getElementById('staffCrmAudioContainer');
    if (!player || !playerContainer) return;

    playerContainer.style.display = 'block';

    try {
      const resp = await fetch(streamUrl, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });
      if (resp.ok) {
        const blob = await resp.blob();
        this.currentAudioBlobUrl = URL.createObjectURL(blob);
        player.src = this.currentAudioBlobUrl;
        player.play().catch(() => {});
        return;
      }
    } catch (_) {}

    player.src = streamUrl;
    player.play().catch(() => {});
  }

  private closeAudioPlayer(): void {
    const playerContainer = document.getElementById('staffCrmAudioContainer');
    const player = document.getElementById('staffCrmAudioPlayer') as HTMLAudioElement;
    if (player) {
      player.pause();
      player.src = '';
    }
    if (playerContainer) playerContainer.style.display = 'none';
    if (this.currentAudioBlobUrl) {
      try { URL.revokeObjectURL(this.currentAudioBlobUrl); } catch (_) {}
      this.currentAudioBlobUrl = null;
    }
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     FORMATTING UTILITIES
     ═══════════════════════════════════════════════════════════════════════════ */

  private fmtNum(n: number | null | undefined): string {
    return (n || 0).toLocaleString('en-IN');
  }

  private fmtCur(n: number | null | undefined): string {
    return '₹' + (n || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 });
  }

  private fmtLakh(n: number | null | undefined): string {
    const v = n || 0;
    if (v >= 10000000) return (v / 10000000).toFixed(1) + 'Cr';
    if (v >= 100000) return (v / 100000).toFixed(1) + 'L';
    if (v >= 1000) return (v / 1000).toFixed(1) + 'K';
    return v.toLocaleString('en-IN');
  }

  private fmtDurationSec(secs: number | null | undefined): string {
    if (!secs || secs <= 0) return '0m';
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    return h > 0 ? `${h}h ${m}m` : `${m}m`;
  }

  private fmtTalkTime(secs: number | null | undefined): string {
    if (!secs || secs <= 0) return '<span style="color:#94a3b8;">0m</span>';
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    if (h > 0) return `<span style="color:#059669; font-weight:700;">${h}h ${m}m</span>`;
    return `<span style="${m >= 30 ? 'color:#059669; font-weight:700;' : ''}">${m}m</span>`;
  }

  private escapeHtml(str: any): string {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  private getDailyDates(): string[] {
    return (this.dashData && this.dashData.daily_dates) ? this.dashData.daily_dates : [];
  }

  private fmtDateLabel(dateStr: string): string {
    try {
      const d = new Date(dateStr + 'T00:00:00');
      const day = d.getDate();
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      return `${day} ${months[d.getMonth()]}`;
    } catch {
      return dateStr;
    }
  }

  private scoreBadge(score: any): string {
    if (!score && score !== 0) return '<span style="background:#f3f4f6; color:#9ca3af; padding:2px 8px; border-radius:12px; font-size:10.5px; font-weight:700;">N/A</span>';
    const n = parseFloat(score);
    if (n >= 4.5) return `<span style="background:#d1fae5; color:#065f46; padding:2px 8px; border-radius:12px; font-size:10.5px; font-weight:700;">${n.toFixed(1)}</span>`;
    if (n >= 3.5) return `<span style="background:#dbeafe; color:#1e40af; padding:2px 8px; border-radius:12px; font-size:10.5px; font-weight:700;">${n.toFixed(1)}</span>`;
    if (n >= 2.5) return `<span style="background:#fef3c7; color:#92400e; padding:2px 8px; border-radius:12px; font-size:10.5px; font-weight:700;">${n.toFixed(1)}</span>`;
    return `<span style="background:#fee2e2; color:#991b1b; padding:2px 8px; border-radius:12px; font-size:10.5px; font-weight:700;">${n.toFixed(1)}</span>`;
  }

  private callTypeBadge(c: any): string {
    const type = (c.call_type || '').toUpperCase();
    const source = (c.source || '').toLowerCase();
    const isOutbound = type === 'OUTGOING' || type === 'OUTBOUND' || c.direction === 'outbound' || source === 'softphone' || source === 'dialer' || source === 'direct';

    if (c.duration_seconds > 0 && isOutbound) {
      return '<span style="background:#dcfce7; color:#166534; font-size:10px; font-weight:700; padding:2px 6px; border-radius:4px;"><i class="fas fa-arrow-up me-1"></i>Outgoing</span>';
    }
    if (type === 'MISSED') {
      if (isOutbound) {
        return '<span style="background:#fee2e2; color:#991b1b; font-size:10px; font-weight:700; padding:2px 6px; border-radius:4px;"><i class="fas fa-phone-slash me-1"></i>Not Answered</span>';
      }
      return '<span style="background:#b91c1c; color:#ffffff; font-size:10px; font-weight:700; padding:2px 6px; border-radius:4px;"><i class="fas fa-phone-slash me-1"></i>Missed by Staff</span>';
    }
    if (type === 'INCOMING' || type === 'INBOUND') {
      return '<span style="background:#dbeafe; color:#1e40af; font-size:10px; font-weight:700; padding:2px 6px; border-radius:4px;"><i class="fas fa-arrow-down me-1"></i>Incoming</span>';
    }
    return `<span style="background:#f1f5f9; color:#475569; font-size:10px; font-weight:700; padding:2px 6px; border-radius:4px;">${this.escapeHtml(type || 'Call')}</span>`;
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     TABLE GENERATION HELPERS
     ═══════════════════════════════════════════════════════════════════════════ */

  private buildStandardHead(extraCols: Array<{ label: string; width?: number }>): string {
    let html = '<tr>';
    extraCols.forEach((ec, idx) => {
      const isFirst = idx === 0;
      const leftPx = isFirst ? 0 : 35;
      html += `<th style="position:sticky; left:${leftPx}px; z-index:4; background:#f8fafc; min-width:${ec.width || 180}px; text-align:left; padding:8px 10px; border-bottom:2px solid #cbd5e1; border-right:1px solid #e2e8f0; font-size:11px; font-weight:700; color:#475569;">${ec.label}</th>`;
    });

    this.getDailyDates().forEach(ds => {
      html += `<th style="text-align:center; padding:8px 8px; border-bottom:2px solid #cbd5e1; font-size:10.5px; font-weight:700; color:#1e40af; background:#eff6ff; min-width:65px;">${this.fmtDateLabel(ds)}</th>`;
    });

    html += `<th style="text-align:center; padding:8px 8px; border-bottom:2px solid #cbd5e1; font-size:10.5px; font-weight:700; color:#047857; background:#f0fdf4; min-width:75px;">Contacted<br>Today</th>`;
    html += `<th style="text-align:center; padding:8px 8px; border-bottom:2px solid #cbd5e1; font-size:10.5px; font-weight:700; color:#1d4ed8; background:#eff6ff; min-width:70px;">Avg Daily<br>Leads</th>`;
    html += `<th style="text-align:center; padding:8px 8px; border-bottom:2px solid #cbd5e1; font-size:10.5px; font-weight:700; color:#b91c1c; background:#fef2f2; min-width:65px;">Overdue</th>`;

    this.STATUS_COLS.forEach(s => {
      html += `<th style="text-align:center; padding:8px 8px; border-bottom:2px solid #cbd5e1; font-size:10.5px; font-weight:700; color:#475569; min-width:75px;">${this.STATUS_LABELS[s] || s}</th>`;
    });

    html += `<th style="text-align:center; padding:8px 10px; border-bottom:2px solid #cbd5e1; font-size:11px; font-weight:800; color:#0f172a; background:#f1f5f9; min-width:75px;">Total</th>`;
    html += `<th style="text-align:center; padding:8px 8px; border-bottom:2px solid #cbd5e1; font-size:10.5px; font-weight:700; color:#4338ca; min-width:75px;">Self<br>Leads</th>`;
    html += `<th style="text-align:center; padding:8px 8px; border-bottom:2px solid #cbd5e1; font-size:10.5px; font-weight:700; color:#0284c7; min-width:75px;">Company<br>Leads</th>`;
    html += `<th style="text-align:right; padding:8px 10px; border-bottom:2px solid #cbd5e1; font-size:11px; font-weight:700; color:#065f46; background:#f0fdf4; min-width:95px;">Actual Rev</th>`;
    html += `<th style="text-align:right; padding:8px 10px; border-bottom:2px solid #cbd5e1; font-size:11px; font-weight:700; color:#047857; background:#f0fdf4; min-width:95px;">Value</th>`;
    html += `<th style="text-align:center; padding:8px 10px; border-bottom:2px solid #cbd5e1; font-size:10.5px; font-weight:700; color:#475569; min-width:85px;">Avg Daily<br>Talk</th>`;
    html += '</tr>';
    return html;
  }

  private buildStandardRow(row: any, extra: Record<string, any> = {}): string {
    let html = '';
    const dc = row.daily_contacted || {};
    const empId = extra?.emp_id != null ? String(extra.emp_id) : (row.emp_id != null ? String(row.emp_id) : 'all');
    let empName = extra?.emp_name ? extra.emp_name : (row.name || 'All');
    if (extra?.category_name) {
      empName = extra.emp_name ? `${extra.emp_name} (${extra.category_name})` : extra.category_name;
    } else if (extra?.company_name) {
      empName = extra.company_name;
    }

    const extraJson = JSON.stringify(extra).replace(/"/g, '&quot;');

    // Daily contacted columns
    this.getDailyDates().forEach(ds => {
      const v = dc[ds] || 0;
      if (v > 0) {
        html += `<td style="text-align:center; padding:7px 8px; font-weight:700; color:#059669; border-bottom:1px solid #f1f5f9;">
          <span class="drill-click" data-empid="${empId}" data-empname="${this.escapeHtml(empName)}" data-mtype="daily_contacted" data-mval="${ds}" data-title="${this.escapeHtml(empName + ' - Contacted on ' + ds)}" data-extra="${extraJson}" style="cursor:pointer; text-decoration:underline;">${this.fmtNum(v)}</span>
        </td>`;
      } else {
        html += `<td style="text-align:center; padding:7px 8px; color:#cbd5e1; border-bottom:1px solid #f1f5f9;">0</td>`;
      }
    });

    // Contacted Today
    const ct = row.contacted_today || 0;
    if (ct > 0) {
      html += `<td style="text-align:center; padding:7px 8px; font-weight:700; color:#059669; background:rgba(16,185,129,0.05); border-bottom:1px solid #f1f5f9;">
        <span class="drill-click" data-empid="${empId}" data-empname="${this.escapeHtml(empName)}" data-mtype="contacted_today" data-mval="" data-title="${this.escapeHtml(empName + ' - Contacted Today')}" data-extra="${extraJson}" style="cursor:pointer; text-decoration:underline;">${this.fmtNum(ct)}</span>
      </td>`;
    } else {
      html += `<td style="text-align:center; padding:7px 8px; color:#cbd5e1; border-bottom:1px solid #f1f5f9;">0</td>`;
    }

    // Avg Daily Leads
    const avg = row.avg_daily_leads || 0;
    html += `<td style="text-align:center; padding:7px 8px; font-weight:600; color:#3b82f6; border-bottom:1px solid #f1f5f9;">${avg % 1 === 0 ? this.fmtNum(avg) : avg.toFixed(1)}</td>`;

    // Overdue
    const od = row.overdue || 0;
    if (od > 0) {
      html += `<td style="text-align:center; padding:7px 8px; font-weight:700; color:#dc2626; background:rgba(239,68,68,0.05); border-bottom:1px solid #f1f5f9;">
        <span class="drill-click" data-empid="${empId}" data-empname="${this.escapeHtml(empName)}" data-mtype="overdue" data-mval="" data-title="${this.escapeHtml(empName + ' - Overdue Leads')}" data-extra="${extraJson}" style="cursor:pointer; text-decoration:underline;">${this.fmtNum(od)}</span>
      </td>`;
    } else {
      html += `<td style="text-align:center; padding:7px 8px; color:#cbd5e1; border-bottom:1px solid #f1f5f9;">0</td>`;
    }

    // 11 Status Columns
    this.STATUS_COLS.forEach(s => {
      const v = row[s] || 0;
      if (v > 0) {
        html += `<td style="text-align:center; padding:7px 8px; font-weight:600; color:#1e293b; border-bottom:1px solid #f1f5f9;">
          <span class="drill-click" data-empid="${empId}" data-empname="${this.escapeHtml(empName)}" data-mtype="status" data-mval="${s}" data-title="${this.escapeHtml(empName + ' - Status: ' + s)}" data-extra="${extraJson}" style="cursor:pointer; text-decoration:underline;">${this.fmtNum(v)}</span>
        </td>`;
      } else {
        html += `<td style="text-align:center; padding:7px 8px; color:#cbd5e1; border-bottom:1px solid #f1f5f9;">0</td>`;
      }
    });

    // Total
    const total = row.total || 0;
    if (total > 0) {
      html += `<td style="text-align:center; padding:7px 10px; font-weight:800; color:#0f172a; background:#f8fafc; border-bottom:1px solid #f1f5f9;">
        <span class="drill-click" data-empid="${empId}" data-empname="${this.escapeHtml(empName)}" data-mtype="total" data-mval="" data-title="${this.escapeHtml(empName + ' - Total Leads')}" data-extra="${extraJson}" style="cursor:pointer; text-decoration:underline;">${this.fmtNum(total)}</span>
      </td>`;
    } else {
      html += `<td style="text-align:center; padding:7px 10px; color:#cbd5e1; border-bottom:1px solid #f1f5f9;">0</td>`;
    }

    // Self Leads
    const sl = row.self_leads || 0;
    html += `<td style="text-align:center; padding:7px 8px; border-bottom:1px solid #f1f5f9;">
      ${sl > 0 ? `<span class="drill-click" data-empid="${empId}" data-empname="${this.escapeHtml(empName)}" data-mtype="self_leads" data-mval="" data-title="${this.escapeHtml(empName + ' - Self Leads')}" data-extra="${extraJson}" style="cursor:pointer; text-decoration:underline; font-weight:600; color:#4338ca;">${this.fmtNum(sl)}</span>` : '<span style="color:#cbd5e1;">0</span>'}
    </td>`;

    // Company Leads
    const cl = row.company_leads || 0;
    html += `<td style="text-align:center; padding:7px 8px; border-bottom:1px solid #f1f5f9;">
      ${cl > 0 ? `<span class="drill-click" data-empid="${empId}" data-empname="${this.escapeHtml(empName)}" data-mtype="company_leads" data-mval="" data-title="${this.escapeHtml(empName + ' - Company Leads')}" data-extra="${extraJson}" style="cursor:pointer; text-decoration:underline; font-weight:600; color:#0284c7;">${this.fmtNum(cl)}</span>` : '<span style="color:#cbd5e1;">0</span>'}
    </td>`;

    // Actual Revenue & Deal Value & Talk Time
    html += `<td style="text-align:right; padding:7px 10px; font-weight:700; color:#065f46; border-bottom:1px solid #f1f5f9;">${this.fmtCur(row.actual_revenue)}</td>`;
    html += `<td style="text-align:right; padding:7px 10px; font-weight:700; color:#047857; border-bottom:1px solid #f1f5f9;">${this.fmtCur(row.deal_value)}</td>`;
    html += `<td style="text-align:center; padding:7px 10px; border-bottom:1px solid #f1f5f9;">${this.fmtTalkTime(row.avg_daily_talk_time)}</td>`;
    return html;
  }

  private calcTotals(rows: any[]): any {
    const totals: Record<string, any> = {
      contacted_today: 0, avg_daily_leads: 0, overdue: 0, total: 0,
      self_leads: 0, company_leads: 0, actual_revenue: 0, deal_value: 0, avg_daily_talk_time: 0
    };
    this.STATUS_COLS.forEach(s => totals[s] = 0);
    const dailyTotals: Record<string, number> = {};
    this.getDailyDates().forEach(ds => { dailyTotals[ds] = 0; });
    let avgSum = 0;

    rows.forEach(r => {
      this.STANDARD_KEYS.forEach(k => {
        if (k === 'avg_daily_leads' || k === 'avg_daily_talk_time') return;
        totals[k] = (totals[k] || 0) + (r[k] || 0);
      });
      avgSum += (r.avg_daily_leads || 0);
      const dc = r.daily_contacted || {};
      this.getDailyDates().forEach(ds => {
        dailyTotals[ds] = (dailyTotals[ds] || 0) + (dc[ds] || 0);
      });
    });

    totals.avg_daily_leads = rows.length > 0 ? Math.round(avgSum / rows.length * 10) / 10 : 0;
    totals.daily_contacted = dailyTotals;
    return totals;
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     EXPORT ACTIVE TAB TO CSV
     ═══════════════════════════════════════════════════════════════════════════ */

  private exportActiveTabToCSV(): void {
    let table = this.container.querySelector(`#tabArea_${this.activeTab} table` ) as HTMLTableElement;
    if (!table) {
      alert('No data table available for export in current tab.');
      return;
    }

    const rows = Array.from(table.querySelectorAll('tr'));
    if (!rows.length) {
      alert('Table is currently empty.');
      return;
    }

    const csvContent = rows.map(r => {
      const cells = Array.from(r.querySelectorAll('th, td'));
      return cells.map(c => {
        let text = (c as HTMLElement).innerText.replace(/(\r\n|\n|\r)/gm, ' ').replace(/\s+/g, ' ').trim();
        text = text.replace(/"/g, '""');
        return `"${text}"`;
      }).join(',');
    }).join('\n');

    const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.setAttribute('download', `CRM_${this.activeTab}_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     RENDER METHODS
     ═══════════════════════════════════════════════════════════════════════════ */

  render(): void {
    const isLeaderOrAdmin = Boolean(this.dashData?.is_leader || this.dashData?.is_admin);
    const canViewFin = Boolean(this.dashData?.can_view_financials);

    // Dynamic Tab Badges
    let myBadge = '';
    if (this.dashData?.my_performance?.summary) {
      myBadge = `${this.fmtNum(this.dashData.my_performance.summary.total_leads)} leads`;
    }
    let teamBadge = '';
    if (this.dashData?.team_performance?.totals) {
      teamBadge = `${this.fmtNum(this.dashData.team_performance.totals.total)} leads`;
    }
    let statusBadge = '';
    if (this.dashData?.status_wise?.totals) {
      statusBadge = `${this.fmtNum(this.dashData.status_wise.totals.total)}`;
    }
    let catBadge = '';
    if (this.dashData?.category_wise) {
      const tot = this.dashData.category_wise.reduce((s: number, r: any) => s + (r.total || 0), 0);
      catBadge = `${this.fmtNum(tot)}`;
    }
    let compBadge = '';
    if (this.dashData?.company_wise) {
      const tot = this.dashData.company_wise.reduce((s: number, r: any) => s + (r.total || 0), 0);
      compBadge = `${this.fmtNum(tot)}`;
    }

    this.container.innerHTML = `
      <div class="staff-crm-page" style="min-height:100vh; background:#f8fafc; padding-bottom:70px;">
        ${PageHeader.render({
          title: 'CRM & Team Performance 360°',
          showBack: true,
          showMenu: true
        })}

        <!-- Top Action Bar with Filters and Export -->
        <div style="display:flex; justify-content:space-between; align-items:center; padding:10px 14px 4px 14px; background:#f1f5f9; border-bottom:1px solid #e2e8f0;">
          <div style="font-size:12px; font-weight:700; color:#1e293b;">
            ${compBadge ? `<span style="background:#e0e7ff; color:#3730a3; padding:2px 8px; border-radius:12px; font-size:11px; font-weight:700;">${compBadge}</span>` : ''}
          </div>
          <div style="display:flex; gap:6px;">
            <button id="crmFilterToggleBtn" class="btn-icon" style="background:#4f46e5; color:white; border:none; border-radius:8px; width:34px; height:34px; display:flex; align-items:center; justify-content:center; cursor:pointer;" title="Filters">
              <i class="fas fa-filter" style="font-size:13px;"></i>
            </button>
            <button id="crmExportCsvBtn" class="btn-icon" style="background:#ecfdf5; color:#065f46; border:1px solid #a7f3d0; border-radius:8px; width:34px; height:34px; display:flex; align-items:center; justify-content:center; cursor:pointer;" title="Export CSV">
              <i class="fas fa-file-excel" style="font-size:13px;"></i>
            </button>
          </div>
        </div>

        <!-- Main Body Container -->
        <div style="padding:12px 14px;">

          <!-- Global Filter Drawer / Panel (Expandable) -->
          <div id="crmFilterPanel" style="display:${this.showFiltersDrawer ? 'block' : 'none'}; background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:14px; margin-bottom:14px; box-shadow:0 4px 6px -1px rgba(0,0,0,0.05);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; border-bottom:1px solid #f1f5f9; padding-bottom:6px;">
              <span style="font-size:12.5px; font-weight:700; color:#1e293b;"><i class="fas fa-sliders-h me-1 text-primary"></i> Filter Dashboard</span>
              <button id="crmCloseFiltersBtn" style="background:none; border:none; color:#64748b; font-size:13px; cursor:pointer;"><i class="fas fa-times"></i></button>
            </div>

            <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:10px;">
              <!-- Company -->
              <div>
                <label style="font-size:10.5px; font-weight:700; color:#475569; display:block; margin-bottom:3px;">Company</label>
                <select id="crmCompanySelect" style="width:100%; font-size:11.5px; padding:6px 8px; border:1px solid #cbd5e1; border-radius:6px; background:#fff;">
                  <option value="">All Companies</option>
                  ${this.companies.map(c => `<option value="${c.id}" ${String(c.id) === this.selectedCompanyId ? 'selected' : ''}>${this.escapeHtml(c.company_name)}</option>`).join('')}
                </select>
              </div>

              <!-- Status -->
              <div>
                <label style="font-size:10.5px; font-weight:700; color:#475569; display:block; margin-bottom:3px;">Status</label>
                <select id="crmStatusSelect" style="width:100%; font-size:11.5px; padding:6px 8px; border:1px solid #cbd5e1; border-radius:6px; background:#fff;">
                  <option value="">All Statuses</option>
                  ${this.STATUS_COLS.map(s => `<option value="${s}" ${s === this.filterStatus ? 'selected' : ''}>${this.STATUS_LABELS[s]}</option>`).join('')}
                </select>
              </div>

              <!-- From Date -->
              <div>
                <label style="font-size:10.5px; font-weight:700; color:#475569; display:block; margin-bottom:3px;">From Date</label>
                <input type="date" id="crmStartDate" value="${this.filterStartDate}" style="width:100%; font-size:11.5px; padding:5px 7px; border:1px solid #cbd5e1; border-radius:6px;">
              </div>

              <!-- To Date -->
              <div>
                <label style="font-size:10.5px; font-weight:700; color:#475569; display:block; margin-bottom:3px;">To Date</label>
                <input type="date" id="crmEndDate" value="${this.filterEndDate}" style="width:100%; font-size:11.5px; padding:5px 7px; border:1px solid #cbd5e1; border-radius:6px;">
              </div>

              <!-- Department -->
              <div>
                <label style="font-size:10.5px; font-weight:700; color:#475569; display:block; margin-bottom:3px;">Department</label>
                <select id="crmDeptSelect" style="width:100%; font-size:11.5px; padding:6px 8px; border:1px solid #cbd5e1; border-radius:6px; background:#fff;">
                  <option value="">All Departments</option>
                  ${this.departments.map(d => `<option value="${d.id}" ${String(d.id) === this.filterDepartmentId ? 'selected' : ''}>${this.escapeHtml(d.name)}</option>`).join('')}
                </select>
              </div>

              <!-- Category -->
              <div>
                <label style="font-size:10.5px; font-weight:700; color:#475569; display:block; margin-bottom:3px;">Category</label>
                <select id="crmCategorySelect" style="width:100%; font-size:11.5px; padding:6px 8px; border:1px solid #cbd5e1; border-radius:6px; background:#fff;">
                  <option value="">All Categories</option>
                  ${this.categories.map(c => `<option value="${c.id}" ${String(c.id) === this.filterCategoryId ? 'selected' : ''}>${this.escapeHtml(c.name)}</option>`).join('')}
                </select>
              </div>
            </div>

            <!-- Source -->
            <div style="margin-bottom:10px;">
              <label style="font-size:10.5px; font-weight:700; color:#475569; display:block; margin-bottom:3px;">Source</label>
              <select id="crmSourceSelect" style="width:100%; font-size:11.5px; padding:6px 8px; border:1px solid #cbd5e1; border-radius:6px; background:#fff;">
                <option value="">All Sources</option>
                ${this.sources.map(s => `<option value="${this.escapeHtml(s)}" ${s === this.filterSource ? 'selected' : ''}>${this.escapeHtml(s)}</option>`).join('')}
              </select>
            </div>

            <div style="display:flex; justify-content:flex-end; gap:8px;">
              <button id="crmResetFiltersBtn" style="background:#f1f5f9; color:#475569; border:1px solid #cbd5e1; border-radius:6px; padding:6px 12px; font-size:11.5px; font-weight:600; cursor:pointer;">
                <i class="fas fa-undo me-1"></i>Reset
              </button>
              <button id="crmApplyFiltersBtn" style="background:#4f46e5; color:#ffffff; border:none; border-radius:6px; padding:6px 14px; font-size:11.5px; font-weight:700; cursor:pointer;">
                <i class="fas fa-search me-1"></i>Apply Filters
              </button>
            </div>
          </div>

          <!-- Horizontal 9-Tabs Bar (Scrollable on Mobile) -->
          <div style="display:flex; gap:6px; overflow-x:auto; padding-bottom:6px; margin-bottom:12px; -webkit-overflow-scrolling:touch;">
            <button class="crm-tab-btn ${this.activeTab === 'my' ? 'active' : ''}" data-tab="my" style="${this.getTabStyle(this.activeTab === 'my')}">
              <span><i class="fas fa-user me-1"></i>My Performance</span>
              ${myBadge ? `<span style="font-size:9.5px; opacity:0.8; margin-left:4px;">(${myBadge})</span>` : ''}
            </button>

            ${isLeaderOrAdmin ? `
              <button class="crm-tab-btn ${this.activeTab === 'team' ? 'active' : ''}" data-tab="team" style="${this.getTabStyle(this.activeTab === 'team')}">
                <span><i class="fas fa-users me-1"></i>Team Performance</span>
                ${teamBadge ? `<span style="font-size:9.5px; opacity:0.8; margin-left:4px;">(${teamBadge})</span>` : ''}
              </button>
            ` : ''}

            <button class="crm-tab-btn ${this.activeTab === 'calls' ? 'active' : ''}" data-tab="calls" style="${this.getTabStyle(this.activeTab === 'calls')}">
              <span><i class="fas fa-phone-alt me-1"></i>Calls</span>
            </button>

            <button class="crm-tab-btn ${this.activeTab === 'quality' ? 'active' : ''}" data-tab="quality" style="${this.getTabStyle(this.activeTab === 'quality')}">
              <span><i class="fas fa-clipboard-check me-1"></i>Quality QA</span>
            </button>

            <button class="crm-tab-btn ${this.activeTab === 'dialer' ? 'active' : ''}" data-tab="dialer" style="${this.getTabStyle(this.activeTab === 'dialer')}">
              <span><i class="fas fa-headset me-1"></i>Auto Dialer</span>
            </button>

            ${isLeaderOrAdmin ? `
              <button class="crm-tab-btn ${this.activeTab === 'status' ? 'active' : ''}" data-tab="status" style="${this.getTabStyle(this.activeTab === 'status')}">
                <span><i class="fas fa-list-ol me-1"></i>Status Wise</span>
                ${statusBadge ? `<span style="font-size:9.5px; opacity:0.8; margin-left:4px;">(${statusBadge})</span>` : ''}
              </button>

              <button class="crm-tab-btn ${this.activeTab === 'category' ? 'active' : ''}" data-tab="category" style="${this.getTabStyle(this.activeTab === 'category')}">
                <span><i class="fas fa-tags me-1"></i>Category Wise</span>
                ${catBadge ? `<span style="font-size:9.5px; opacity:0.8; margin-left:4px;">(${catBadge})</span>` : ''}
              </button>
            ` : ''}

            ${canViewFin ? `
              <button class="crm-tab-btn ${this.activeTab === 'company' ? 'active' : ''}" data-tab="company" style="${this.getTabStyle(this.activeTab === 'company')}">
                <span><i class="fas fa-building me-1"></i>Company Wise</span>
                ${compBadge ? `<span style="font-size:9.5px; opacity:0.8; margin-left:4px;">(${compBadge})</span>` : ''}
              </button>

              <button class="crm-tab-btn ${this.activeTab === 'earnings' ? 'active' : ''}" data-tab="earnings" style="${this.getTabStyle(this.activeTab === 'earnings')}">
                <span><i class="fas fa-wallet me-1"></i>Earnings</span>
              </button>
            ` : ''}
          </div>

          <!-- Loading State -->
          ${this.loading ? `
            <div style="text-align:center; padding:48px 16px;">
              <i class="fas fa-circle-notch fa-spin" style="font-size:28px; color:#4f46e5; margin-bottom:12px;"></i>
              <div style="color:#64748b; font-size:13px; font-weight:600;">Loading CRM Performance 360°...</div>
            </div>
          ` : `
            <!-- Tab Panes -->
            <div id="tabArea_${this.activeTab}">
              ${this.activeTab === 'my' ? this.renderMyPerformanceTab() : ''}
              ${this.activeTab === 'team' ? this.renderTeamPerformanceTab() : ''}
              ${this.activeTab === 'calls' ? this.renderCallsTab() : ''}
              ${this.activeTab === 'quality' ? this.renderQualityTab() : ''}
              ${this.activeTab === 'dialer' ? this.renderDialerTab() : ''}
              ${this.activeTab === 'status' ? this.renderStatusWiseTab() : ''}
              ${this.activeTab === 'category' ? this.renderCategoryWiseTab() : ''}
              ${this.activeTab === 'company' ? this.renderCompanyWiseTab() : ''}
              ${this.activeTab === 'earnings' ? this.renderEarningsTab() : ''}
            </div>
          `}

        </div>

        <!-- In-Page Audio Player Floating Bar (for call recording playback) -->
        <div id="staffCrmAudioContainer" style="display:none; position:fixed; bottom:0; left:0; right:0; background:#0f172a; color:#fff; padding:10px 16px; z-index:1040; border-top:1px solid #334155; box-shadow:0 -4px 12px rgba(0,0,0,0.15);">
          <div style="display:flex; align-items:center; gap:10px; max-width:600px; margin:0 auto;">
            <i class="fas fa-headphones" style="color:#38bdf8; font-size:16px;"></i>
            <audio id="staffCrmAudioPlayer" controls style="flex:1; height:32px; outline:none;"></audio>
            <button id="closeStaffCrmAudioBtn" style="background:none; border:none; color:#94a3b8; font-size:16px; cursor:pointer;"><i class="fas fa-times"></i></button>
          </div>
        </div>

        <!-- Count Drilldown Modal / Bottom Sheet -->
        ${this.showDrilldownModal ? this.renderDrilldownModal() : ''}

        <!-- Lead Communication History Modal / Bottom Sheet -->
        ${this.showHistoryModal ? this.renderHistoryModal() : ''}
      </div>
    `;

    PageHeader.attachListeners({
      title: 'CRM Dashboard',
      showMenu: true,
      showBack: true
    });

    this.attachEventListeners();
  }

  private getTabStyle(active: boolean): string {
    if (active) {
      return 'white-space:nowrap; background:#4f46e5; color:#ffffff; border:none; border-radius:8px; padding:8px 12px; font-size:11.5px; font-weight:700; cursor:pointer; box-shadow:0 2px 6px rgba(79,70,229,0.3);';
    }
    return 'white-space:nowrap; background:#ffffff; color:#64748b; border:1px solid #e2e8f0; border-radius:8px; padding:8px 12px; font-size:11.5px; font-weight:600; cursor:pointer;';
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     TAB 1: MY PERFORMANCE
     ═══════════════════════════════════════════════════════════════════════════ */

  private renderMyPerformanceTab(): string {
    const my = this.dashData?.my_performance;
    if (!my) {
      return `<div style="text-align:center; padding:32px; color:#94a3b8;">No personal performance data recorded.</div>`;
    }

    const s = my.summary || {};
    const myEmpId = this.dashData?.current_employee?.id ? String(this.dashData.current_employee.id) : 'all';
    const myEmpName = this.dashData?.current_employee?.name || 'My';
    const winRate = s.total_leads > 0 ? ((s.won || 0) / s.total_leads * 100).toFixed(1) + '%' : '0%';
    const cats = my.category_breakdown || [];

    return `
      <!-- My KPI Cards Grid -->
      <div style="display:grid; grid-template-columns:repeat(2, 1fr); gap:8px; margin-bottom:12px;">
        <div class="drill-click stat-card" data-empid="${myEmpId}" data-empname="${this.escapeHtml(myEmpName)}" data-mtype="total" data-mval="" data-title="My Performance - Total Leads" style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:10px 12px; cursor:pointer;">
          <div style="font-size:10px; font-weight:700; color:#64748b; text-transform:uppercase;">Total Leads</div>
          <div style="font-size:22px; font-weight:800; color:#4f46e5; margin-top:2px;">${this.fmtNum(s.total_leads)}</div>
          <div style="font-size:9.5px; color:#94a3b8;">Assigned pipeline</div>
        </div>

        <div class="drill-click stat-card" data-empid="${myEmpId}" data-empname="${this.escapeHtml(myEmpName)}" data-mtype="contacted_today" data-mval="" data-title="My Performance - Contacted Today" style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:10px 12px; cursor:pointer;">
          <div style="font-size:10px; font-weight:700; color:#64748b; text-transform:uppercase;">Contacted Today</div>
          <div style="font-size:22px; font-weight:800; color:#059669; margin-top:2px;">${this.fmtNum(s.contacted_today)}</div>
          <div style="font-size:9.5px; color:#059669;">Daily interactions</div>
        </div>

        <div class="stat-card" style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:10px 12px;">
          <div style="font-size:10px; font-weight:700; color:#64748b; text-transform:uppercase;">Avg Daily Leads</div>
          <div style="font-size:20px; font-weight:800; color:#2563eb; margin-top:2px;">${s.avg_daily_leads || 0}</div>
          <div style="font-size:9.5px; color:#64748b;">Pacing rate</div>
        </div>

        <div class="drill-click stat-card" data-empid="${myEmpId}" data-empname="${this.escapeHtml(myEmpName)}" data-mtype="overdue" data-mval="" data-title="My Performance - Overdue Leads" style="background:#ffffff; border:1px solid #fecaca; border-radius:10px; padding:10px 12px; cursor:pointer;">
          <div style="font-size:10px; font-weight:700; color:#dc2626; text-transform:uppercase;">Overdue</div>
          <div style="font-size:20px; font-weight:800; color:#b91c1c; margin-top:2px;">${this.fmtNum(s.overdue)}</div>
          <div style="font-size:9.5px; color:#dc2626;">Needs immediate action</div>
        </div>
      </div>

      <!-- Secondary 4-Card Grid -->
      <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:6px; margin-bottom:12px;">
        <div class="drill-click" data-empid="${myEmpId}" data-empname="${this.escapeHtml(myEmpName)}" data-mtype="status" data-mval="new" data-title="My Performance - New Leads" style="background:#ffffff; border:1px solid #e2e8f0; border-radius:8px; padding:8px 4px; text-align:center; cursor:pointer;">
          <div style="font-size:9px; color:#64748b; font-weight:700;">NEW</div>
          <div style="font-size:14px; font-weight:800; color:#1e293b; margin-top:2px;">${this.fmtNum(s.new)}</div>
        </div>
        <div class="drill-click" data-empid="${myEmpId}" data-empname="${this.escapeHtml(myEmpName)}" data-mtype="status" data-mval="interested" data-title="My Performance - Interested Leads" style="background:#ffffff; border:1px solid #e2e8f0; border-radius:8px; padding:8px 4px; text-align:center; cursor:pointer;">
          <div style="font-size:9px; color:#2563eb; font-weight:700;">INTERESTED</div>
          <div style="font-size:14px; font-weight:800; color:#1d4ed8; margin-top:2px;">${this.fmtNum(s.interested)}</div>
        </div>
        <div class="drill-click" data-empid="${myEmpId}" data-empname="${this.escapeHtml(myEmpName)}" data-mtype="status" data-mval="won" data-title="My Performance - Won Leads" style="background:#ffffff; border:1px solid #86efac; border-radius:8px; padding:8px 4px; text-align:center; cursor:pointer;">
          <div style="font-size:9px; color:#059669; font-weight:700;">WON</div>
          <div style="font-size:14px; font-weight:800; color:#047857; margin-top:2px;">${this.fmtNum(s.won)}</div>
          <div style="font-size:8px; color:#059669;">${winRate}</div>
        </div>
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:8px; padding:8px 4px; text-align:center;">
          <div style="font-size:9px; color:#0f766e; font-weight:700;">ACTUAL REV</div>
          <div style="font-size:11.5px; font-weight:800; color:#0f766e; margin-top:2px;">${this.fmtLakh(my.actual_revenue)}</div>
        </div>
      </div>

      <!-- Category Breakdown Table -->
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:12px; margin-bottom:14px;">
        <div style="font-size:12.5px; font-weight:700; color:#1e293b; margin-bottom:10px; display:flex; align-items:center; gap:6px;">
          <i class="fas fa-tags" style="color:#4f46e5;"></i> My Category Breakdown (${cats.length})
        </div>

        <div style="overflow-x:auto; -webkit-overflow-scrolling:touch;">
          <table style="width:100%; min-width:1100px; border-collapse:collapse; font-size:11.5px;">
            <thead>
              ${this.buildStandardHead([{ label: 'Category', width: 170 }])}
            </thead>
            <tbody>
              ${cats.map((c: any) => {
                const extra = { category_name: c.category_name, emp_id: myEmpId, emp_name: myEmpName, category_ids: c.category_ids || (c.category_id ? String(c.category_id) : 'none') };
                return `
                  <tr>
                    <td style="position:sticky; left:0; z-index:2; background:#ffffff; padding:7px 10px; font-weight:700; color:#0f172a; border-bottom:1px solid #f1f5f9; border-right:1px solid #e2e8f0;">
                      ${this.escapeHtml(c.category_name || 'General')}
                    </td>
                    ${this.buildStandardRow(c, extra)}
                  </tr>
                `;
              }).join('')}
            </tbody>
            <tfoot>
              <tr style="background:#f8fafc; font-weight:800;">
                <td style="position:sticky; left:0; z-index:2; background:#f8fafc; padding:8px 10px; color:#0f172a; border-right:1px solid #cbd5e1;">TOTAL</td>
                ${this.buildStandardRow(this.calcTotals(cats), { emp_id: myEmpId, emp_name: myEmpName })}
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    `;
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     TAB 2: TEAM PERFORMANCE (STAFF-WISE MATRIX)
     ═══════════════════════════════════════════════════════════════════════════ */

  private renderTeamPerformanceTab(): string {
    const tp = this.dashData?.team_performance;
    if (!tp) {
      return `<div style="text-align:center; padding:32px; color:#94a3b8;">No team members data available.</div>`;
    }

    const allEmployees = tp.employees || [];
    const specialRows = tp.special_rows || [];

    // Filter employees by multi-select if active
    let employees = allEmployees;
    if (this.teamSelectedEmpIds) {
      employees = allEmployees.filter((e: any) => this.teamSelectedEmpIds!.has(e.emp_id));
    }

    // Find top converter
    let topEmpId: any = null;
    let maxWon = 0;
    employees.forEach((e: any) => {
      if ((e.won || 0) > maxWon) {
        maxWon = e.won;
        topEmpId = e.emp_id;
      }
    });

    return `
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:12px; margin-bottom:14px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
          <div>
            <div style="font-size:12.5px; font-weight:700; color:#1e293b; display:flex; align-items:center; gap:6px;">
              <i class="fas fa-users" style="color:#4f46e5;"></i> Staff-Wise Lead Matrix (${employees.length})
            </div>
            <div style="font-size:10px; color:#64748b;">Includes unassigned pool &amp; inactive members</div>
          </div>
          <button id="toggleEmpSelectBtn" style="background:#f1f5f9; border:1px solid #cbd5e1; border-radius:6px; padding:5px 10px; font-size:11px; font-weight:700; color:#334155; cursor:pointer;">
            <i class="fas fa-filter me-1"></i>${this.showEmpSelectPanel ? 'Close Filter' : 'Select Members'}
          </button>
        </div>

        <!-- Employee Multi-Select Panel -->
        <div id="empSelectPanel" style="display:${this.showEmpSelectPanel ? 'flex' : 'none'}; flex-wrap:wrap; gap:6px; padding:10px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; margin-bottom:10px;">
          <label style="background:${!this.teamSelectedEmpIds ? '#4f46e5' : '#fff'}; color:${!this.teamSelectedEmpIds ? '#fff' : '#475569'}; border:1px solid #cbd5e1; border-radius:14px; padding:3px 10px; font-size:10.5px; font-weight:700; cursor:pointer;" id="chipToggleAllEmps">
            All (${allEmployees.length})
          </label>
          ${allEmployees.map((emp: any) => {
            const isSel = !this.teamSelectedEmpIds || this.teamSelectedEmpIds.has(emp.emp_id);
            return `
              <label class="emp-chip-item" data-empid="${emp.emp_id}" style="background:${isSel ? '#dbeafe' : '#fff'}; color:${isSel ? '#1e40af' : '#64748b'}; border:1px solid ${isSel ? '#93c5fd' : '#cbd5e1'}; border-radius:14px; padding:3px 10px; font-size:10.5px; font-weight:600; cursor:pointer;">
                ${this.escapeHtml(emp.name || emp.emp_code)}
              </label>
            `;
          }).join('')}
        </div>

        <!-- High-Density Matrix Table -->
        <div style="overflow-x:auto; -webkit-overflow-scrolling:touch;">
          <table style="width:100%; min-width:1250px; border-collapse:collapse; font-size:11.5px;">
            <thead>
              ${this.buildStandardHead([
                { label: '#', width: 35 },
                { label: 'Staff Member', width: 190 }
              ])}
            </thead>
            <tbody>
              <!-- Special Rows: Unassigned Pool & Inactive Employees -->
              ${specialRows.map((sp: any) => {
                const isUnassigned = sp.special_type === 'unassigned';
                const bg = isUnassigned ? '#eff6ff' : '#fffbeb';
                const icon = isUnassigned ? 'fa-building text-primary' : 'fa-user-slash text-warning';
                const badgeText = isUnassigned ? 'Company Pool' : 'Inactive / Past';
                const badgeColor = isUnassigned ? 'background:#2563eb; color:#fff;' : 'background:#d97706; color:#fff;';

                return `
                  <tr style="background:${bg};">
                    <td style="position:sticky; left:0; z-index:2; background:${bg}; padding:7px 6px; text-align:center; border-bottom:1px solid #cbd5e1;">
                      <i class="fas ${icon}" style="font-size:11px;"></i>
                    </td>
                    <td style="position:sticky; left:35px; z-index:2; background:${bg}; padding:7px 10px; border-bottom:1px solid #cbd5e1; border-right:1px solid #cbd5e1;">
                      <div style="font-weight:700; color:#1e293b; font-size:11.5px;">
                        ${this.escapeHtml(sp.name)}
                        <span style="${badgeColor} font-size:8.5px; padding:2px 5px; border-radius:4px; margin-left:4px; font-weight:700;">${badgeText}</span>
                      </div>
                      <div style="font-size:9.5px; color:#64748b;">${this.escapeHtml(sp.emp_code || '')} · Leads Pool</div>
                    </td>
                    ${this.buildStandardRow(sp, { emp_id: sp.special_type, emp_name: sp.name })}
                  </tr>
                `;
              }).join('')}

              <!-- Employee Rows -->
              ${employees.map((emp: any, idx: number) => {
                const isTop = (emp.emp_id === topEmpId && maxWon > 0);
                const winRate = emp.total > 0 ? ((emp.won || 0) / emp.total * 100).toFixed(1) + '%' : '0%';

                return `
                  <tr>
                    <td style="position:sticky; left:0; z-index:2; background:#ffffff; padding:7px 6px; text-align:center; border-bottom:1px solid #f1f5f9; color:#64748b;">
                      ${idx + 1}
                    </td>
                    <td style="position:sticky; left:35px; z-index:2; background:#ffffff; padding:7px 10px; border-bottom:1px solid #f1f5f9; border-right:1px solid #e2e8f0;">
                      <div style="font-weight:700; color:#0f172a; font-size:11.5px; display:flex; align-items:center;">
                        ${this.escapeHtml(emp.name || '-')}
                        ${isTop ? '<span style="background:#fef08a; color:#854d0e; font-size:8.5px; padding:1px 5px; border-radius:4px; margin-left:4px; font-weight:700;"><i class="fas fa-crown me-1"></i>Top</span>' : ''}
                      </div>
                      <div style="font-size:9.5px; color:#64748b;">${this.escapeHtml(emp.emp_code || '')} · Win: ${winRate}</div>
                    </td>
                    ${this.buildStandardRow(emp, { emp_id: emp.emp_id, emp_name: emp.name })}
                  </tr>
                `;
              }).join('')}
            </tbody>
            <tfoot>
              <tr style="background:#f8fafc; font-weight:800;">
                <td style="position:sticky; left:0; z-index:2; background:#f8fafc; border-bottom:2px solid #cbd5e1;"></td>
                <td style="position:sticky; left:35px; z-index:2; background:#f8fafc; padding:8px 10px; color:#0f172a; border-right:1px solid #cbd5e1;">TOTAL</td>
                ${this.buildStandardRow(tp.totals || this.calcTotals(employees), { emp_id: 'all', emp_name: 'TOTAL' })}
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    `;
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     TAB 3: CALL TRACKING & LOGS
     ═══════════════════════════════════════════════════════════════════════════ */

  private renderCallsTab(): string {
    const o = this.ctData?.overview || {};
    const trend = (this.ctData?.daily_trend || []).slice().reverse();
    const perStaff = this.ctData?.per_staff || [];

    const connectedCalls = Math.max((o.outgoing || 0) + (o.incoming || 0) - (o.missed || 0), 0);
    const ansRate = o.total_calls > 0 ? (connectedCalls / o.total_calls * 100).toFixed(1) + '%' : '0%';

    const maxCalls = Math.max(...trend.map((d: any) => d.calls || 0), 1);

    return `
      <!-- Sub-Filter Bar for Quick Range & Sub-Tabs -->
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:12px; margin-bottom:12px;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:8px;">
          <div style="display:flex; gap:4px; overflow-x:auto; -webkit-overflow-scrolling:touch;">
            ${['today', 'yesterday', 'this_week', 'last_7', 'this_month', 'last_30'].map(r => `
              <button class="ct-range-btn ${this.ctCurrentRange === r ? 'active' : ''}" data-range="${r}" style="white-space:nowrap; background:${this.ctCurrentRange === r ? '#4f46e5' : '#f1f5f9'}; color:${this.ctCurrentRange === r ? '#fff' : '#475569'}; border:none; border-radius:6px; padding:4px 9px; font-size:10.5px; font-weight:700; cursor:pointer;">
                ${r.replace(/_/g, ' ').toUpperCase()}
              </button>
            `).join('')}
          </div>

          <div style="display:flex; gap:4px; align-items:center;">
            <div style="display:flex; background:#f1f5f9; border-radius:6px; padding:2px;">
              <button id="ctStaffTabBtn" style="background:${this.ctSubTab === 'staff' ? '#4f46e5' : 'transparent'}; color:${this.ctSubTab === 'staff' ? '#fff' : '#64748b'}; border:none; border-radius:4px; padding:4px 8px; font-size:10.5px; font-weight:700; cursor:pointer;">
                Staff
              </button>
              <button id="ctSlotsTabBtn" style="background:${this.ctSubTab === 'slots' ? '#4f46e5' : 'transparent'}; color:${this.ctSubTab === 'slots' ? '#fff' : '#64748b'}; border:none; border-radius:4px; padding:4px 8px; font-size:10.5px; font-weight:700; cursor:pointer;">
                2-Hr Slots
              </button>
            </div>
            <button id="ctRefreshBtn" style="background:#e0e7ff; color:#3730a3; border:none; border-radius:6px; padding:4px 8px; font-size:11px; cursor:pointer;">
              <i class="fas fa-sync-alt"></i>
            </button>
          </div>
        </div>
      </div>

      <!-- Call Tracking KPI Stat Cards -->
      <div style="display:grid; grid-template-columns:repeat(2, 1fr); gap:8px; margin-bottom:12px;">
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:10px 12px;">
          <div style="font-size:10px; font-weight:700; color:#64748b; text-transform:uppercase;">Total Calls</div>
          <div style="font-size:20px; font-weight:800; color:#2563eb; margin-top:2px;">${this.fmtNum(o.total_calls)}</div>
          <div style="font-size:9.5px; color:#059669; font-weight:600;">${ansRate} Connect Rate</div>
        </div>

        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:10px 12px;">
          <div style="font-size:10px; font-weight:700; color:#64748b; text-transform:uppercase;">Total Talk Time</div>
          <div style="font-size:20px; font-weight:800; color:#059669; margin-top:2px;">${this.fmtDurationSec(o.total_duration_seconds)}</div>
          <div style="font-size:9.5px; color:#64748b;">Avg Daily: ${this.fmtDurationSec(o.avg_daily_talk_time)}</div>
        </div>
      </div>

      <!-- Secondary 4-Card Grid for Calls -->
      <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:6px; margin-bottom:12px;">
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:8px; padding:8px 4px; text-align:center;">
          <div style="font-size:9px; color:#166534; font-weight:700;">OUTGOING</div>
          <div style="font-size:13px; font-weight:800; color:#15803d; margin-top:2px;">${this.fmtNum(o.outgoing)}</div>
        </div>
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:8px; padding:8px 4px; text-align:center;">
          <div style="font-size:9px; color:#1e40af; font-weight:700;">INCOMING</div>
          <div style="font-size:13px; font-weight:800; color:#1d4ed8; margin-top:2px;">${this.fmtNum(o.incoming)}</div>
        </div>
        <div style="background:#ffffff; border:1px solid #fecaca; border-radius:8px; padding:8px 4px; text-align:center;">
          <div style="font-size:9px; color:#dc2626; font-weight:700;">NOT ANS</div>
          <div style="font-size:13px; font-weight:800; color:#b91c1c; margin-top:2px;">${this.fmtNum(o.missed)}</div>
        </div>
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:8px; padding:8px 4px; text-align:center;">
          <div style="font-size:9px; color:#d97706; font-weight:700;">CRM MATCH</div>
          <div style="font-size:13px; font-weight:800; color:#b45309; margin-top:2px;">${this.fmtNum(o.crm_matched)}</div>
        </div>
      </div>

      <!-- Daily Trend Bar Chart -->
      ${trend.length > 0 ? `
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:12px; margin-bottom:14px;">
          <div style="font-size:12px; font-weight:700; color:#1e293b; margin-bottom:8px;">
            <i class="fas fa-chart-bar text-primary me-1"></i> Daily Call Volume Trend
          </div>
          <div style="display:flex; align-items:flex-end; gap:6px; height:65px; padding-top:8px;">
            ${trend.map((d: any) => {
              const h = Math.max(((d.calls || 0) / maxCalls) * 100, 6);
              return `
                <div style="flex:1; display:flex; flex-direction:column; align-items:center; height:100%; justify-content:flex-end;">
                  <div style="width:100%; height:${h}%; background:#4f46e5; border-radius:3px 3px 0 0;" title="${d.date}: ${d.calls} calls"></div>
                  <div style="font-size:8.5px; color:#64748b; margin-top:3px; white-space:nowrap;">${d.date ? d.date.slice(5) : ''}</div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      ` : ''}

      <!-- SubTab View 1: Staff Activity Table -->
      ${this.ctSubTab === 'staff' ? `
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:12px; margin-bottom:14px;">
          <div style="font-size:12.5px; font-weight:700; color:#1e293b; margin-bottom:10px;">
            Staff Call Activity &amp; Audio Recordings (${perStaff.length})
          </div>

          <div style="overflow-x:auto; -webkit-overflow-scrolling:touch;">
            <table style="width:100%; min-width:850px; border-collapse:collapse; font-size:11.5px;">
              <thead>
                <tr style="background:#f8fafc; border-bottom:2px solid #cbd5e1;">
                  <th style="padding:8px 6px; text-align:center; width:35px;">#</th>
                  <th style="padding:8px 10px; text-align:left;">Employee</th>
                  <th style="padding:8px 8px; text-align:center;">Total Calls</th>
                  <th style="padding:8px 8px; text-align:center; color:#166534;">Outgoing</th>
                  <th style="padding:8px 8px; text-align:center; color:#1e40af;">Incoming</th>
                  <th style="padding:8px 8px; text-align:center; color:#b91c1c;">Not Answered</th>
                  <th style="padding:8px 8px; text-align:center;">Total Duration</th>
                  <th style="padding:8px 8px; text-align:center;">CRM Matched</th>
                  <th style="padding:8px 10px; text-align:center;">Action</th>
                </tr>
              </thead>
              <tbody>
                ${perStaff.map((s: any, idx: number) => `
                  <tr style="border-bottom:1px solid #f1f5f9;">
                    <td style="padding:7px 6px; text-align:center; color:#64748b;">${idx + 1}</td>
                    <td style="padding:7px 10px;">
                      <div style="font-weight:700; color:#0f172a;">${this.escapeHtml(s.name || s.staff_name || '-')}</div>
                      <div style="font-size:9.5px; color:#64748b;">${this.escapeHtml(s.emp_code || '')} ${s.department ? '· ' + this.escapeHtml(s.department) : ''}</div>
                    </td>
                    <td style="padding:7px 8px; text-align:center; font-weight:800;">${this.fmtNum(s.total_calls)}</td>
                    <td style="padding:7px 8px; text-align:center; color:#15803d; font-weight:700;">${this.fmtNum(s.outgoing)}</td>
                    <td style="padding:7px 8px; text-align:center; color:#1d4ed8; font-weight:700;">${this.fmtNum(s.incoming)}</td>
                    <td style="padding:7px 8px; text-align:center; color:${s.missed > 0 ? '#b91c1c' : '#94a3b8'}; font-weight:700;">${this.fmtNum(s.missed)}</td>
                    <td style="padding:7px 8px; text-align:center;">${this.fmtDurationSec(s.total_duration_seconds || s.total_duration)}</td>
                    <td style="padding:7px 8px; text-align:center; color:#b45309; font-weight:700;">${this.fmtNum(s.crm_matched)}</td>
                    <td style="padding:7px 10px; text-align:center;">
                      <button class="view-staff-calls-btn" data-staffid="${s.staff_id}" data-staffname="${this.escapeHtml(s.name || s.staff_name || '')}" style="background:#eff6ff; color:#2563eb; border:1px solid #bfdbfe; border-radius:6px; padding:3px 8px; font-size:10.5px; font-weight:700; cursor:pointer;">
                        View Calls
                      </button>
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>
      ` : `
        <!-- SubTab View 2: 2-Hour Slots Table -->
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:12px; margin-bottom:14px;">
          <div style="font-size:12.5px; font-weight:700; color:#1e293b; margin-bottom:10px;">
            2-Hour Slot Call Activity Breakdown
          </div>

          <div style="overflow-x:auto; -webkit-overflow-scrolling:touch;">
            <table style="width:100%; min-width:650px; border-collapse:collapse; font-size:11.5px;">
              <thead>
                <tr style="background:#f8fafc; border-bottom:2px solid #cbd5e1;">
                  <th style="padding:8px 10px; text-align:left;">Staff</th>
                  <th style="padding:8px 8px; text-align:left;">Dept</th>
                  <th style="padding:8px 6px; text-align:center;">10-12</th>
                  <th style="padding:8px 6px; text-align:center;">12-14</th>
                  <th style="padding:8px 6px; text-align:center;">14-16</th>
                  <th style="padding:8px 6px; text-align:center;">16-18</th>
                  <th style="padding:8px 6px; text-align:center;">18-20</th>
                  <th style="padding:8px 6px; text-align:center;">Other</th>
                  <th style="padding:8px 8px; text-align:center;">Total</th>
                </tr>
              </thead>
              <tbody>
                ${(this.ctSlotData?.per_staff || []).map((row: any) => `
                  <tr style="border-bottom:1px solid #f1f5f9;">
                    <td style="padding:7px 10px; font-weight:700;">${this.escapeHtml(row.name || '-')} <small style="color:#64748b;">(${this.escapeHtml(row.emp_code || '')})</small></td>
                    <td style="padding:7px 8px; color:#64748b;">${this.escapeHtml(row.department || '-')}</td>
                    <td style="padding:7px 6px; text-align:center;">${(row.slots && row.slots.slot_1 && row.slots.slot_1.calls) || 0}</td>
                    <td style="padding:7px 6px; text-align:center;">${(row.slots && row.slots.slot_2 && row.slots.slot_2.calls) || 0}</td>
                    <td style="padding:7px 6px; text-align:center;">${(row.slots && row.slots.slot_3 && row.slots.slot_3.calls) || 0}</td>
                    <td style="padding:7px 6px; text-align:center;">${(row.slots && row.slots.slot_4 && row.slots.slot_4.calls) || 0}</td>
                    <td style="padding:7px 6px; text-align:center;">${(row.slots && row.slots.slot_5 && row.slots.slot_5.calls) || 0}</td>
                    <td style="padding:7px 6px; text-align:center;">${(row.slots && row.slots.other && row.slots.other.calls) || 0}</td>
                    <td style="padding:7px 8px; text-align:center; font-weight:800; color:#2563eb;">${(row.total && row.total.calls) || 0}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `}

      <!-- Staff Call Logs & Recordings Drilldown In-Page Section -->
      ${this.ctSelectedStaffId ? `
        <div style="background:#ffffff; border:1px solid #bfdbfe; border-radius:12px; padding:12px; margin-bottom:14px; box-shadow:0 4px 6px -1px rgba(37,99,235,0.05);">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <div style="font-size:12.5px; font-weight:700; color:#1e3a5f;">
              <i class="fas fa-headphones text-primary me-1"></i> Call Logs: ${this.escapeHtml(this.ctSelectedStaffName)} (${this.ctDrilldownCalls.length})
            </div>
            <button id="closeStaffCallsBtn" style="background:#f1f5f9; border:1px solid #cbd5e1; border-radius:6px; padding:3px 8px; font-size:11px; cursor:pointer;">Close</button>
          </div>

          <div style="overflow-x:auto; -webkit-overflow-scrolling:touch;">
            <table style="width:100%; min-width:700px; border-collapse:collapse; font-size:11px;">
              <thead>
                <tr style="background:#f8fafc; border-bottom:1px solid #cbd5e1;">
                  <th style="padding:6px 6px; text-align:center; width:30px;">#</th>
                  <th style="padding:6px 8px; text-align:left;">Date &amp; Time</th>
                  <th style="padding:6px 8px; text-align:left;">Phone</th>
                  <th style="padding:6px 8px; text-align:center;">Type</th>
                  <th style="padding:6px 8px; text-align:center;">Duration</th>
                  <th style="padding:6px 8px; text-align:left;">Lead Name</th>
                  <th style="padding:6px 8px; text-align:center;">Recording</th>
                </tr>
              </thead>
              <tbody>
                ${this.ctDrilldownCalls.length === 0 ? `
                  <tr><td colspan="7" style="text-align:center; padding:16px; color:#94a3b8;">No calls recorded for this staff member</td></tr>
                ` : this.ctDrilldownCalls.map((c: any, i: number) => {
                  const hasRec = Boolean((c.has_recording || c.recording_id) && c.recording_id);
                  return `
                    <tr style="border-bottom:1px solid #f1f5f9;">
                      <td style="padding:6px 6px; text-align:center; color:#64748b;">${i + 1}</td>
                      <td style="padding:6px 8px; white-space:nowrap;">${c.call_datetime ? new Date(c.call_datetime).toLocaleString('en-IN') : '-'}</td>
                      <td style="padding:6px 8px; font-weight:700;">${this.escapeHtml(c.phone_number || '-')}</td>
                      <td style="padding:6px 8px; text-align:center;">${this.callTypeBadge(c)}</td>
                      <td style="padding:6px 8px; text-align:center;">${this.fmtDurationSec(c.duration_seconds)}</td>
                      <td style="padding:6px 8px;">${this.escapeHtml(c.matched_lead_name || c.contact_name_crm || c.contact_name || '-')}</td>
                      <td style="padding:6px 8px; text-align:center;">
                        ${hasRec ? `
                          <button class="play-audio-btn" data-recid="${c.recording_id}" style="background:#0284c7; color:#fff; border:none; border-radius:4px; padding:2px 8px; font-size:10px; font-weight:700; cursor:pointer;">
                            <i class="fas fa-play me-1"></i>Play
                          </button>
                        ` : '<span style="color:#cbd5e1;">—</span>'}
                      </td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>
        </div>
      ` : ''}
    `;
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     TAB 4: QUALITY & QA AUDITS
     ═══════════════════════════════════════════════════════════════════════════ */

  private renderQualityTab(): string {
    const o = this.qaData?.summary || this.qaData?.overview || {};
    const execs = this.qaData?.executives || this.qaData?.executive_breakdown || [];

    const totalCalls = o.total_calls || 0;
    const qaSampled = o.quality_sampled ?? o.total_qa_sampled ?? 0;
    const qaReviewed = o.quality_reviewed ?? o.total_qa_reviewed ?? 0;
    const covRate = totalCalls > 0 ? ((qaSampled / totalCalls) * 100).toFixed(1) + '%' : '0%';

    return `
      <!-- QA Filter Controls -->
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:12px; margin-bottom:12px;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
          <div style="display:flex; background:#f1f5f9; border-radius:6px; padding:2px;">
            <button id="qaModeDayBtn" style="background:${this.qaMode === 'day' ? '#4f46e5' : 'transparent'}; color:${this.qaMode === 'day' ? '#fff' : '#64748b'}; border:none; border-radius:4px; padding:4px 10px; font-size:11px; font-weight:700; cursor:pointer;">
              Day Mode
            </button>
            <button id="qaModeRangeBtn" style="background:${this.qaMode === 'range' ? '#4f46e5' : 'transparent'}; color:${this.qaMode === 'range' ? '#fff' : '#64748b'}; border:none; border-radius:4px; padding:4px 10px; font-size:11px; font-weight:700; cursor:pointer;">
              Range Mode
            </button>
          </div>

          <div style="display:flex; gap:6px; align-items:center;">
            ${this.qaMode === 'day' ? `
              <input type="date" id="qaDateInput" value="${this.qaDate}" style="font-size:11.5px; padding:4px 6px; border:1px solid #cbd5e1; border-radius:6px;">
            ` : `
              <input type="date" id="qaRangeFromInput" value="${this.qaRangeFrom}" style="font-size:11px; padding:4px 5px; border:1px solid #cbd5e1; border-radius:6px; width:115px;">
              <span style="color:#64748b; font-size:10px;">to</span>
              <input type="date" id="qaRangeToInput" value="${this.qaRangeTo}" style="font-size:11px; padding:4px 5px; border:1px solid #cbd5e1; border-radius:6px; width:115px;">
            `}
            <button id="qaSubmitBtn" style="background:#4f46e5; color:#fff; border:none; border-radius:6px; padding:5px 12px; font-size:11px; font-weight:700; cursor:pointer;">
              <i class="fas fa-sync me-1"></i>Load
            </button>
          </div>
        </div>
      </div>

      <!-- QA KPI Cards -->
      <div style="display:grid; grid-template-columns:repeat(2, 1fr); gap:8px; margin-bottom:12px;">
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:10px 12px;">
          <div style="font-size:10px; font-weight:700; color:#64748b; text-transform:uppercase;">Monitored Calls</div>
          <div style="font-size:20px; font-weight:800; color:#2563eb; margin-top:2px;">${this.fmtNum(totalCalls)}</div>
          <div style="font-size:9.5px; color:#64748b;">${covRate} Audit Coverage</div>
        </div>

        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:10px 12px;">
          <div style="font-size:10px; font-weight:700; color:#64748b; text-transform:uppercase;">Avg Quality Score</div>
          <div style="font-size:20px; font-weight:800; color:#0f766e; margin-top:2px;">${this.scoreBadge(o.avg_quality_score)}</div>
          <div style="font-size:9.5px; color:#059669;">${this.fmtNum(qaReviewed)} Reviewed</div>
        </div>
      </div>

      <!-- Executive Quality Breakdown Table -->
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:12px; margin-bottom:14px;">
        <div style="font-size:12.5px; font-weight:700; color:#1e293b; margin-bottom:10px;">
          Executive Quality Breakdown (${execs.length})
        </div>

        <div style="overflow-x:auto; -webkit-overflow-scrolling:touch;">
          <table style="width:100%; min-width:750px; border-collapse:collapse; font-size:11.5px;">
            <thead>
              <tr style="background:#f8fafc; border-bottom:2px solid #cbd5e1;">
                <th style="padding:8px 6px; text-align:center; width:30px;"></th>
                <th style="padding:8px 10px; text-align:left;">Executive</th>
                <th style="padding:8px 8px; text-align:center;">Total Calls</th>
                <th style="padding:8px 8px; text-align:center; color:#15803d;">Outgoing</th>
                <th style="padding:8px 8px; text-align:center; color:#1d4ed8;">Incoming</th>
                <th style="padding:8px 8px; text-align:center; color:#b91c1c;">Not Answered</th>
                <th style="padding:8px 8px; text-align:center;">QA Sampled</th>
                <th style="padding:8px 8px; text-align:center; color:#059669;">Reviewed</th>
                <th style="padding:8px 8px; text-align:center;">Score</th>
              </tr>
            </thead>
            <tbody>
              ${execs.length === 0 ? `
                <tr><td colspan="9" style="text-align:center; padding:20px; color:#94a3b8;">No QA records found for this period</td></tr>
              ` : execs.map((e: any, idx: number) => {
                const c = e.calls || {};
                const q = e.quality || {};
                const isOpen = !!this.expandedQaMap[idx];

                return `
                  <tr class="qa-expand-row" data-idx="${idx}" style="border-bottom:1px solid #f1f5f9; cursor:pointer;">
                    <td style="padding:7px 6px; text-align:center; color:#94a3b8;">
                      <i class="fas ${isOpen ? 'fa-chevron-down' : 'fa-chevron-right'}" style="font-size:10px;"></i>
                    </td>
                    <td style="padding:7px 10px;">
                      <div style="font-weight:700; color:#0f172a;">${this.escapeHtml(e.staff_name || '')}</div>
                      <div style="font-size:9.5px; color:#64748b;">${this.escapeHtml(e.emp_code || '')} ${e.role ? '· ' + this.escapeHtml(e.role) : ''}</div>
                    </td>
                    <td style="padding:7px 8px; text-align:center; font-weight:800;">${this.fmtNum(c.total)}</td>
                    <td style="padding:7px 8px; text-align:center; color:#15803d; font-weight:700;">${this.fmtNum(c.outgoing)}</td>
                    <td style="padding:7px 8px; text-align:center; color:#1d4ed8; font-weight:700;">${this.fmtNum(c.incoming)}</td>
                    <td style="padding:7px 8px; text-align:center; color:${c.missed > 0 ? '#b91c1c' : '#94a3b8'}; font-weight:700;">${this.fmtNum(c.missed)}</td>
                    <td style="padding:7px 8px; text-align:center;">${this.fmtNum(q.sampled)}</td>
                    <td style="padding:7px 8px; text-align:center; color:#059669; font-weight:700;">${this.fmtNum(q.reviewed)}</td>
                    <td style="padding:7px 8px; text-align:center;">${this.scoreBadge(q.avg_score)}</td>
                  </tr>
                  ${isOpen ? `
                    <tr style="background:#f8faff;">
                      <td colspan="9" style="padding:10px 14px; border-bottom:1px solid #bfdbfe;">
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; font-size:11px;">
                          <div>
                            <div style="font-weight:700; color:#1e40af; margin-bottom:4px;">Call Breakdown</div>
                            <div>Outgoing: <strong>${c.outgoing || 0}</strong></div>
                            <div>Incoming: <strong>${c.incoming || 0}</strong></div>
                            <div>Not Answered: <strong>${c.missed || 0}</strong></div>
                            <div>Avg Duration: <strong>${this.fmtDurationSec(c.avg_duration_seconds)}</strong></div>
                          </div>
                          <div>
                            <div style="font-weight:700; color:#059669; margin-bottom:4px;">Quality Scorecard</div>
                            <div>Sampled: <strong>${q.sampled || 0}</strong></div>
                            <div>Reviewed: <strong>${q.reviewed || 0}</strong></div>
                            <div>Pending: <strong>${q.pending || 0}</strong></div>
                            <div>Avg Score: <strong>${q.avg_score ? parseFloat(q.avg_score).toFixed(1) : 'N/A'}</strong></div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  ` : ''}
                `;
              }).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     TAB 5: AUTO DIALER
     ═══════════════════════════════════════════════════════════════════════════ */

  private renderDialerTab(): string {
    const o = this.dialerData?.overview || {};
    const attempts = this.dialerData?.recent_attempts || [];
    const connectRate = o.total_dials > 0 ? ((o.answered || 0) / o.total_dials * 100).toFixed(1) + '%' : '0%';

    return `
      <!-- Dialer Controls -->
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:12px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
        <div style="display:flex; gap:4px;">
          ${['today', 'week', 'month'].map(p => `
            <button class="dialer-p-btn ${this.dialerPeriod === p ? 'active' : ''}" data-period="${p}" style="background:${this.dialerPeriod === p ? '#4f46e5' : '#f1f5f9'}; color:${this.dialerPeriod === p ? '#fff' : '#475569'}; border:none; border-radius:6px; padding:5px 12px; font-size:11px; font-weight:700; cursor:pointer;">
              ${p.toUpperCase()}
            </button>
          `).join('')}
        </div>

        <button id="openDialerPageBtn" style="background:#059669; color:#fff; border:none; border-radius:6px; padding:6px 14px; font-size:11px; font-weight:700; cursor:pointer;">
          <i class="fas fa-phone-alt me-1"></i>Open Auto Dialer
        </button>
      </div>

      <!-- Dialer KPI Cards -->
      <div style="display:grid; grid-template-columns:repeat(2, 1fr); gap:8px; margin-bottom:12px;">
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:10px 12px;">
          <div style="font-size:10px; font-weight:700; color:#64748b; text-transform:uppercase;">Total Dials</div>
          <div style="font-size:20px; font-weight:800; color:#2563eb; margin-top:2px;">${this.fmtNum(o.total_dials)}</div>
          <div style="font-size:9.5px; color:#059669; font-weight:600;">${connectRate} Answered (${this.fmtNum(o.answered)})</div>
        </div>

        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:10px 12px;">
          <div style="font-size:10px; font-weight:700; color:#64748b; text-transform:uppercase;">Dialer Sessions</div>
          <div style="font-size:20px; font-weight:800; color:#7c3aed; margin-top:2px;">${this.fmtNum(o.total_sessions)}</div>
          <div style="font-size:9.5px; color:#64748b;">Busy: ${this.fmtNum(o.busy)} · DNC: ${this.fmtNum(o.do_not_call)}</div>
        </div>
      </div>

      <!-- Recent Dialer Attempts Table -->
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:12px; margin-bottom:14px;">
        <div style="font-size:12.5px; font-weight:700; color:#1e293b; margin-bottom:10px;">
          Recent Dialer Attempts (${attempts.length})
        </div>

        <div style="overflow-x:auto; -webkit-overflow-scrolling:touch;">
          <table style="width:100%; min-width:600px; border-collapse:collapse; font-size:11.5px;">
            <thead>
              <tr style="background:#f8fafc; border-bottom:2px solid #cbd5e1;">
                <th style="padding:8px 6px; text-align:center; width:35px;">#</th>
                <th style="padding:8px 10px; text-align:left;">Lead</th>
                <th style="padding:8px 8px; text-align:center;">Outcome</th>
                <th style="padding:8px 8px; text-align:center;">Duration</th>
                <th style="padding:8px 8px; text-align:center;">Updated Status</th>
                <th style="padding:8px 10px; text-align:left;">Time</th>
              </tr>
            </thead>
            <tbody>
              ${attempts.length === 0 ? `
                <tr><td colspan="6" style="text-align:center; padding:20px; color:#94a3b8;">No dialer attempts in this period</td></tr>
              ` : attempts.map((a: any, i: number) => `
                <tr style="border-bottom:1px solid #f1f5f9;">
                  <td style="padding:7px 6px; text-align:center; color:#64748b;">${i + 1}</td>
                  <td style="padding:7px 10px;">
                    <div style="font-weight:700; color:#0f172a;">${this.escapeHtml(a.lead_name || 'Lead #' + a.lead_id)}</div>
                    <div style="font-size:9.5px; color:#64748b;">${this.escapeHtml(a.lead_phone || '')}</div>
                  </td>
                  <td style="padding:7px 8px; text-align:center;">
                    <span style="background:${a.call_outcome === 'answered' ? '#dcfce7' : '#fee2e2'}; color:${a.call_outcome === 'answered' ? '#166534' : '#991b1b'}; padding:2px 6px; border-radius:4px; font-size:10px; font-weight:700;">
                      ${this.escapeHtml(a.call_outcome || '-')}
                    </span>
                  </td>
                  <td style="padding:7px 8px; text-align:center;">${this.fmtDurationSec(a.duration_seconds)}</td>
                  <td style="padding:7px 8px; text-align:center; color:#475569; font-weight:600;">${this.escapeHtml(a.status_updated_to || '-')}</td>
                  <td style="padding:7px 10px; font-size:10.5px; color:#64748b;">${a.dialed_at ? new Date(a.dialed_at).toLocaleTimeString('en-IN') : '-'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     TAB 6, 7, 8: STATUS WISE, CATEGORY WISE, COMPANY WISE
     ═══════════════════════════════════════════════════════════════════════════ */

  private renderStatusWiseTab(): string {
    const sw = this.dashData?.status_wise;
    if (!sw) return `<div style="text-align:center; padding:32px; color:#94a3b8;">No status-wise records.</div>`;
    const emps = sw.employees || [];
    const special = sw.special_rows || [];

    return `
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:12px; margin-bottom:14px;">
        <div style="font-size:12.5px; font-weight:700; color:#1e293b; margin-bottom:10px;">
          Status Wise Lead Matrix (${emps.length})
        </div>
        <div style="overflow-x:auto; -webkit-overflow-scrolling:touch;">
          <table style="width:100%; min-width:1250px; border-collapse:collapse; font-size:11.5px;">
            <thead>
              ${this.buildStandardHead([{ label: '#', width: 35 }, { label: 'Employee', width: 180 }])}
            </thead>
            <tbody>
              ${special.map((sp: any) => `
                <tr style="background:#eff6ff;">
                  <td style="position:sticky; left:0; z-index:2; background:#eff6ff; padding:7px 6px; text-align:center; border-bottom:1px solid #cbd5e1;"><i class="fas fa-building text-primary"></i></td>
                  <td style="position:sticky; left:35px; z-index:2; background:#eff6ff; padding:7px 10px; font-weight:700; color:#1e3a5f; border-bottom:1px solid #cbd5e1; border-right:1px solid #cbd5e1;">${this.escapeHtml(sp.name)}</td>
                  ${this.buildStandardRow(sp, { emp_id: sp.special_type, emp_name: sp.name })}
                </tr>
              `).join('')}
              ${emps.map((e: any, idx: number) => `
                <tr>
                  <td style="position:sticky; left:0; z-index:2; background:#fff; padding:7px 6px; text-align:center; color:#64748b; border-bottom:1px solid #f1f5f9;">${idx + 1}</td>
                  <td style="position:sticky; left:35px; z-index:2; background:#fff; padding:7px 10px; font-weight:700; border-bottom:1px solid #f1f5f9; border-right:1px solid #e2e8f0;">
                    <div>${this.escapeHtml(e.name)}</div>
                    <small style="color:#64748b;">${this.escapeHtml(e.emp_code || '')}</small>
                  </td>
                  ${this.buildStandardRow(e, { emp_id: e.emp_id, emp_name: e.name })}
                </tr>
              `).join('')}
            </tbody>
            <tfoot>
              <tr style="background:#f8fafc; font-weight:800;">
                <td style="position:sticky; left:0; z-index:2; background:#f8fafc; border-bottom:2px solid #cbd5e1;"></td>
                <td style="position:sticky; left:35px; z-index:2; background:#f8fafc; padding:8px 10px; border-right:1px solid #cbd5e1;">TOTAL</td>
                ${this.buildStandardRow(sw.totals || this.calcTotals(emps), { emp_id: 'all', emp_name: 'TOTAL' })}
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    `;
  }

  private renderCategoryWiseTab(): string {
    const cats = this.dashData?.category_wise || [];
    return `
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:12px; margin-bottom:14px;">
        <div style="font-size:12.5px; font-weight:700; color:#1e293b; margin-bottom:10px;">
          Category Wise Performance (${cats.length})
        </div>
        <div style="overflow-x:auto; -webkit-overflow-scrolling:touch;">
          <table style="width:100%; min-width:1150px; border-collapse:collapse; font-size:11.5px;">
            <thead>
              ${this.buildStandardHead([{ label: 'Category', width: 180 }])}
            </thead>
            <tbody>
              ${cats.map((c: any) => {
                const extra = { category_name: c.category_name, category_ids: c.category_ids || (c.category_id ? String(c.category_id) : 'none') };
                return `
                  <tr>
                    <td style="position:sticky; left:0; z-index:2; background:#ffffff; padding:7px 10px; font-weight:700; color:#0f172a; border-bottom:1px solid #f1f5f9; border-right:1px solid #e2e8f0;">
                      ${this.escapeHtml(c.category_name || 'General')}
                    </td>
                    ${this.buildStandardRow(c, extra)}
                  </tr>
                `;
              }).join('')}
            </tbody>
            <tfoot>
              <tr style="background:#f8fafc; font-weight:800;">
                <td style="position:sticky; left:0; z-index:2; background:#f8fafc; padding:8px 10px; border-right:1px solid #cbd5e1;">TOTAL</td>
                ${this.buildStandardRow(this.calcTotals(cats))}
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    `;
  }

  private renderCompanyWiseTab(): string {
    const comps = this.dashData?.company_wise || [];
    return `
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:12px; margin-bottom:14px;">
        <div style="font-size:12.5px; font-weight:700; color:#1e293b; margin-bottom:10px;">
          Company Wise Performance (${comps.length})
        </div>
        <div style="overflow-x:auto; -webkit-overflow-scrolling:touch;">
          <table style="width:100%; min-width:1150px; border-collapse:collapse; font-size:11.5px;">
            <thead>
              ${this.buildStandardHead([{ label: 'Company', width: 190 }])}
            </thead>
            <tbody>
              ${comps.map((c: any) => {
                const extra = { company_id: c.company_id, company_name: c.company_name };
                return `
                  <tr>
                    <td style="position:sticky; left:0; z-index:2; background:#ffffff; padding:7px 10px; font-weight:700; color:#0f172a; border-bottom:1px solid #f1f5f9; border-right:1px solid #e2e8f0;">
                      ${this.escapeHtml(c.company_name || 'Company')}
                    </td>
                    ${this.buildStandardRow(c, extra)}
                  </tr>
                `;
              }).join('')}
            </tbody>
            <tfoot>
              <tr style="background:#f8fafc; font-weight:800;">
                <td style="position:sticky; left:0; z-index:2; background:#f8fafc; padding:8px 10px; border-right:1px solid #cbd5e1;">TOTAL</td>
                ${this.buildStandardRow(this.calcTotals(comps))}
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    `;
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     TAB 9: EARNINGS & INCENTIVE ACHIEVEMENTS
     ═══════════════════════════════════════════════════════════════════════════ */

  private renderEarningsTab(): string {
    const rows = this.earnData || [];

    // Extract category slugs
    const catMap = new Map<string, string>();
    rows.forEach(r => {
      (r.categories || []).forEach((c: any) => {
        if (!catMap.has(c.slug)) {
          const clean = (c.slug || '').replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase());
          catMap.set(c.slug, clean);
        }
      });
    });
    const catSlugs = Array.from(catMap.keys());

    return `
      <!-- Earnings Filter Controls -->
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:12px; margin-bottom:12px;">
        <div style="display:flex; flex-wrap:wrap; align-items:flex-end; gap:8px;">
          <div>
            <label style="font-size:10px; font-weight:700; color:#64748b; display:block; margin-bottom:2px;">Month</label>
            <select id="earnMonthSelect" style="font-size:11.5px; padding:5px 8px; border:1px solid #cbd5e1; border-radius:6px; background:#fff;">
              ${[1,2,3,4,5,6,7,8,9,10,11,12].map(m => `
                <option value="${m}" ${m === this.earnMonth ? 'selected' : ''}>
                  ${new Date(2026, m - 1, 1).toLocaleString('en-US', { month: 'long' })}
                </option>
              `).join('')}
            </select>
          </div>

          <div>
            <label style="font-size:10px; font-weight:700; color:#64748b; display:block; margin-bottom:2px;">Year</label>
            <select id="earnYearSelect" style="font-size:11.5px; padding:5px 8px; border:1px solid #cbd5e1; border-radius:6px; background:#fff;">
              ${[2026, 2025, 2024].map(y => `
                <option value="${y}" ${y === this.earnYear ? 'selected' : ''}>${y}</option>
              `).join('')}
            </select>
          </div>

          <div style="flex:1; min-width:130px;">
            <label style="font-size:10px; font-weight:700; color:#64748b; display:block; margin-bottom:2px;">Company</label>
            <select id="earnCompanySelect" style="width:100%; font-size:11.5px; padding:5px 8px; border:1px solid #cbd5e1; border-radius:6px; background:#fff;">
              <option value="">All Companies</option>
              ${this.companies.map(c => `<option value="${c.id}" ${String(c.id) === this.earnCompanyId ? 'selected' : ''}>${this.escapeHtml(c.company_name)}</option>`).join('')}
            </select>
          </div>

          <button id="earnCalculateBtn" style="background:#4f46e5; color:#fff; border:none; border-radius:6px; padding:6px 14px; font-size:11.5px; font-weight:700; cursor:pointer;">
            <i class="fas fa-calculator me-1"></i>Calculate
          </button>
        </div>
      </div>

      ${this.earnLoading ? `
        <div style="text-align:center; padding:32px; color:#4f46e5;">
          <i class="fas fa-spinner fa-spin me-2"></i>Calculating earnings...
        </div>
      ` : rows.length === 0 ? `
        <div style="text-align:center; padding:32px; color:#94a3b8; background:#fff; border-radius:12px; border:1px solid #e2e8f0;">
          <i class="fas fa-wallet" style="font-size:24px; opacity:0.5; margin-bottom:8px;"></i>
          <div>Click Calculate to load earnings for the selected month</div>
        </div>
      ` : `
        <!-- 1. Achievement Matrix (Units Achieved) -->
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:12px; margin-bottom:14px;">
          <div style="font-size:12.5px; font-weight:700; color:#1e293b; margin-bottom:10px;">
            <i class="fas fa-star text-warning me-1"></i> Achievement Matrix (${rows.length})
          </div>

          <div style="overflow-x:auto; -webkit-overflow-scrolling:touch;">
            <table style="width:100%; min-width:550px; border-collapse:collapse; font-size:11.5px;">
              <thead>
                <tr style="background:#f8fafc; border-bottom:2px solid #cbd5e1;">
                  <th style="padding:8px 10px; text-align:left;">Employee</th>
                  ${catSlugs.map(s => `<th style="padding:8px 8px; text-align:center;">${catMap.get(s)}</th>`).join('')}
                </tr>
              </thead>
              <tbody>
                ${rows.map(r => {
                  const empCats: Record<string, number> = {};
                  (r.categories || []).forEach((c: any) => empCats[c.slug] = c.achieved_count || 0);
                  return `
                    <tr style="border-bottom:1px solid #f1f5f9;">
                      <td style="padding:7px 10px; font-weight:700;">${this.escapeHtml(r.name || '-')} <small style="color:#64748b;">(${this.escapeHtml(r.emp_code || '')})</small></td>
                      ${catSlugs.map(s => `<td style="padding:7px 8px; text-align:center; font-weight:600;">${empCats[s] || 0}</td>`).join('')}
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>
        </div>

        <!-- 2. Earnings & Payout Summary -->
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:12px; margin-bottom:14px;">
          <div style="font-size:12.5px; font-weight:700; color:#1e293b; margin-bottom:10px;">
            <i class="fas fa-wallet text-success me-1"></i> Earnings &amp; Payout Summary
          </div>

          <div style="overflow-x:auto; -webkit-overflow-scrolling:touch;">
            <table style="width:100%; min-width:600px; border-collapse:collapse; font-size:11.5px;">
              <thead>
                <tr style="background:#f8fafc; border-bottom:2px solid #cbd5e1;">
                  <th style="padding:8px 10px; text-align:left;">Employee</th>
                  ${catSlugs.map(s => `<th style="padding:8px 8px; text-align:center;">${catMap.get(s)} ₹</th>`).join('')}
                  <th style="padding:8px 10px; text-align:right; color:#059669;">Total Payout</th>
                  <th style="padding:8px 8px; text-align:center;">Status</th>
                </tr>
              </thead>
              <tbody>
                ${rows.map(r => {
                  const empPay: Record<string, number> = {};
                  (r.categories || []).forEach((c: any) => empPay[c.slug] = c.incentive_earned || 0);
                  return `
                    <tr style="border-bottom:1px solid #f1f5f9;">
                      <td style="padding:7px 10px; font-weight:700;">${this.escapeHtml(r.name || '-')} <small style="color:#64748b;">(${this.escapeHtml(r.emp_code || '')})</small></td>
                      ${catSlugs.map(s => `<td style="padding:7px 8px; text-align:center;">₹${this.fmtNum(empPay[s] || 0)}</td>`).join('')}
                      <td style="padding:7px 10px; text-align:right; font-weight:800; color:#059669;">₹${this.fmtNum(r.total_incentive_earned || 0)}</td>
                      <td style="padding:7px 8px; text-align:center;"><span style="background:#dcfce7; color:#166534; padding:2px 6px; border-radius:4px; font-size:10px; font-weight:700;">Calculated</span></td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `}
    `;
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     MODAL 1: COUNT DRILLDOWN BOTTOM SHEET
     ═══════════════════════════════════════════════════════════════════════════ */

  private renderDrilldownModal(): string {
    return `
      <div id="drilldownOverlay" style="position:fixed; inset:0; background:rgba(0,0,0,0.5); z-index:1050; display:flex; align-items:flex-end; justify-content:center;">
        <div style="background:#ffffff; width:100%; max-width:768px; max-height:90vh; border-radius:16px 16px 0 0; display:flex; flex-direction:column; overflow:hidden; box-shadow:0 -10px 25px rgba(0,0,0,0.2);">
          
          <!-- Header -->
          <div style="padding:14px 16px; border-bottom:1px solid #e2e8f0; display:flex; justify-content:space-between; align-items:center; background:#f8fafc;">
            <div>
              <div style="font-size:14px; font-weight:800; color:#0f172a;">${this.escapeHtml(this.drilldownTitle)}</div>
              <div style="font-size:11px; color:#64748b;">${this.escapeHtml(this.drilldownSubtitle)} · <strong style="color:#2563eb;">${this.drilldownTotalCount} Leads</strong></div>
            </div>
            <button id="closeDrilldownModalBtn" style="background:#e2e8f0; border:none; width:28px; height:28px; border-radius:50%; display:flex; align-items:center; justify-content:center; color:#475569; font-size:12px; cursor:pointer;">
              <i class="fas fa-times"></i>
            </button>
          </div>

          <!-- Search & Telecaller Filter Bar -->
          <div style="padding:10px 14px; background:#ffffff; border-bottom:1px solid #f1f5f9; display:flex; gap:8px;">
            <input type="text" id="drilldownSearchInput" value="${this.escapeHtml(this.drilldownSearch)}" placeholder="Search customer or phone..." style="flex:1; font-size:11.5px; padding:6px 10px; border:1px solid #cbd5e1; border-radius:6px;">
            
            <select id="drilldownTelecallerSelect" style="font-size:11.5px; padding:6px 8px; border:1px solid #cbd5e1; border-radius:6px; background:#fff; max-width:140px;">
              <option value="">All Telecallers</option>
              <option value="unassigned" ${this.drilldownTelecallerId === 'unassigned' ? 'selected' : ''}>Unassigned</option>
              ${this.drilldownTelecallers.map(tc => `
                <option value="${tc.id}" ${String(tc.id) === this.drilldownTelecallerId ? 'selected' : ''}>${this.escapeHtml(tc.name)}</option>
              `).join('')}
            </select>

            <button id="execDrilldownSearchBtn" style="background:#4f46e5; color:#fff; border:none; border-radius:6px; padding:6px 12px; font-size:11.5px; font-weight:700; cursor:pointer;">
              <i class="fas fa-search"></i>
            </button>
          </div>

          <!-- Body / Leads Table -->
          <div style="flex:1; overflow-y:auto; overflow-x:auto; padding:10px 14px; -webkit-overflow-scrolling:touch;">
            ${this.drilldownLoading ? `
              <div style="text-align:center; padding:48px 16px; color:#4f46e5;">
                <i class="fas fa-circle-notch fa-spin" style="font-size:24px; margin-bottom:8px;"></i>
                <div style="font-size:12px; font-weight:600;">Loading leads...</div>
              </div>
            ` : this.drilldownItems.length === 0 ? `
              <div style="text-align:center; padding:36px; color:#94a3b8;">
                <i class="fas fa-inbox" style="font-size:24px; margin-bottom:8px;"></i>
                <div>No leads found matching criteria</div>
              </div>
            ` : `
              <table style="width:100%; min-width:850px; border-collapse:collapse; font-size:11px;">
                <thead>
                  <tr style="background:#f8fafc; border-bottom:2px solid #cbd5e1;">
                    <th style="padding:6px 6px; text-align:center; width:30px;">#</th>
                    <th style="padding:6px 8px; text-align:left;">Date</th>
                    <th style="padding:6px 8px; text-align:left;">Customer Name</th>
                    <th style="padding:6px 8px; text-align:left;">Phone / Dial</th>
                    <th style="padding:6px 8px; text-align:left;">Category</th>
                    <th style="padding:6px 8px; text-align:left;">Telecaller</th>
                    <th style="padding:6px 8px; text-align:center;">Status</th>
                    <th style="padding:6px 8px; text-align:left;">Last Interaction</th>
                    <th style="padding:6px 8px; text-align:center;">Action</th>
                  </tr>
                </thead>
                <tbody>
                  ${this.drilldownItems.map((l: any, idx: number) => {
                    const rowIdx = (this.drilldownCurrentPage - 1) * 20 + idx + 1;
                    return `
                      <tr style="border-bottom:1px solid #f1f5f9;">
                        <td style="padding:6px 6px; text-align:center; color:#64748b;">${rowIdx}</td>
                        <td style="padding:6px 8px; white-space:nowrap; color:#64748b;">${l.lead_date || '-'}</td>
                        <td style="padding:6px 8px; font-weight:700; color:#0f172a;">${this.escapeHtml(l.customer_name || '-')}</td>
                        <td style="padding:6px 8px;">
                          ${l.phone && l.phone !== '-' ? `
                            <button class="lead-dial-btn" data-phone="${this.escapeHtml(l.phone)}" data-name="${this.escapeHtml(l.customer_name || 'Contact')}" data-leadid="${l.id}" style="background:#dcfce7; color:#166534; border:1px solid #86efac; border-radius:4px; padding:2px 7px; font-size:10.5px; font-weight:700; cursor:pointer; display:inline-flex; align-items:center; gap:4px;">
                              <i class="fas fa-phone-alt"></i> ${this.escapeHtml(l.phone)}
                            </button>
                          ` : '-'}
                        </td>
                        <td style="padding:6px 8px;"><span style="background:#f1f5f9; padding:2px 6px; border-radius:4px; font-size:9.5px;">${this.escapeHtml(l.category || '-')}</span></td>
                        <td style="padding:6px 8px; color:#475569;">${this.escapeHtml(l.telecaller_name || '-')}</td>
                        <td style="padding:6px 8px; text-align:center;"><span style="background:#e0e7ff; color:#3730a3; padding:2px 6px; border-radius:4px; font-size:9.5px; font-weight:700;">${this.escapeHtml(l.latest_status || '-')}</span></td>
                        <td style="padding:6px 8px; font-size:9.5px; color:#64748b;">
                          ${l.last_call?.call_datetime ? `${l.last_call.call_datetime} (${l.last_call.duration_str || ''})` : '-'}
                        </td>
                        <td style="padding:6px 8px; text-align:center;">
                          <button class="lead-history-btn" data-leadid="${l.id}" data-leadname="${this.escapeHtml(l.customer_name || 'Lead')}" style="background:#eff6ff; color:#2563eb; border:1px solid #bfdbfe; border-radius:4px; padding:2px 7px; font-size:10px; font-weight:700; cursor:pointer;">
                            <i class="fas fa-history me-1"></i>History
                          </button>
                        </td>
                      </tr>
                    `;
                  }).join('')}
                </tbody>
              </table>
            `}
          </div>

          <!-- Pagination Footer -->
          <div style="padding:10px 16px; border-top:1px solid #e2e8f0; background:#f8fafc; display:flex; justify-content:space-between; align-items:center;">
            <button id="drilldownPrevBtn" ${this.drilldownCurrentPage <= 1 ? 'disabled' : ''} style="background:${this.drilldownCurrentPage <= 1 ? '#e2e8f0' : '#4f46e5'}; color:${this.drilldownCurrentPage <= 1 ? '#94a3b8' : '#fff'}; border:none; border-radius:6px; padding:5px 12px; font-size:11px; font-weight:700; cursor:pointer;">
              Previous
            </button>
            <span style="font-size:11px; color:#64748b; font-weight:600;">Page ${this.drilldownCurrentPage} of ${this.drilldownTotalPages}</span>
            <button id="drilldownNextBtn" ${this.drilldownCurrentPage >= this.drilldownTotalPages ? 'disabled' : ''} style="background:${this.drilldownCurrentPage >= this.drilldownTotalPages ? '#e2e8f0' : '#4f46e5'}; color:${this.drilldownCurrentPage >= this.drilldownTotalPages ? '#94a3b8' : '#fff'}; border:none; border-radius:6px; padding:5px 12px; font-size:11px; font-weight:700; cursor:pointer;">
              Next
            </button>
          </div>

        </div>
      </div>
    `;
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     MODAL 2: LEAD COMMUNICATION HISTORY MODAL
     ═══════════════════════════════════════════════════════════════════════════ */

  private renderHistoryModal(): string {
    return `
      <div id="historyOverlay" style="position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:1060; display:flex; align-items:flex-end; justify-content:center;">
        <div style="background:#ffffff; width:100%; max-width:768px; max-height:85vh; border-radius:16px 16px 0 0; display:flex; flex-direction:column; overflow:hidden; box-shadow:0 -10px 25px rgba(0,0,0,0.25);">
          
          <!-- Header -->
          <div style="padding:14px 16px; border-bottom:1px solid #e2e8f0; display:flex; justify-content:space-between; align-items:center; background:#f8fafc;">
            <div>
              <div style="font-size:13.5px; font-weight:800; color:#0f172a;">Communication History — ${this.escapeHtml(this.historyLeadName)}</div>
              <div style="font-size:10.5px; color:#64748b;">Lead ID: #${this.historyLeadId}</div>
            </div>
            <button id="closeHistoryModalBtn" style="background:#e2e8f0; border:none; width:28px; height:28px; border-radius:50%; display:flex; align-items:center; justify-content:center; color:#475569; font-size:12px; cursor:pointer;">
              <i class="fas fa-times"></i>
            </button>
          </div>

          <!-- History Tabs -->
          <div style="display:flex; background:#f1f5f9; padding:4px 16px; border-bottom:1px solid #e2e8f0; gap:6px;">
            <button class="hist-tab-btn ${this.historyActiveTab === 'calls' ? 'active' : ''}" data-htab="calls" style="background:${this.historyActiveTab === 'calls' ? '#4f46e5' : 'transparent'}; color:${this.historyActiveTab === 'calls' ? '#fff' : '#475569'}; border:none; border-radius:6px; padding:5px 12px; font-size:11px; font-weight:700; cursor:pointer;">
              <i class="fas fa-phone-alt me-1"></i>Calls (${this.historyCalls.length})
            </button>
            <button class="hist-tab-btn ${this.historyActiveTab === 'wa' ? 'active' : ''}" data-htab="wa" style="background:${this.historyActiveTab === 'wa' ? '#4f46e5' : 'transparent'}; color:${this.historyActiveTab === 'wa' ? '#fff' : '#475569'}; border:none; border-radius:6px; padding:5px 12px; font-size:11px; font-weight:700; cursor:pointer;">
              <i class="fab fa-whatsapp me-1"></i>WhatsApp (${this.historyWhatsApp.length})
            </button>
            <button class="hist-tab-btn ${this.historyActiveTab === 'notes' ? 'active' : ''}" data-htab="notes" style="background:${this.historyActiveTab === 'notes' ? '#4f46e5' : 'transparent'}; color:${this.historyActiveTab === 'notes' ? '#fff' : '#475569'}; border:none; border-radius:6px; padding:5px 12px; font-size:11px; font-weight:700; cursor:pointer;">
              <i class="fas fa-sticky-note me-1"></i>Notes (${this.historyNotes.length})
            </button>
          </div>

          <!-- History Content -->
          <div style="flex:1; overflow-y:auto; padding:14px; -webkit-overflow-scrolling:touch;">
            ${this.historyLoading ? `
              <div style="text-align:center; padding:32px; color:#4f46e5;">
                <i class="fas fa-circle-notch fa-spin" style="font-size:20px; margin-bottom:8px;"></i>
                <div style="font-size:11.5px;">Loading communication logs...</div>
              </div>
            ` : this.historyActiveTab === 'calls' ? `
              <!-- Calls View -->
              ${this.historyCalls.length === 0 ? `
                <div style="text-align:center; padding:24px; color:#94a3b8;">No call recordings found for this lead.</div>
              ` : `
                <div style="display:flex; flex-direction:column; gap:8px;">
                  ${this.historyCalls.map((c: any) => `
                    <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:10px; display:flex; justify-content:space-between; align-items:center;">
                      <div>
                        <div style="font-size:11.5px; font-weight:700; color:#0f172a;">${this.callTypeBadge(c)} ${c.duration_str ? '· ' + c.duration_str : ''}</div>
                        <div style="font-size:10px; color:#64748b; margin-top:2px;">${c.call_datetime || '-'} · Staff: ${this.escapeHtml(c.staff_name || 'Staff')}</div>
                      </div>
                      ${(c.has_recording && c.recording_id) ? `
                        <button class="play-audio-btn" data-recid="${c.recording_id}" style="background:#0284c7; color:#fff; border:none; border-radius:4px; padding:4px 10px; font-size:10px; font-weight:700; cursor:pointer;">
                          <i class="fas fa-play me-1"></i>Play
                        </button>
                      ` : '<span style="font-size:10px; color:#cbd5e1;">No Audio</span>'}
                    </div>
                  `).join('')}
                </div>
              `}
            ` : this.historyActiveTab === 'wa' ? `
              <!-- WhatsApp Messages Timeline -->
              ${this.historyWhatsApp.length === 0 ? `
                <div style="text-align:center; padding:24px; color:#94a3b8;">No WhatsApp interactions recorded.</div>
              ` : `
                <div style="display:flex; flex-direction:column; gap:8px;">
                  ${this.historyWhatsApp.map((m: any) => {
                    const isOut = m.direction === 'outbound';
                    return `
                      <div style="align-self:${isOut ? 'flex-end' : 'flex-start'}; background:${isOut ? '#dcf8c6' : '#fff'}; border:1px solid ${isOut ? '#bbf7d0' : '#e2e8f0'}; border-radius:8px; padding:8px 12px; max-width:85%; box-shadow:0 1px 2px rgba(0,0,0,0.05);">
                        <div style="font-size:9.5px; font-weight:700; color:#475569; margin-bottom:3px; display:flex; justify-content:space-between; gap:8px;">
                          <span>${this.escapeHtml(m.sender_name || (isOut ? 'Staff' : 'Customer'))}</span>
                          <span style="color:#94a3b8;">${m.sent_at || ''}</span>
                        </div>
                        <div style="font-size:11.5px; color:#1e293b; white-space:pre-wrap;">${this.escapeHtml(m.message_text || m.body || '')}</div>
                      </div>
                    `;
                  }).join('')}
                </div>
              `}
            ` : `
              <!-- Notes Timeline -->
              ${this.historyNotes.length === 0 ? `
                <div style="text-align:center; padding:24px; color:#94a3b8;">No internal notes recorded.</div>
              ` : `
                <div style="display:flex; flex-direction:column; gap:8px;">
                  ${this.historyNotes.map((n: any) => `
                    <div style="background:#fffbeb; border:1px solid #fde68a; border-radius:8px; padding:10px;">
                      <div style="font-size:10px; font-weight:700; color:#92400e; margin-bottom:3px; display:flex; justify-content:space-between;">
                        <span>${this.escapeHtml(n.author_name || 'Staff')}</span>
                        <span>${n.created_at || ''}</span>
                      </div>
                      <div style="font-size:11.5px; color:#78350f;">${this.escapeHtml(n.note_text || n.content || '')}</div>
                    </div>
                  `).join('')}
                </div>
              `}
            `}
          </div>

        </div>
      </div>
    `;
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     EVENT LISTENERS & BINDINGS
     ═══════════════════════════════════════════════════════════════════════════ */

  private attachEventListeners(): void {
    // Filter Drawer Toggle
    document.getElementById('crmFilterToggleBtn')?.addEventListener('click', () => {
      this.showFiltersDrawer = !this.showFiltersDrawer;
      this.render();
    });
    document.getElementById('crmCloseFiltersBtn')?.addEventListener('click', () => {
      this.showFiltersDrawer = false;
      this.render();
    });

    // Company change -> reload categories and sources
    document.getElementById('crmCompanySelect')?.addEventListener('change', (e) => {
      this.selectedCompanyId = (e.target as HTMLSelectElement).value;
      this.loadCategoriesAndSources().then(() => this.render());
    });

    // Apply & Reset Filters
    document.getElementById('crmApplyFiltersBtn')?.addEventListener('click', () => {
      this.filterStartDate = (document.getElementById('crmStartDate') as HTMLInputElement)?.value || '';
      this.filterEndDate = (document.getElementById('crmEndDate') as HTMLInputElement)?.value || '';
      this.filterStatus = (document.getElementById('crmStatusSelect') as HTMLSelectElement)?.value || '';
      this.filterDepartmentId = (document.getElementById('crmDeptSelect') as HTMLSelectElement)?.value || '';
      this.filterCategoryId = (document.getElementById('crmCategorySelect') as HTMLSelectElement)?.value || '';
      this.filterSource = (document.getElementById('crmSourceSelect') as HTMLSelectElement)?.value || '';
      this.showFiltersDrawer = false;
      this.loadDashboardData();
    });

    document.getElementById('crmResetFiltersBtn')?.addEventListener('click', () => {
      this.selectedCompanyId = '';
      this.filterStartDate = '';
      this.filterEndDate = '';
      this.filterStatus = '';
      this.filterDepartmentId = '';
      this.filterCategoryId = '';
      this.filterSource = '';
      this.showFiltersDrawer = false;
      this.loadDashboardData();
    });

    // Export CSV
    document.getElementById('crmExportCsvBtn')?.addEventListener('click', () => {
      this.exportActiveTabToCSV();
    });

    // Tab Switching
    this.container.querySelectorAll('.crm-tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = (e.currentTarget as HTMLElement).dataset.tab as any;
        if (tab) {
          this.activeTab = tab;
          this.render();

          if (tab === 'calls' && !this.ctData) {
            this.loadCallTrackingData();
          } else if (tab === 'quality' && !this.qaData) {
            this.loadQualityReport();
          } else if (tab === 'dialer' && !this.dialerData) {
            this.loadDialerData('today');
          } else if (tab === 'earnings' && !this.earnData) {
            this.loadEarningsData();
          }
        }
      });
    });

    // Team Multi-Select Toggle
    document.getElementById('toggleEmpSelectBtn')?.addEventListener('click', () => {
      this.showEmpSelectPanel = !this.showEmpSelectPanel;
      this.render();
    });

    document.getElementById('chipToggleAllEmps')?.addEventListener('click', () => {
      this.teamSelectedEmpIds = null;
      this.render();
    });

    this.container.querySelectorAll('.emp-chip-item').forEach(chip => {
      chip.addEventListener('click', (e) => {
        const empId = Number((e.currentTarget as HTMLElement).dataset.empid);
        const all = this.dashData?.team_performance?.employees || [];
        if (!this.teamSelectedEmpIds) {
          this.teamSelectedEmpIds = new Set(all.map((x: any) => x.emp_id));
        }
        if (this.teamSelectedEmpIds.has(empId)) {
          this.teamSelectedEmpIds.delete(empId);
        } else {
          this.teamSelectedEmpIds.add(empId);
        }
        if (this.teamSelectedEmpIds.size === all.length) {
          this.teamSelectedEmpIds = null;
        }
        this.render();
      });
    });

    // Interactive Count Click -> Open Drilldown
    this.container.querySelectorAll('.drill-click').forEach(el => {
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        const target = e.currentTarget as HTMLElement;
        const empId = target.dataset.empid || 'all';
        const empName = target.dataset.empname || 'All';
        const metricType = target.dataset.mtype || 'total';
        const metricVal = target.dataset.mval || '';
        const title = target.dataset.title || 'Leads Drilldown';
        let extra: Record<string, any> = {};
        try {
          extra = JSON.parse(target.dataset.extra || '{}');
        } catch (_) {}

        this.openCountDrilldown(empId, empName, metricType, metricVal, title, extra);
      });
    });

    // Call Tracking Sub-Tabs & Range
    this.container.querySelectorAll('.ct-range-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.ctCurrentRange = (e.currentTarget as HTMLElement).dataset.range as any;
        this.loadCallTrackingData();
      });
    });

    document.getElementById('ctStaffTabBtn')?.addEventListener('click', () => {
      this.ctSubTab = 'staff';
      this.render();
    });
    document.getElementById('ctSlotsTabBtn')?.addEventListener('click', () => {
      this.ctSubTab = 'slots';
      this.render();
    });
    document.getElementById('ctRefreshBtn')?.addEventListener('click', () => {
      this.loadCallTrackingData();
    });

    // View Staff Calls Click
    this.container.querySelectorAll('.view-staff-calls-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const target = e.currentTarget as HTMLElement;
        const staffId = Number(target.dataset.staffid);
        const staffName = target.dataset.staffname || 'Staff';
        this.loadStaffCalls(staffId, staffName);
      });
    });
    document.getElementById('closeStaffCallsBtn')?.addEventListener('click', () => {
      this.ctSelectedStaffId = null;
      this.render();
    });

    // Audio Play Buttons
    this.container.querySelectorAll('.play-audio-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const recId = Number((e.currentTarget as HTMLElement).dataset.recid);
        if (recId) this.playAudioStream(recId);
      });
    });
    document.getElementById('closeStaffCrmAudioBtn')?.addEventListener('click', () => {
      this.closeAudioPlayer();
    });

    // QA Mode & Submit
    document.getElementById('qaModeDayBtn')?.addEventListener('click', () => {
      this.qaMode = 'day';
      this.render();
    });
    document.getElementById('qaModeRangeBtn')?.addEventListener('click', () => {
      this.qaMode = 'range';
      this.render();
    });
    document.getElementById('qaSubmitBtn')?.addEventListener('click', () => {
      if (this.qaMode === 'day') {
        this.qaDate = (document.getElementById('qaDateInput') as HTMLInputElement)?.value || this.qaDate;
      } else {
        this.qaRangeFrom = (document.getElementById('qaRangeFromInput') as HTMLInputElement)?.value || this.qaRangeFrom;
        this.qaRangeTo = (document.getElementById('qaRangeToInput') as HTMLInputElement)?.value || this.qaRangeTo;
      }
      this.loadQualityReport();
    });

    // QA Row Expand
    this.container.querySelectorAll('.qa-expand-row').forEach(row => {
      row.addEventListener('click', (e) => {
        const idx = Number((e.currentTarget as HTMLElement).dataset.idx);
        this.expandedQaMap[idx] = !this.expandedQaMap[idx];
        this.render();
      });
    });

    // Dialer Period & Open Dialer
    this.container.querySelectorAll('.dialer-p-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const p = (e.currentTarget as HTMLElement).dataset.period as any;
        this.loadDialerData(p);
      });
    });
    document.getElementById('openDialerPageBtn')?.addEventListener('click', () => {
      routerService.navigate('auto-dialer');
    });

    // Earnings Calculate
    document.getElementById('earnCalculateBtn')?.addEventListener('click', () => {
      this.earnMonth = Number((document.getElementById('earnMonthSelect') as HTMLSelectElement)?.value || this.earnMonth);
      this.earnYear = Number((document.getElementById('earnYearSelect') as HTMLSelectElement)?.value || this.earnYear);
      this.earnCompanyId = (document.getElementById('earnCompanySelect') as HTMLSelectElement)?.value || '';
      this.loadEarningsData();
    });

    // Drilldown Modal Controls
    document.getElementById('closeDrilldownModalBtn')?.addEventListener('click', () => {
      this.showDrilldownModal = false;
      this.render();
    });

    document.getElementById('execDrilldownSearchBtn')?.addEventListener('click', () => {
      this.drilldownSearch = (document.getElementById('drilldownSearchInput') as HTMLInputElement)?.value.trim() || '';
      this.drilldownTelecallerId = (document.getElementById('drilldownTelecallerSelect') as HTMLSelectElement)?.value || '';
      this.drilldownCurrentPage = 1;
      this.fetchDrilldownLeads();
    });

    document.getElementById('drilldownPrevBtn')?.addEventListener('click', () => {
      if (this.drilldownCurrentPage > 1) {
        this.drilldownCurrentPage--;
        this.fetchDrilldownLeads();
      }
    });

    document.getElementById('drilldownNextBtn')?.addEventListener('click', () => {
      if (this.drilldownCurrentPage < this.drilldownTotalPages) {
        this.drilldownCurrentPage++;
        this.fetchDrilldownLeads();
      }
    });

    // Direct Lead Dial from Drilldown
    this.container.querySelectorAll('.lead-dial-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const target = e.currentTarget as HTMLElement;
        const phone = target.dataset.phone;
        const name = target.dataset.name;
        const leadId = target.dataset.leadid;
        if (phone) {
          callController.openCallDialer({
            phoneNumber: phone,
            name: name || 'Lead Contact',
            entityId: leadId ? Number(leadId) : undefined,
            entityType: 'lead',
            autoStart: true
          });
        }
      });
    });

    // Lead History Modal Open
    this.container.querySelectorAll('.lead-history-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const target = e.currentTarget as HTMLElement;
        const leadId = Number(target.dataset.leadid);
        const leadName = target.dataset.leadname || 'Lead';
        this.openLeadHistory(leadId, leadName);
      });
    });

    document.getElementById('closeHistoryModalBtn')?.addEventListener('click', () => {
      this.showHistoryModal = false;
      this.render();
    });

    this.container.querySelectorAll('.hist-tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.historyActiveTab = (e.currentTarget as HTMLElement).dataset.htab as any;
        this.render();
      });
    });
  }
}
