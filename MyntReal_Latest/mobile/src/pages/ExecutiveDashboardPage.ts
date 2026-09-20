/**
 * Executive Dashboard Page (Mobile View)
 * DC Protocol: DC_MOBILE_STAFF_EXEC_DASH_001
 * Comprehensive mobile interface for Executive Dashboard & Leadership Analytics
 * Full Parity with Web staff_executive_dashboard.html across all 4 platforms
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import { routerService } from '../services/router.service';

interface AnalyticsSummary {
  total_leads?: number;
  won_leads?: number;
  in_progress_leads?: number;
  lost_leads?: number;
  pipeline_leads?: number;
  total_deal_value?: number;
  won_deal_value?: number;
  pipeline_deal_value?: number;
  avg_deal_value?: number;
  total_collected?: number;
  total_pending?: number;
  loan_rejected_pending?: number;
}

interface BreakdownItem {
  name?: string;
  category?: string;
  source?: string;
  status?: string;
  emp_code?: string;
  count?: number;
  total?: number;
  won?: number;
  deal_value?: number;
  won_deal_value?: number;
  completed?: number;
  final_deal_value?: number;
  win_received?: number;
  completed_received?: number;
  win_rate?: number;
  _unassigned?: boolean;
  [key: string]: any;
}

interface TrendItem {
  period?: string;
  month?: string;
  week?: string;
  total?: number;
  won?: number;
  submitted?: number;
  submitted_val?: number;
  pipeline?: number;
  pipeline_val?: number;
  eb_change?: number;
  at_bank?: number;
  first_pmt_recd?: number;
  inst_pending?: number;
  net_meter_pending?: number;
  bal_pending?: number;
  subsidy_pending?: number;
  completed?: number;
  comp_value?: number;
  installed?: number;
  [key: string]: any;
}

interface EmpPerfRecord {
  period_key?: string;
  department_name?: string;
  emp_code?: string;
  employee_name?: string;
  self_leads?: number;
  overall_new_leads?: number;
  overdue_leads?: number;
  overall_won?: number;
  overall_rev?: number;
  solar_won?: number;
  solar_rev?: number;
  etc_won?: number;
  etc_rev?: number;
  b2b_won?: number;
  b2b_rev?: number;
  b2c_won?: number;
  b2c_rev?: number;
  insurance_won?: number;
  insurance_rev?: number;
  service_tickets_count?: number;
  service_rev?: number;
  spares_rev?: number;
  others_won?: number;
  others_rev?: number;
  attendance_days?: number;
  avg_talk_time_per_day?: string;
  calls_per_day?: string;
  [key: string]: any;
}

interface EtcStudentItem {
  id?: number;
  registration_id?: string;
  student_id?: string;
  name?: string;
  phone?: string;
  email?: string;
  state?: string;
  district?: string;
  course_type?: string;
  training_stage?: string;
  training_completed_date?: string;
  deal_value?: number;
  received?: number;
  balance?: number;
  confirmed?: boolean;
  confirmed_amount?: number;
  handler_name?: string;
  handler_emp_code?: string;
  telecaller_name?: string;
  telecaller_emp_code?: string;
  crm_lead_id?: number;
  source?: string;
  [key: string]: any;
}

interface EtcBatchItem {
  batch_no?: string;
  month?: string;
  start_date?: string;
  total_students?: number;
  completed?: number;
  deal_value?: number;
  received?: number;
  balance?: number;
  confirmed_count?: number;
  confirmed_value?: number;
  students?: EtcStudentItem[];
  [key: string]: any;
}

export class ExecutiveDashboardPage {
  private container: HTMLElement;
  private loading: boolean = true;
  private activePreset: 'today' | 'this_week' | 'last_week' | 'this_month' | 'last_month' | 'this_fy' | 'overall' = 'overall';
  private fromDate: string = '';
  private toDate: string = '';
  private selectedSegment: string = '';
  private activeTab: 'overview' | 'trends' | 'emp_perf' | 'etc_batchwise' | 'handlers' = 'overview';

  // Raw Lead Analytics data
  private summary: AnalyticsSummary = {};
  private byCategory: BreakdownItem[] = [];
  private byStatus: BreakdownItem[] = [];
  private bySource: BreakdownItem[] = [];
  private byTelecaller: BreakdownItem[] = [];
  private byFieldStaff: BreakdownItem[] = [];
  private monthlyTrend: TrendItem[] = [];
  private weeklyTrend: TrendItem[] = [];
  private rawLeadData: any = {};

  // Trends Tab state
  private activeTrendView: 'monthly' | 'weekly' = 'monthly';

  // Employee Performance Tab state
  private empPerfLoading: boolean = false;
  private empPerfData: { monthly?: EmpPerfRecord[]; weekly?: EmpPerfRecord[]; departments?: Array<{ id: number; name: string }> } | null = null;
  private empPerfActiveSection: 'monthly' | 'weekly' = 'monthly';
  private empPerfSearch: string = '';
  private empPerfDeptFilter: string = '';
  private expandedEmpMap: Record<string, boolean> = {};

  // ETC Batchwise Tab state
  private etcBatchLoading: boolean = false;
  private etcBatchData: { kpis?: Record<string, any>; batches?: EtcBatchItem[] } | null = null;
  private etcBatchSearch: string = '';
  private expandedBatchMap: Record<string, boolean> = {};

  // Handlers Tab state
  private handlerSearch: string = '';
  private activeHandlerType: 'ground' | 'handler' | 'support' | 'field' | 'guru' | 'zguru' | 'partner' | 'source' = 'ground';

  constructor(container: HTMLElement) {
    this.container = container;
    this.init();
  }

  private init(): void {
    this.loadData();
  }

  private fmtNum(n: number | undefined | null): string {
    return Number(n || 0).toLocaleString('en-IN');
  }

  private fmtVal(n: number | undefined | null): string {
    const val = parseFloat(String(n || 0));
    if (isNaN(val) || val === 0) return '₹0';
    if (val >= 10000000) return '₹' + (val / 10000000).toFixed(2) + ' Cr';
    if (val >= 100000) return '₹' + (val / 100000).toFixed(2) + ' L';
    if (val >= 1000) return '₹' + (val / 1000).toFixed(1) + ' K';
    return '₹' + val.toLocaleString('en-IN');
  }

  private fmtDateISO(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${dd}`;
  }

  private setPreset(preset: 'today' | 'this_week' | 'last_week' | 'this_month' | 'last_month' | 'this_fy' | 'overall'): void {
    this.activePreset = preset;
    const today = new Date();
    const todayStr = this.fmtDateISO(today);

    if (preset === 'overall') {
      this.fromDate = '';
      this.toDate = '';
    } else if (preset === 'today') {
      this.fromDate = todayStr;
      this.toDate = todayStr;
    } else if (preset === 'this_week') {
      const day = today.getDay();
      const diffToMon = today.getDate() - day + (day === 0 ? -6 : 1);
      const mon = new Date(today);
      mon.setDate(diffToMon);
      this.fromDate = this.fmtDateISO(mon);
      this.toDate = todayStr;
    } else if (preset === 'last_week') {
      const day = today.getDay();
      const diffToLastMon = today.getDate() - day + (day === 0 ? -6 : 1) - 7;
      const lastMon = new Date(today);
      lastMon.setDate(diffToLastMon);
      const lastSun = new Date(lastMon);
      lastSun.setDate(lastMon.getDate() + 6);
      this.fromDate = this.fmtDateISO(lastMon);
      this.toDate = this.fmtDateISO(lastSun);
    } else if (preset === 'this_month') {
      const s = new Date(today.getFullYear(), today.getMonth(), 1);
      this.fromDate = this.fmtDateISO(s);
      this.toDate = todayStr;
    } else if (preset === 'last_month') {
      const s = new Date(today.getFullYear(), today.getMonth() - 1, 1);
      const e = new Date(today.getFullYear(), today.getMonth(), 0);
      this.fromDate = this.fmtDateISO(s);
      this.toDate = this.fmtDateISO(e);
    } else if (preset === 'this_fy') {
      const curYear = today.getFullYear();
      const fyStartYear = today.getMonth() >= 3 ? curYear : curYear - 1;
      this.fromDate = `${fyStartYear}-04-01`;
      this.toDate = todayStr;
    }
    this.loadData();
    if (this.activeTab === 'emp_perf') {
      this.loadEmployeePerformance();
    }
  }

  private async loadData(): Promise<void> {
    this.loading = true;
    this.render();

    try {
      const p = new URLSearchParams();
      if (this.fromDate) p.set('created_from', this.fromDate);
      if (this.toDate) p.set('created_to', this.toDate);
      if (this.selectedSegment) p.set('category', this.selectedSegment);

      const resp = await apiService.get<any>(`/crm/lead-analytics?${p.toString()}`);
      if (resp && (resp.success !== false)) {
        const d = resp.data || resp;
        this.rawLeadData = d;
        this.summary = d.summary || {};
        this.byCategory = d.by_category || [];
        this.byStatus = d.by_status || [];
        this.bySource = d.by_source || [];
        this.byTelecaller = d.by_telecaller || [];
        this.byFieldStaff = d.by_field_staff || [];
        this.monthlyTrend = (d.monthly_trend || []).slice().reverse();
        this.weeklyTrend = (d.weekly_trend || []).slice().reverse();
      }
    } catch (e) {
      console.error('[ExecutiveDashboardPage] Failed to load lead analytics:', e);
    } finally {
      this.loading = false;
      this.render();
    }
  }

  private async loadEmployeePerformance(): Promise<void> {
    this.empPerfLoading = true;
    this.render();

    try {
      const p = new URLSearchParams();
      if (this.empPerfSearch) p.set('search', this.empPerfSearch);
      if (this.empPerfDeptFilter) p.set('department_id', this.empPerfDeptFilter);
      if (this.fromDate) p.set('created_from', this.fromDate);
      if (this.toDate) p.set('created_to', this.toDate);

      const resp = await apiService.get<any>(`/crm/employee-performance-dashboard?${p.toString()}`);
      if (resp && (resp.success !== false)) {
        this.empPerfData = resp.data || resp;
      }
    } catch (e) {
      console.error('[ExecutiveDashboardPage] Failed to load employee performance:', e);
    } finally {
      this.empPerfLoading = false;
      this.render();
    }
  }

  private async loadEtcBatchwise(): Promise<void> {
    this.etcBatchLoading = true;
    this.render();

    try {
      const p = new URLSearchParams();
      if (this.etcBatchSearch) p.set('search', this.etcBatchSearch);

      const resp = await apiService.get<any>(`/etc/students/batchwise-analytics?${p.toString()}`);
      if (resp && (resp.success !== false)) {
        this.etcBatchData = resp.data || resp;
      }
    } catch (e) {
      console.error('[ExecutiveDashboardPage] Failed to load etc batchwise analytics:', e);
    } finally {
      this.etcBatchLoading = false;
      this.render();
    }
  }

  private switchTab(tab: 'overview' | 'trends' | 'emp_perf' | 'etc_batchwise' | 'handlers'): void {
    this.activeTab = tab;
    if (tab === 'emp_perf' && !this.empPerfData && !this.empPerfLoading) {
      this.loadEmployeePerformance();
    } else if (tab === 'etc_batchwise' && !this.etcBatchData && !this.etcBatchLoading) {
      this.loadEtcBatchwise();
    } else {
      this.render();
    }
  }

  private render(): void {
    const total = this.summary.total_leads || 0;
    const won = this.summary.won_leads || 0;
    const inProg = this.summary.in_progress_leads || 0;
    const lost = this.summary.lost_leads || 0;
    const pipeline = this.summary.pipeline_leads || 0;
    const totalVal = this.summary.total_deal_value || 0;
    const wonVal = this.summary.won_deal_value || 0;
    const avgVal = this.summary.avg_deal_value || 0;
    const collected = this.summary.total_collected || 0;
    const pendingBal = this.summary.total_pending || 0;
    const loanRej = this.summary.loan_rejected_pending || 0;
    const winRate = total > 0 ? ((won / total) * 100).toFixed(1) : '0';

    this.container.innerHTML = `
      <div class="executive-dashboard-container" style="background:#0b1329; min-height:100vh; padding-bottom:80px; color:#f1f5f9; font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;">
        ${PageHeader.render({
          title: 'Executive Dashboard',
          subtitle: 'Live Analytics · Solar, EV, RD, Insurance, ETC',
          showMenu: true,
          showBack: true
        })}

        <div style="padding:14px;">
          <!-- Quick Timeframe Presets (Complete parity with Web) -->
          <div style="display:flex; gap:6px; overflow-x:auto; padding-bottom:6px; margin-bottom:12px; -webkit-overflow-scrolling:touch;">
            <button class="preset-btn ${this.activePreset === 'overall' ? 'active' : ''}" data-preset="overall" style="${this.getPresetStyle(this.activePreset === 'overall')}">Overall (All)</button>
            <button class="preset-btn ${this.activePreset === 'today' ? 'active' : ''}" data-preset="today" style="${this.getPresetStyle(this.activePreset === 'today')}">Today</button>
            <button class="preset-btn ${this.activePreset === 'this_week' ? 'active' : ''}" data-preset="this_week" style="${this.getPresetStyle(this.activePreset === 'this_week')}">This Week</button>
            <button class="preset-btn ${this.activePreset === 'last_week' ? 'active' : ''}" data-preset="last_week" style="${this.getPresetStyle(this.activePreset === 'last_week')}">Last Week</button>
            <button class="preset-btn ${this.activePreset === 'this_month' ? 'active' : ''}" data-preset="this_month" style="${this.getPresetStyle(this.activePreset === 'this_month')}">This Month</button>
            <button class="preset-btn ${this.activePreset === 'last_month' ? 'active' : ''}" data-preset="last_month" style="${this.getPresetStyle(this.activePreset === 'last_month')}">Last Month</button>
            <button class="preset-btn ${this.activePreset === 'this_fy' ? 'active' : ''}" data-preset="this_fy" style="${this.getPresetStyle(this.activePreset === 'this_fy')}">This FY</button>
          </div>

          <!-- Date Range & Segment Filter Collapsible -->
          <div style="background:#1e293b; border:1px solid #334155; border-radius:10px; padding:12px; margin-bottom:14px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
              <span style="font-size:11px; font-weight:700; color:#94a3b8; text-transform:uppercase; letter-spacing:0.5px;">Custom Filter &amp; Range</span>
              <div style="display:flex; gap:8px;">
                <button id="execResetBtn" style="background:transparent; border:none; color:#94a3b8; font-size:12px; cursor:pointer; font-weight:600;">
                  Reset
                </button>
                <button id="execRefreshBtn" style="background:transparent; border:none; color:#38bdf8; font-size:12px; cursor:pointer; font-weight:600; display:flex; align-items:center; gap:4px;">
                  <i class="fas fa-sync-alt ${this.loading ? 'fa-spin' : ''}"></i> Refresh
                </button>
              </div>
            </div>

            <!-- Segment Selector -->
            <div style="margin-bottom:8px;">
              <select id="execCategoryFilter" style="width:100%; background:#0f172a; border:1px solid #334155; color:#f1f5f9; border-radius:6px; padding:6px 8px; font-size:12px;">
                <option value="" ${this.selectedSegment === '' ? 'selected' : ''}>All Segments / Verticals</option>
                <option value="Solar" ${this.selectedSegment === 'Solar' ? 'selected' : ''}>☀️ Solar</option>
                <option value="EV B2B" ${this.selectedSegment === 'EV B2B' ? 'selected' : ''}>⚡ EV B2B (Fleet/Franchise)</option>
                <option value="EV B2C" ${this.selectedSegment === 'EV B2C' ? 'selected' : ''}>🛵 EV B2C (2-Wheelers)</option>
                <option value="EV Spares" ${this.selectedSegment === 'EV Spares' ? 'selected' : ''}>🔧 EV Spares &amp; Batteries</option>
                <option value="Real Dreams" ${this.selectedSegment === 'Real Dreams' ? 'selected' : ''}>🏡 Real Dreams (Plots/Villas)</option>
                <option value="Insurance" ${this.selectedSegment === 'Insurance' ? 'selected' : ''}>🛡️ Insurance</option>
                <option value="ETC Training" ${this.selectedSegment === 'ETC Training' ? 'selected' : ''}>🎓 ETC Training</option>
              </select>
            </div>

            <div style="display:flex; gap:8px; align-items:center;">
              <div style="flex:1;">
                <input type="date" id="execFromDate" value="${this.fromDate}" style="width:100%; background:#0f172a; border:1px solid #334155; color:#f1f5f9; border-radius:6px; padding:6px 8px; font-size:12px;">
              </div>
              <span style="color:#64748b; font-size:12px;">to</span>
              <div style="flex:1;">
                <input type="date" id="execToDate" value="${this.toDate}" style="width:100%; background:#0f172a; border:1px solid #334155; color:#f1f5f9; border-radius:6px; padding:6px 8px; font-size:12px;">
              </div>
              <button id="execApplyDateBtn" style="background:#2563eb; color:white; border:none; border-radius:6px; padding:7px 12px; font-size:12px; font-weight:600; cursor:pointer;">
                Apply
              </button>
            </div>
          </div>

          <!-- 11 Top KPI Cards (Web Parity) -->
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:8px;">
            <!-- Total Leads -->
            <div style="background:linear-gradient(135deg, #1e293b, #111827); border:1px solid #334155; border-radius:10px; padding:10px 12px;">
              <div style="font-size:10px; font-weight:700; color:#94a3b8; text-transform:uppercase;">Total Leads</div>
              <div style="font-size:22px; font-weight:800; color:#ffffff;">${this.fmtNum(total)}</div>
              <div style="font-size:10px; color:#38bdf8;">All verticals</div>
            </div>

            <!-- Won Deals -->
            <div style="background:linear-gradient(135deg, #064e3b, #022c22); border:1px solid #059669; border-radius:10px; padding:10px 12px;">
              <div style="font-size:10px; font-weight:700; color:#6ee7b7; text-transform:uppercase;">Won Deals</div>
              <div style="font-size:22px; font-weight:800; color:#34d399;">${this.fmtNum(won)}</div>
              <div style="font-size:10px; color:#a7f3d0;">${winRate}% Win Rate</div>
            </div>

            <!-- Pipeline Deals -->
            <div style="background:linear-gradient(135deg, #1e1b4b, #0f172a); border:1px solid #2563eb; border-radius:10px; padding:10px 12px;">
              <div style="font-size:10px; font-weight:700; color:#93c5fd; text-transform:uppercase;">Pipeline</div>
              <div style="font-size:18px; font-weight:800; color:#60a5fa;">${this.fmtNum(pipeline)}</div>
              <div style="font-size:10px; color:#93c5fd;">Active prospects</div>
            </div>

            <!-- Won Deal Revenue -->
            <div style="background:linear-gradient(135deg, #14532d, #052e16); border:1px solid #16a34a; border-radius:10px; padding:10px 12px;">
              <div style="font-size:10px; font-weight:700; color:#86efac; text-transform:uppercase;">Won Value</div>
              <div style="font-size:18px; font-weight:800; color:#4ade80;">${this.fmtVal(wonVal)}</div>
              <div style="font-size:10px; color:#bbf7d0;">Closed revenue</div>
            </div>
          </div>

          <!-- Secondary KPI 4-grid -->
          <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:6px; margin-bottom:8px;">
            <div style="background:#1e293b; border:1px solid #334155; border-radius:8px; padding:8px 4px; text-align:center;">
              <div style="font-size:9px; color:#fbbf24; font-weight:700;">IN PROGRESS</div>
              <div style="font-size:14px; font-weight:800; color:#fef08a; margin-top:2px;">${this.fmtNum(inProg)}</div>
            </div>
            <div style="background:#1e293b; border:1px solid #334155; border-radius:8px; padding:8px 4px; text-align:center;">
              <div style="font-size:9px; color:#f87171; font-weight:700;">LOST</div>
              <div style="font-size:14px; font-weight:800; color:#fca5a5; margin-top:2px;">${this.fmtNum(lost)}</div>
            </div>
            <div style="background:#1e293b; border:1px solid #334155; border-radius:8px; padding:8px 4px; text-align:center;">
              <div style="font-size:9px; color:#818cf8; font-weight:700;">TOTAL VAL</div>
              <div style="font-size:12px; font-weight:800; color:#c7d2fe; margin-top:2px;">${this.fmtVal(totalVal)}</div>
            </div>
            <div style="background:#1e293b; border:1px solid #334155; border-radius:8px; padding:8px 4px; text-align:center;">
              <div style="font-size:9px; color:#38bdf8; font-weight:700;">AVG VAL</div>
              <div style="font-size:12px; font-weight:800; color:#7dd3fc; margin-top:2px;">${this.fmtVal(avgVal)}</div>
            </div>
          </div>

          <!-- Financial Collections & Balance KPI Row -->
          <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:6px; margin-bottom:14px;">
            <div style="background:#1e293b; border-left:3px solid #059669; border-radius:8px; padding:8px; text-align:center;">
              <div style="font-size:9px; color:#34d399; font-weight:700;">COLLECTED</div>
              <div style="font-size:13px; font-weight:800; color:#a7f3d0; margin-top:2px;">${this.fmtVal(collected)}</div>
            </div>
            <div style="background:#1e293b; border-left:3px solid #dc2626; border-radius:8px; padding:8px; text-align:center;">
              <div style="font-size:9px; color:#f87171; font-weight:700;">PENDING BAL</div>
              <div style="font-size:13px; font-weight:800; color:#fca5a5; margin-top:2px;">${this.fmtVal(pendingBal)}</div>
            </div>
            <div style="background:#1e293b; border-left:3px solid #9d174d; border-radius:8px; padding:8px; text-align:center;">
              <div style="font-size:9px; color:#f472b6; font-weight:700;">LOAN REJ ₹</div>
              <div style="font-size:13px; font-weight:800; color:#fbcfe8; margin-top:2px;">${this.fmtVal(loanRej)}</div>
            </div>
          </div>

          <!-- All 5 Authentic Tabs Bar (Full Parity with Web) -->
          <div style="display:flex; gap:4px; overflow-x:auto; padding:4px; background:#0f172a; border:1px solid #334155; border-radius:10px; margin-bottom:14px; -webkit-overflow-scrolling:touch;">
            <button class="nav-tab-btn ${this.activeTab === 'overview' ? 'active' : ''}" data-tab="overview" style="${this.getNavTabStyle(this.activeTab === 'overview')}">
              <i class="fas fa-chart-bar" style="margin-right:4px;"></i>Overview
            </button>
            <button class="nav-tab-btn ${this.activeTab === 'trends' ? 'active' : ''}" data-tab="trends" style="${this.getNavTabStyle(this.activeTab === 'trends')}">
              <i class="fas fa-chart-line" style="margin-right:4px;"></i>Trends
            </button>
            <button class="nav-tab-btn ${this.activeTab === 'emp_perf' ? 'active' : ''}" data-tab="emp_perf" style="${this.getNavTabStyle(this.activeTab === 'emp_perf')}">
              <i class="fas fa-users-cog" style="margin-right:4px;"></i>Employee Perf
            </button>
            <button class="nav-tab-btn ${this.activeTab === 'etc_batchwise' ? 'active' : ''}" data-tab="etc_batchwise" style="${this.getNavTabStyle(this.activeTab === 'etc_batchwise')}">
              <i class="fas fa-graduation-cap" style="margin-right:4px;"></i>ETC Batches
            </button>
            <button class="nav-tab-btn ${this.activeTab === 'handlers' ? 'active' : ''}" data-tab="handlers" style="${this.getNavTabStyle(this.activeTab === 'handlers')}">
              <i class="fas fa-users" style="margin-right:4px;"></i>Handlers
            </button>
          </div>

          ${this.loading ? `
            <div style="text-align:center; padding:48px 16px;">
              <i class="fas fa-circle-notch fa-spin" style="font-size:28px; color:#38bdf8; margin-bottom:12px;"></i>
              <div style="color:#94a3b8; font-size:13px; font-weight:500;">Loading leadership metrics...</div>
            </div>
          ` : `
            <!-- Tab Content -->
            ${this.activeTab === 'overview' ? this.renderOverviewTab(total) : ''}
            ${this.activeTab === 'trends' ? this.renderTrendsTab() : ''}
            ${this.activeTab === 'emp_perf' ? this.renderEmpPerfTab() : ''}
            ${this.activeTab === 'etc_batchwise' ? this.renderEtcBatchwiseTab() : ''}
            ${this.activeTab === 'handlers' ? this.renderHandlersTab() : ''}
          `}
        </div>
      </div>
    `;

    PageHeader.attachListeners({
      title: 'Executive Dashboard',
      showMenu: true,
      showBack: true
    });

    this.attachEventListeners();
  }

  private getPresetStyle(active: boolean): string {
    if (active) {
      return 'background:#2563eb; color:white; border:none; border-radius:20px; padding:6px 14px; font-size:11px; font-weight:700; white-space:nowrap; cursor:pointer; box-shadow:0 2px 8px rgba(37,99,235,0.4);';
    }
    return 'background:#1e293b; color:#94a3b8; border:1px solid #334155; border-radius:20px; padding:6px 14px; font-size:11px; font-weight:600; white-space:nowrap; cursor:pointer;';
  }

  private getNavTabStyle(active: boolean): string {
    if (active) {
      return 'white-space:nowrap; background:#1e293b; color:#38bdf8; border:none; border-radius:7px; padding:7px 12px; font-size:11px; font-weight:700; cursor:pointer; box-shadow:0 1px 4px rgba(0,0,0,0.2);';
    }
    return 'white-space:nowrap; background:transparent; color:#94a3b8; border:none; padding:7px 12px; font-size:11px; font-weight:600; cursor:pointer;';
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     TAB 1: OVERVIEW (5 Breakdowns matching Web)
     ═══════════════════════════════════════════════════════════════════════════ */
  private renderOverviewTab(total: number): string {
    return `
      <!-- 1. By Status Breakdown -->
      <div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:14px; margin-bottom:14px;">
        <div style="font-size:13px; font-weight:700; color:#ffffff; margin-bottom:12px; display:flex; align-items:center; gap:6px;">
          <i class="fas fa-chart-pie" style="color:#38bdf8;"></i> By Status (${this.byStatus.length})
        </div>
        ${this.byStatus.length === 0 ? `
          <div style="text-align:center; color:#64748b; padding:16px; font-size:12px;">No status data available</div>
        ` : this.byStatus.map(st => {
          const count = st.count || st.total || 0;
          const pct = total > 0 ? ((count / total) * 100).toFixed(1) : '0';
          const name = (st.status || st.name || 'Unknown').replace(/_/g, ' ').toUpperCase();
          const color = name.includes('WON') ? '#10b981' : name.includes('LOST') ? '#ef4444' : name.includes('PROGRESS') || name.includes('CONTACT') ? '#f59e0b' : '#38bdf8';
          return `
            <div style="margin-bottom:10px;">
              <div style="display:flex; justify-content:space-between; font-size:11.5px; margin-bottom:4px;">
                <span style="font-weight:600; color:#e2e8f0;">${name}</span>
                <span style="font-weight:700; color:#94a3b8;">${this.fmtNum(count)} <span style="font-size:10px; font-weight:400; color:#64748b;">(${pct}%)</span></span>
              </div>
              <div style="background:#0f172a; border-radius:4px; height:6px; overflow:hidden;">
                <div style="width:${pct}%; background:${color}; height:100%; border-radius:4px;"></div>
              </div>
            </div>
          `;
        }).join('')}
      </div>

      <!-- 2. By Segment (Verticals) Breakdown -->
      <div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:14px; margin-bottom:14px;">
        <div style="font-size:13px; font-weight:700; color:#ffffff; margin-bottom:12px; display:flex; align-items:center; gap:6px;">
          <i class="fas fa-layer-group" style="color:#f59e0b;"></i> By Segment (${this.byCategory.length})
        </div>
        <div style="display:flex; flex-direction:column; gap:8px;">
          ${this.byCategory.length === 0 ? `
            <div style="text-align:center; color:#64748b; padding:16px; font-size:12px;">No category distribution found</div>
          ` : this.byCategory.map(cat => {
            const name = cat.category || cat.name || 'General';
            const cnt = cat.count || cat.total || 0;
            const won = cat.won || 0;
            const val = cat.deal_value || cat.won_deal_value || 0;
            const pct = total > 0 ? ((cnt / total) * 100).toFixed(1) : '0';

            return `
              <div class="cat-card" data-cat="${name.toLowerCase().replace(/[^a-z0-9]/g, '-')}" style="background:#0f172a; border:1px solid #334155; border-radius:8px; padding:10px 12px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                  <div style="font-size:12px; font-weight:700; color:#ffffff;">${name}</div>
                  <div style="font-size:11px; font-weight:600; color:#38bdf8;">${this.fmtNum(cnt)} leads (${pct}%)</div>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:6px;">
                  <span style="color:#34d399; font-weight:600;">Won: ${this.fmtNum(won)}</span>
                  <span style="color:#818cf8; font-weight:600;">Value: ${this.fmtVal(val)}</span>
                </div>
                <div style="background:#1e293b; border-radius:3px; height:5px; overflow:hidden;">
                  <div style="width:${pct}%; background:#38bdf8; height:100%; border-radius:3px;"></div>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      </div>

      <!-- 3. By Source Breakdown -->
      ${this.bySource.length > 0 ? `
        <div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:14px; margin-bottom:14px;">
          <div style="font-size:13px; font-weight:700; color:#ffffff; margin-bottom:12px; display:flex; align-items:center; gap:6px;">
            <i class="fas fa-share-alt" style="color:#a855f7;"></i> By Source (${this.bySource.length})
          </div>
          ${this.bySource.slice(0, 10).map(src => {
            const count = src.count || src.total || 0;
            const won = src.won || 0;
            const pct = total > 0 ? ((count / total) * 100).toFixed(1) : '0';
            const name = (src.source || src.name || 'Other').toUpperCase();
            return `
              <div style="margin-bottom:8px;">
                <div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:3px;">
                  <span style="font-weight:600; color:#cbd5e1;">${name}</span>
                  <span style="font-weight:700; color:#94a3b8;">${this.fmtNum(count)} <span style="color:#34d399;">(${won} won)</span></span>
                </div>
                <div style="background:#0f172a; border-radius:3px; height:5px; overflow:hidden;">
                  <div style="width:${pct}%; background:#a855f7; height:100%; border-radius:3px;"></div>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      ` : ''}

      <!-- 4. By Support Staff (Telecaller) Breakdown (Web Parity) -->
      ${this.byTelecaller.length > 0 ? `
        <div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:14px; margin-bottom:14px;">
          <div style="font-size:13px; font-weight:700; color:#ffffff; margin-bottom:12px; display:flex; align-items:center; gap:6px;">
            <i class="fas fa-headset" style="color:#38bdf8;"></i> By Support Staff (${this.byTelecaller.length})
          </div>
          <div style="display:flex; flex-direction:column; gap:6px;">
            ${this.byTelecaller.slice(0, 15).map(tc => {
              const name = tc.name || 'Support Staff';
              const cnt = tc.total || tc.count || 0;
              const won = tc.won || 0;
              const winPct = cnt > 0 ? ((won / cnt) * 100).toFixed(0) : '0';
              const val = tc.deal_value || 0;

              return `
                <div style="background:#0f172a; border:1px solid #334155; border-radius:8px; padding:8px 10px; display:flex; justify-content:space-between; align-items:center;">
                  <div>
                    <div style="font-size:11.5px; font-weight:600; color:#f1f5f9;">${name}</div>
                    <div style="font-size:10px; color:#64748b;">${cnt} leads assigned</div>
                  </div>
                  <div style="text-align:right;">
                    <div style="font-size:11.5px; font-weight:700; color:#34d399;">${won} Won (${winPct}%)</div>
                    <div style="font-size:10px; color:#818cf8;">${this.fmtVal(val)}</div>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      ` : ''}

      <!-- 5. By Field Staff (Showroom) Breakdown (Web Parity) -->
      ${this.byFieldStaff.length > 0 ? `
        <div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:14px; margin-bottom:14px;">
          <div style="font-size:13px; font-weight:700; color:#ffffff; margin-bottom:12px; display:flex; align-items:center; gap:6px;">
            <i class="fas fa-user-tie" style="color:#ec4899;"></i> By Field Staff (Showroom) (${this.byFieldStaff.length})
          </div>
          <div style="display:flex; flex-direction:column; gap:6px;">
            ${this.byFieldStaff.slice(0, 15).map(fs => {
              const name = fs.name || 'Field Staff';
              const cnt = fs.total || fs.count || 0;
              const won = fs.won || 0;
              const winPct = cnt > 0 ? ((won / cnt) * 100).toFixed(0) : '0';
              const val = fs.deal_value || 0;

              return `
                <div style="background:#0f172a; border:1px solid #334155; border-radius:8px; padding:8px 10px; display:flex; justify-content:space-between; align-items:center;">
                  <div>
                    <div style="font-size:11.5px; font-weight:600; color:#f1f5f9;">${name}</div>
                    <div style="font-size:10px; color:#64748b;">${cnt} leads assigned</div>
                  </div>
                  <div style="text-align:right;">
                    <div style="font-size:11.5px; font-weight:700; color:#34d399;">${won} Won (${winPct}%)</div>
                    <div style="font-size:10px; color:#818cf8;">${this.fmtVal(val)}</div>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      ` : ''}

      <!-- Quick Shortcuts to Workflows -->
      <div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:14px; margin-bottom:14px;">
        <div style="font-size:13px; font-weight:700; color:#ffffff; margin-bottom:10px; display:flex; align-items:center; gap:6px;">
          <i class="fas fa-bolt" style="color:#f59e0b;"></i> Workflows &amp; Category Masters
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
          <button class="workflow-nav-card" data-route="staff-bank-wise-leads" style="background:#0f172a; border:1px solid #334155; border-radius:8px; padding:10px; text-align:left; color:#f1f5f9; cursor:pointer;">
            <div style="font-size:11px; font-weight:700; color:#38bdf8;"><i class="fas fa-users-gear"></i> Field Sales</div>
            <div style="font-size:10px; color:#64748b; margin-top:2px;">Bank pipeline tracking</div>
          </button>
          <button class="workflow-nav-card" data-route="category-leads-master" data-tab="solar" style="background:#0f172a; border:1px solid #334155; border-radius:8px; padding:10px; text-align:left; color:#f1f5f9; cursor:pointer;">
            <div style="font-size:11px; font-weight:700; color:#f59e0b;"><i class="fas fa-solar-panel"></i> Solar Leads</div>
            <div style="font-size:10px; color:#64748b; margin-top:2px;">Master Solar pipeline</div>
          </button>
          <button class="workflow-nav-card" data-route="category-leads-master" data-tab="ev-b2b" style="background:#0f172a; border:1px solid #334155; border-radius:8px; padding:10px; text-align:left; color:#f1f5f9; cursor:pointer;">
            <div style="font-size:11px; font-weight:700; color:#3b82f6;"><i class="fas fa-truck"></i> EV B2B Leads</div>
            <div style="font-size:10px; color:#64748b; margin-top:2px;">Franchise &amp; Dealerships</div>
          </button>
          <button class="workflow-nav-card" data-route="category-leads-master" data-tab="real-dreams" style="background:#0f172a; border:1px solid #334155; border-radius:8px; padding:10px; text-align:left; color:#f1f5f9; cursor:pointer;">
            <div style="font-size:11px; font-weight:700; color:#ef4444;"><i class="fas fa-home"></i> Real Dreams</div>
            <div style="font-size:10px; color:#64748b; margin-top:2px;">Plots &amp; Real Estate</div>
          </button>
        </div>
      </div>
    `;
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     TAB 2: MONTHLY & WEEKLY TRENDS (Web Parity)
     ═══════════════════════════════════════════════════════════════════════════ */
  private renderTrendsTab(): string {
    const list = this.activeTrendView === 'monthly' ? this.monthlyTrend : this.weeklyTrend;
    const title = this.activeTrendView === 'monthly' ? 'Monthly Trend — Last 12 Months' : 'Weekly Trend — Last 12 Weeks';

    return `
      <div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:14px; margin-bottom:14px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
          <div>
            <div style="font-size:13px; font-weight:700; color:#ffffff; display:flex; align-items:center; gap:6px;">
              <i class="fas fa-chart-line" style="color:#38bdf8;"></i> ${title}
            </div>
            <div style="font-size:10px; color:#64748b; margin-top:2px;">Stage velocity &amp; conversion pipeline</div>
          </div>
          <div style="display:flex; background:#0f172a; border:1px solid #334155; border-radius:6px; padding:2px;">
            <button id="trendMonthlyBtn" style="background:${this.activeTrendView === 'monthly' ? '#2563eb' : 'transparent'}; color:${this.activeTrendView === 'monthly' ? 'white' : '#94a3b8'}; border:none; border-radius:4px; padding:4px 8px; font-size:10px; font-weight:700; cursor:pointer;">
              Monthly
            </button>
            <button id="trendWeeklyBtn" style="background:${this.activeTrendView === 'weekly' ? '#2563eb' : 'transparent'}; color:${this.activeTrendView === 'weekly' ? 'white' : '#94a3b8'}; border:none; border-radius:4px; padding:4px 8px; font-size:10px; font-weight:700; cursor:pointer;">
              Weekly
            </button>
          </div>
        </div>

        ${list.length === 0 ? `
          <div style="text-align:center; color:#64748b; padding:24px; font-size:12px;">No trend data available</div>
        ` : `
          <!-- Trend Cards List -->
          <div style="display:flex; flex-direction:column; gap:10px;">
            ${list.map(t => {
              const period = t.period || t.month || t.week || 'Period';
              const tot = t.total || 0;
              const won = t.won || 0;
              const sub = t.submitted || 0;
              const subVal = t.submitted_val || 0;
              const pipe = t.pipeline || 0;
              const pipeVal = t.pipeline_val || 0;
              const comp = t.completed || 0;
              const compVal = t.comp_value || 0;
              const subWonPct = won > 0 ? ((sub / won) * 100).toFixed(0) : '0';

              return `
                <div style="background:#0f172a; border:1px solid #334155; border-radius:10px; padding:12px;">
                  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; border-bottom:1px solid #1e293b; padding-bottom:6px;">
                    <div style="font-size:13px; font-weight:700; color:#38bdf8;">${period}</div>
                    <div style="font-size:11px; font-weight:600; color:#94a3b8;">${this.fmtNum(tot)} Total Leads</div>
                  </div>

                  <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:6px; margin-bottom:8px;">
                    <!-- Won & Submitted -->
                    <div style="background:#1e293b; border-left:3px solid #10b981; border-radius:6px; padding:6px 8px;">
                      <div style="font-size:9px; color:#6ee7b7; font-weight:700;">WON / SUB</div>
                      <div style="font-size:13px; font-weight:800; color:#34d399; margin-top:2px;">${won} <span style="font-size:10px; color:#a7f3d0;">/ ${sub}</span></div>
                      <div style="font-size:9.5px; color:#6ee7b7;">${this.fmtVal(subVal)} (${subWonPct}%)</div>
                    </div>

                    <!-- Pipeline -->
                    <div style="background:#1e293b; border-left:3px solid #3b82f6; border-radius:6px; padding:6px 8px;">
                      <div style="font-size:9px; color:#93c5fd; font-weight:700;">PIPELINE</div>
                      <div style="font-size:13px; font-weight:800; color:#60a5fa; margin-top:2px;">${pipe}</div>
                      <div style="font-size:9.5px; color:#93c5fd;">${this.fmtVal(pipeVal)}</div>
                    </div>

                    <!-- Completed -->
                    <div style="background:#1e293b; border-left:3px solid #0d9488; border-radius:6px; padding:6px 8px;">
                      <div style="font-size:9px; color:#5eead4; font-weight:700;">COMPLETED</div>
                      <div style="font-size:13px; font-weight:800; color:#2dd4bf; margin-top:2px;">${comp}</div>
                      <div style="font-size:9.5px; color:#5eead4;">${this.fmtVal(compVal)}</div>
                    </div>
                  </div>

                  <!-- Milestones -->
                  <div style="display:flex; flex-wrap:wrap; gap:4px; font-size:9.5px; color:#94a3b8;">
                    <span style="background:#1e293b; padding:2px 6px; border-radius:4px;">1st Pmt: <strong style="color:#e2e8f0;">${t.first_pmt_recd || 0}</strong></span>
                    <span style="background:#1e293b; padding:2px 6px; border-radius:4px;">Install Pend: <strong style="color:#e2e8f0;">${t.inst_pending || 0}</strong></span>
                    <span style="background:#1e293b; padding:2px 6px; border-radius:4px;">Net Meter: <strong style="color:#e2e8f0;">${t.net_meter_pending || 0}</strong></span>
                    <span style="background:#1e293b; padding:2px 6px; border-radius:4px;">At Bank: <strong style="color:#e2e8f0;">${t.at_bank || 0}</strong></span>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        `}
      </div>
    `;
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     TAB 3: EMPLOYEE WISE PERFORMANCE DASHBOARD (Web Parity)
     ═══════════════════════════════════════════════════════════════════════════ */
  private renderEmpPerfTab(): string {
    if (this.empPerfLoading) {
      return `
        <div style="text-align:center; padding:48px 16px;">
          <i class="fas fa-circle-notch fa-spin" style="font-size:28px; color:#38bdf8; margin-bottom:12px;"></i>
          <div style="color:#94a3b8; font-size:13px; font-weight:500;">Loading Employee Performance...</div>
        </div>
      `;
    }

    const data = this.empPerfData || {};
    const departments = data.departments || [];
    const rawRows = (this.empPerfActiveSection === 'monthly' ? data.monthly : data.weekly) || [];

    // Filter out FL (freelancers) and apply local search & dept filter
    const searchVal = this.empPerfSearch.toLowerCase().trim();
    const deptVal = this.empPerfDeptFilter;

    let filteredRows = rawRows.filter(r => {
      const code = (r.emp_code || '').toUpperCase();
      if (code.startsWith('FL')) return false;
      if (searchVal) {
        const matchName = (r.employee_name || '').toLowerCase().includes(searchVal);
        const matchCode = (r.emp_code || '').toLowerCase().includes(searchVal);
        if (!matchName && !matchCode) return false;
      }
      if (deptVal) {
        const matchDept = String(r.department_id || '') === deptVal || (r.department_name || '').toLowerCase().includes(deptVal.toLowerCase());
        if (!matchDept) return false;
      }
      return true;
    });

    // Group rows by employee
    const empGroups: Record<string, { emp_code: string; employee_name: string; department_name: string; summary: Record<string, any>; records: EmpPerfRecord[] }> = {};
    const empOrder: string[] = [];

    filteredRows.forEach(r => {
      const empKey = r.emp_code && r.emp_code !== 'UNASSIGNED' ? r.emp_code : (r.employee_name || 'Staff');
      if (!empGroups[empKey]) {
        empGroups[empKey] = {
          emp_code: r.emp_code || '',
          employee_name: r.employee_name || 'Staff',
          department_name: r.department_name || 'General',
          summary: {
            self_leads: 0,
            overall_new_leads: 0,
            overdue_leads: r.overdue_leads || 0,
            overall_won: 0,
            overall_rev: 0,
            solar_won: 0,
            solar_rev: 0,
            etc_won: 0,
            etc_rev: 0,
            b2b_won: 0,
            b2b_rev: 0,
            b2c_won: 0,
            b2c_rev: 0,
            insurance_won: 0,
            insurance_rev: 0,
            attendance_days: 0,
            avg_talk_time_per_day: r.avg_talk_time_per_day || '—'
          },
          records: []
        };
        empOrder.push(empKey);
      }

      const g = empGroups[empKey];
      g.summary.self_leads += r.self_leads || 0;
      g.summary.overall_new_leads += r.overall_new_leads || 0;
      g.summary.overall_won += r.overall_won || 0;
      g.summary.overall_rev += r.overall_rev || 0;
      g.summary.solar_won += r.solar_won || 0;
      g.summary.solar_rev += r.solar_rev || 0;
      g.summary.etc_won += r.etc_won || 0;
      g.summary.etc_rev += r.etc_rev || 0;
      g.summary.b2b_won += r.b2b_won || 0;
      g.summary.b2b_rev += r.b2b_rev || 0;
      g.summary.b2c_won += r.b2c_won || 0;
      g.summary.b2c_rev += r.b2c_rev || 0;
      g.summary.insurance_won += r.insurance_won || 0;
      g.summary.insurance_rev += r.insurance_rev || 0;
      g.summary.attendance_days += r.attendance_days || 0;
      g.records.push(r);
    });

    return `
      <div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:14px; margin-bottom:14px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
          <div>
            <div style="font-size:13px; font-weight:700; color:#ffffff; display:flex; align-items:center; gap:6px;">
              <i class="fas fa-users-cog" style="color:#2563eb;"></i> Employee Performance
            </div>
            <div style="font-size:10px; color:#64748b; margin-top:2px;">Across departments, categories &amp; talk time</div>
          </div>
          <button id="empPerfRefreshBtn" style="background:transparent; border:none; color:#38bdf8; font-size:12px; cursor:pointer; font-weight:600;">
            <i class="fas fa-sync-alt"></i>
          </button>
        </div>

        <!-- Section toggle (Monthly vs Weekly) -->
        <div style="display:flex; background:#0f172a; border:1px solid #334155; border-radius:8px; padding:3px; margin-bottom:12px;">
          <button id="empPerfMonthlyTab" style="flex:1; background:${this.empPerfActiveSection === 'monthly' ? '#2563eb' : 'transparent'}; color:${this.empPerfActiveSection === 'monthly' ? 'white' : '#94a3b8'}; border:none; border-radius:6px; padding:6px 10px; font-size:11px; font-weight:700; cursor:pointer;">
            Monthly Performance
          </button>
          <button id="empPerfWeeklyTab" style="flex:1; background:${this.empPerfActiveSection === 'weekly' ? '#0891b2' : 'transparent'}; color:${this.empPerfActiveSection === 'weekly' ? 'white' : '#94a3b8'}; border:none; border-radius:6px; padding:6px 10px; font-size:11px; font-weight:700; cursor:pointer;">
            Weekly (12 Wk)
          </button>
        </div>

        <!-- Filters: Search & Department -->
        <div style="display:flex; gap:8px; margin-bottom:12px; flex-direction:column;">
          <input type="text" id="empPerfSearchInput" placeholder="Search employee name or code..." value="${this.empPerfSearch}" style="width:100%; background:#0f172a; border:1px solid #334155; color:#f1f5f9; border-radius:6px; padding:7px 10px; font-size:12px; outline:none;">
          <select id="empPerfDeptSelect" style="width:100%; background:#0f172a; border:1px solid #334155; color:#f1f5f9; border-radius:6px; padding:7px 10px; font-size:12px;">
            <option value="">All Departments</option>
            ${departments.map(d => `
              <option value="${d.name}" ${this.empPerfDeptFilter === d.name ? 'selected' : ''}>${d.name}</option>
            `).join('')}
          </select>
        </div>

        ${empOrder.length === 0 ? `
          <div style="text-align:center; color:#64748b; padding:24px; font-size:12px;">No employee records match the filter</div>
        ` : `
          <!-- Employee Cards List -->
          <div style="display:flex; flex-direction:column; gap:10px;">
            ${empOrder.map(empKey => {
              const group = empGroups[empKey];
              const s = group.summary;
              const isExpanded = !!this.expandedEmpMap[empKey];
              const winPct = s.overall_new_leads > 0 ? ((s.overall_won / s.overall_new_leads) * 100).toFixed(0) : '0';

              return `
                <div style="background:#0f172a; border:1px solid #334155; border-radius:10px; padding:12px;">
                  <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
                    <div>
                      <div style="font-size:13px; font-weight:700; color:#f1f5f9;">${group.employee_name}</div>
                      <div style="display:flex; align-items:center; gap:6px; margin-top:2px;">
                        <span style="font-size:10px; color:#38bdf8; font-weight:600;">${group.emp_code}</span>
                        <span style="font-size:9.5px; background:#1e293b; color:#94a3b8; padding:1px 6px; border-radius:4px;">${group.department_name}</span>
                      </div>
                    </div>
                    <div style="text-align:right;">
                      <div style="font-size:14px; font-weight:800; color:#34d399;">${s.overall_won} Won</div>
                      <div style="font-size:10.5px; font-weight:600; color:#818cf8;">${this.fmtVal(s.overall_rev)}</div>
                    </div>
                  </div>

                  <!-- Quick Stats Grid -->
                  <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:6px; background:#1e293b; border-radius:6px; padding:8px; margin-bottom:8px; text-align:center;">
                    <div>
                      <div style="font-size:9px; color:#94a3b8;">Leads</div>
                      <div style="font-size:11px; font-weight:700; color:#f1f5f9;">${s.overall_new_leads}</div>
                    </div>
                    <div>
                      <div style="font-size:9px; color:#94a3b8;">Win Rate</div>
                      <div style="font-size:11px; font-weight:700; color:#a7f3d0;">${winPct}%</div>
                    </div>
                    <div>
                      <div style="font-size:9px; color:#94a3b8;">Talk Time</div>
                      <div style="font-size:11px; font-weight:700; color:#38bdf8;">${s.avg_talk_time_per_day}</div>
                    </div>
                    <div>
                      <div style="font-size:9px; color:#94a3b8;">Attendance</div>
                      <div style="font-size:11px; font-weight:700; color:#fbbf24;">${s.attendance_days}d</div>
                    </div>
                  </div>

                  <!-- Category Won Distribution Chips -->
                  <div style="display:flex; flex-wrap:wrap; gap:4px; margin-bottom:8px; font-size:9.5px;">
                    ${s.solar_won > 0 ? `<span style="background:#064e3b; color:#6ee7b7; padding:2px 6px; border-radius:4px;">☀️ Solar: ${s.solar_won} (${this.fmtVal(s.solar_rev)})</span>` : ''}
                    ${s.etc_won > 0 ? `<span style="background:#3b0764; color:#d8b4fe; padding:2px 6px; border-radius:4px;">🎓 ETC: ${s.etc_won} (${this.fmtVal(s.etc_rev)})</span>` : ''}
                    ${s.b2b_won > 0 ? `<span style="background:#1e3a8a; color:#93c5fd; padding:2px 6px; border-radius:4px;">⚡ B2B: ${s.b2b_won} (${this.fmtVal(s.b2b_rev)})</span>` : ''}
                    ${s.b2c_won > 0 ? `<span style="background:#701a75; color:#f5d0fe; padding:2px 6px; border-radius:4px;">🛵 B2C: ${s.b2c_won}</span>` : ''}
                    ${s.insurance_won > 0 ? `<span style="background:#78350f; color:#fde68a; padding:2px 6px; border-radius:4px;">🛡️ Ins: ${s.insurance_won}</span>` : ''}
                  </div>

                  <!-- Toggle details button -->
                  <button class="toggle-emp-btn" data-emp="${empKey}" style="width:100%; background:#1e293b; border:1px solid #334155; color:#94a3b8; border-radius:6px; padding:6px; font-size:10.5px; font-weight:600; cursor:pointer; display:flex; justify-content:center; align-items:center; gap:6px;">
                    <span>${isExpanded ? 'Hide Periods' : `View ${group.records.length} Period Details`}</span>
                    <i class="fas fa-chevron-${isExpanded ? 'up' : 'down'}"></i>
                  </button>

                  <!-- Expanded Periods List -->
                  ${isExpanded ? `
                    <div style="margin-top:8px; border-top:1px dashed #334155; padding-top:8px; display:flex; flex-direction:column; gap:6px;">
                      ${group.records.map(r => `
                        <div style="background:#131d33; border-radius:6px; padding:6px 8px; font-size:10.5px; display:flex; justify-content:space-between; align-items:center;">
                          <div>
                            <span style="font-weight:700; color:#38bdf8;">${r.period_key}</span>
                            <span style="color:#64748b; margin-left:6px;">(${r.overall_new_leads || 0} leads)</span>
                          </div>
                          <div style="text-align:right;">
                            <span style="color:#34d399; font-weight:700;">${r.overall_won || 0} Won</span>
                            <span style="color:#818cf8; margin-left:6px;">${this.fmtVal(r.overall_rev)}</span>
                          </div>
                        </div>
                      `).join('')}
                    </div>
                  ` : ''}
                </div>
              `;
            }).join('')}
          </div>
        `}
      </div>
    `;
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     TAB 4: ETC STUDENTS BATCH WISE (Web Parity)
     ═══════════════════════════════════════════════════════════════════════════ */
  private renderEtcBatchwiseTab(): string {
    if (this.etcBatchLoading) {
      return `
        <div style="text-align:center; padding:48px 16px;">
          <i class="fas fa-circle-notch fa-spin" style="font-size:28px; color:#38bdf8; margin-bottom:12px;"></i>
          <div style="color:#94a3b8; font-size:13px; font-weight:500;">Loading ETC Batch-wise report...</div>
        </div>
      `;
    }

    const data = this.etcBatchData || {};
    const kpis = data.kpis || {};
    const rawBatches = data.batches || [];

    // Filter batches based on search
    const q = this.etcBatchSearch.toLowerCase().trim();
    const batches = rawBatches.filter(b => {
      if (!q) return true;
      const matchBatch = (b.batch_no || '').toLowerCase().includes(q) || (b.month || '').toLowerCase().includes(q);
      const matchStudents = (b.students || []).some(s =>
        (s.name || '').toLowerCase().includes(q) ||
        (s.phone || '').includes(q) ||
        (s.student_id || '').toLowerCase().includes(q) ||
        (s.registration_id || '').toLowerCase().includes(q)
      );
      return matchBatch || matchStudents;
    });

    return `
      <!-- 6 ETC KPI Cards (Web Parity) -->
      <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:6px; margin-bottom:8px;">
        <div style="background:#1e293b; border-left:3px solid #1e3a5f; border-radius:8px; padding:8px; text-align:center;">
          <div style="font-size:9px; color:#94a3b8; font-weight:700;">BATCHES</div>
          <div style="font-size:15px; font-weight:800; color:#f1f5f9; margin-top:2px;">${this.fmtNum(kpis.total_batches)}</div>
        </div>
        <div style="background:#1e293b; border-left:3px solid #2563eb; border-radius:8px; padding:8px; text-align:center;">
          <div style="font-size:9px; color:#93c5fd; font-weight:700;">STUDENTS</div>
          <div style="font-size:15px; font-weight:800; color:#60a5fa; margin-top:2px;">${this.fmtNum(kpis.total_students)}</div>
        </div>
        <div style="background:#1e293b; border-left:3px solid #16a34a; border-radius:8px; padding:8px; text-align:center;">
          <div style="font-size:9px; color:#86efac; font-weight:700;">COMPLETED</div>
          <div style="font-size:15px; font-weight:800; color:#4ade80; margin-top:2px;">${this.fmtNum(kpis.completed_students)}</div>
        </div>
      </div>

      <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:6px; margin-bottom:12px;">
        <div style="background:#1e293b; border-left:3px solid #7c3aed; border-radius:8px; padding:8px; text-align:center;">
          <div style="font-size:9px; color:#d8b4fe; font-weight:700;">DEAL VALUE</div>
          <div style="font-size:12.5px; font-weight:800; color:#c084fc; margin-top:2px;">${this.fmtVal(kpis.total_deal_value)}</div>
        </div>
        <div style="background:#1e293b; border-left:3px solid #059669; border-radius:8px; padding:8px; text-align:center;">
          <div style="font-size:9px; color:#6ee7b7; font-weight:700;">RECEIVED</div>
          <div style="font-size:12.5px; font-weight:800; color:#34d399; margin-top:2px;">${this.fmtVal(kpis.total_received)}</div>
        </div>
        <div style="background:#1e293b; border-left:3px solid #dc2626; border-radius:8px; padding:8px; text-align:center;">
          <div style="font-size:9px; color:#fca5a5; font-weight:700;">BALANCE</div>
          <div style="font-size:12.5px; font-weight:800; color:#f87171; margin-top:2px;">${this.fmtVal(kpis.total_balance)}</div>
        </div>
      </div>

      <!-- Controls: Search & Expand All -->
      <div style="background:#1e293b; border:1px solid #334155; border-radius:10px; padding:10px; margin-bottom:12px;">
        <div style="display:flex; gap:8px; align-items:center; margin-bottom:8px;">
          <input type="text" id="etcBatchSearchInput" placeholder="Search batch or student name..." value="${this.etcBatchSearch}" style="flex:1; background:#0f172a; border:1px solid #334155; color:#f1f5f9; border-radius:6px; padding:7px 10px; font-size:12px; outline:none;">
          <button id="etcBatchRefreshBtn" style="background:#0f172a; border:1px solid #334155; color:#38bdf8; border-radius:6px; padding:7px 10px; font-size:12px; cursor:pointer;">
            <i class="fas fa-sync-alt"></i>
          </button>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size:11px; color:#94a3b8;">${batches.length} batches found</span>
          <div style="display:flex; gap:6px;">
            <button id="etcExpandAllBtn" style="background:#0f172a; border:1px solid #334155; color:#38bdf8; border-radius:4px; padding:4px 8px; font-size:10px; font-weight:600; cursor:pointer;">
              Expand All
            </button>
            <button id="etcCollapseAllBtn" style="background:#0f172a; border:1px solid #334155; color:#94a3b8; border-radius:4px; padding:4px 8px; font-size:10px; font-weight:600; cursor:pointer;">
              Collapse All
            </button>
          </div>
        </div>
      </div>

      ${batches.length === 0 ? `
        <div style="text-align:center; color:#64748b; padding:24px; font-size:12px;">No ETC batches found</div>
      ` : `
        <!-- Batches List -->
        <div style="display:flex; flex-direction:column; gap:10px;">
          ${batches.map(b => {
            const bNo = b.batch_no || 'Batch';
            const isExpanded = !!this.expandedBatchMap[bNo];
            const students = b.students || [];

            return `
              <div style="background:#0f172a; border:1px solid #334155; border-radius:10px; padding:12px;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
                  <div>
                    <div style="font-size:13px; font-weight:700; color:#f1f5f9;">${bNo}</div>
                    <div style="font-size:10.5px; color:#64748b; margin-top:2px;">${b.month || '—'} · Start: ${b.start_date || '—'}</div>
                  </div>
                  <div style="text-align:right;">
                    <div style="font-size:12px; font-weight:700; color:#38bdf8;">${b.total_students || 0} Students</div>
                    <div style="font-size:10px; color:#34d399;">${b.completed || 0} Completed</div>
                  </div>
                </div>

                <!-- Fee Stats -->
                <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:6px; background:#1e293b; border-radius:6px; padding:6px 8px; margin-bottom:8px; text-align:center;">
                  <div>
                    <div style="font-size:9px; color:#94a3b8;">Total Fee</div>
                    <div style="font-size:11px; font-weight:700; color:#c084fc;">${this.fmtVal(b.deal_value)}</div>
                  </div>
                  <div>
                    <div style="font-size:9px; color:#94a3b8;">Received</div>
                    <div style="font-size:11px; font-weight:700; color:#34d399;">${this.fmtVal(b.received)}</div>
                  </div>
                  <div>
                    <div style="font-size:9px; color:#94a3b8;">Balance</div>
                    <div style="font-size:11px; font-weight:700; color:#f87171;">${this.fmtVal(b.balance)}</div>
                  </div>
                </div>

                <!-- Toggle Batch Students -->
                <button class="toggle-batch-btn" data-batch="${bNo}" style="width:100%; background:#1e293b; border:1px solid #334155; color:#94a3b8; border-radius:6px; padding:6px; font-size:10.5px; font-weight:600; cursor:pointer; display:flex; justify-content:center; align-items:center; gap:6px;">
                  <span>${isExpanded ? 'Hide Students' : `View ${students.length} Students`}</span>
                  <i class="fas fa-chevron-${isExpanded ? 'up' : 'down'}"></i>
                </button>

                <!-- Students in Batch -->
                ${isExpanded ? `
                  <div style="margin-top:8px; border-top:1px dashed #334155; padding-top:8px; display:flex; flex-direction:column; gap:6px;">
                    ${students.map(s => `
                      <div style="background:#131d33; border:1px solid #1e293b; border-radius:6px; padding:8px 10px;">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:4px;">
                          <div>
                            <div style="font-size:11.5px; font-weight:600; color:#f1f5f9;">${s.name}</div>
                            <div style="font-size:9.5px; color:#64748b;">${s.student_id || s.registration_id || 'ID'} · ${s.phone || '—'}</div>
                          </div>
                          <span style="font-size:9px; font-weight:700; padding:2px 6px; border-radius:4px; ${s.training_stage === 'training_completed' ? 'background:#064e3b; color:#6ee7b7;' : 'background:#1e3a8a; color:#93c5fd;'}">
                            ${s.training_stage === 'training_completed' ? 'COMPLETED' : 'TRAINING'}
                          </span>
                        </div>
                        <div style="display:flex; justify-content:space-between; font-size:10px; margin-top:4px;">
                          <span style="color:#94a3b8;">Fee: ${this.fmtVal(s.deal_value)}</span>
                          <span style="color:#34d399; font-weight:600;">Paid: ${this.fmtVal(s.received)}</span>
                          <span style="color:#f87171; font-weight:600;">Bal: ${this.fmtVal(s.balance)}</span>
                        </div>
                      </div>
                    `).join('')}
                  </div>
                ` : ''}
              </div>
            `;
          }).join('')}
        </div>
      `}
    `;
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     TAB 5: HANDLERS LEADERBOARD (Web Parity with Handler Types)
     ═══════════════════════════════════════════════════════════════════════════ */
  private renderHandlersTab(): string {
    // Select appropriate data set based on active handler type
    let handlerList: BreakdownItem[] = [];
    if (this.activeHandlerType === 'ground') {
      handlerList = this.rawLeadData.by_ground_source || this.rawLeadData.handlers || [];
    } else if (this.activeHandlerType === 'handler') {
      handlerList = this.rawLeadData.by_handler || this.rawLeadData.handlers || [];
    } else if (this.activeHandlerType === 'support') {
      handlerList = this.byTelecaller;
    } else if (this.activeHandlerType === 'field') {
      handlerList = this.byFieldStaff;
    } else if (this.activeHandlerType === 'guru') {
      handlerList = this.rawLeadData.by_guru || [];
    } else if (this.activeHandlerType === 'zguru') {
      handlerList = this.rawLeadData.by_z_guru || [];
    } else if (this.activeHandlerType === 'partner') {
      handlerList = this.rawLeadData.by_partner || [];
    } else if (this.activeHandlerType === 'source') {
      handlerList = this.bySource;
    } else {
      handlerList = this.rawLeadData.handlers || [];
    }

    const q = (this.handlerSearch || '').toLowerCase().trim();
    const filteredHandlers = handlerList.filter(h => {
      if (!q) return true;
      const n = (h.name || h.source || h.status || '').toLowerCase();
      const c = (h.emp_code || '').toLowerCase();
      return n.includes(q) || c.includes(q);
    });

    return `
      <div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:14px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
          <span style="font-size:13px; font-weight:700; color:#ffffff;"><i class="fas fa-trophy" style="color:#fbbf24;"></i> Handler Leaderboard</span>
          <span style="font-size:11px; color:#94a3b8; font-weight:400;">${filteredHandlers.length} Handlers</span>
        </div>

        <!-- Handler Type Selector Chips (Web Parity) -->
        <div style="display:flex; gap:6px; overflow-x:auto; padding-bottom:6px; margin-bottom:10px; -webkit-overflow-scrolling:touch;">
          <button class="ht-type-btn ${this.activeHandlerType === 'ground' ? 'active' : ''}" data-ht="ground" style="${this.getHtChipStyle(this.activeHandlerType === 'ground')}">Ground Source</button>
          <button class="ht-type-btn ${this.activeHandlerType === 'handler' ? 'active' : ''}" data-ht="handler" style="${this.getHtChipStyle(this.activeHandlerType === 'handler')}">Handler</button>
          <button class="ht-type-btn ${this.activeHandlerType === 'support' ? 'active' : ''}" data-ht="support" style="${this.getHtChipStyle(this.activeHandlerType === 'support')}">Telecaller</button>
          <button class="ht-type-btn ${this.activeHandlerType === 'field' ? 'active' : ''}" data-ht="field" style="${this.getHtChipStyle(this.activeHandlerType === 'field')}">Showroom</button>
          <button class="ht-type-btn ${this.activeHandlerType === 'guru' ? 'active' : ''}" data-ht="guru" style="${this.getHtChipStyle(this.activeHandlerType === 'guru')}">Senior</button>
          <button class="ht-type-btn ${this.activeHandlerType === 'zguru' ? 'active' : ''}" data-ht="zguru" style="${this.getHtChipStyle(this.activeHandlerType === 'zguru')}">Extended</button>
          <button class="ht-type-btn ${this.activeHandlerType === 'partner' ? 'active' : ''}" data-ht="partner" style="${this.getHtChipStyle(this.activeHandlerType === 'partner')}">Business Partner</button>
          <button class="ht-type-btn ${this.activeHandlerType === 'source' ? 'active' : ''}" data-ht="source" style="${this.getHtChipStyle(this.activeHandlerType === 'source')}">Lead Source</button>
        </div>

        <!-- Handler Search Input -->
        <div style="margin-bottom:12px;">
          <input type="text" id="execHandlerSearchInput" placeholder="Search handler name or code..." value="${this.handlerSearch}" style="width:100%; background:#0f172a; border:1px solid #334155; color:#f1f5f9; border-radius:6px; padding:7px 10px; font-size:12px; outline:none;">
        </div>

        ${filteredHandlers.length === 0 ? `
          <div style="text-align:center; color:#64748b; padding:24px; font-size:12px;">No handlers matching current filter</div>
        ` : `
          <div style="display:flex; flex-direction:column; gap:8px;">
            ${filteredHandlers.slice(0, 50).map((h, i) => {
              const name = h.name || h.source || 'Staff Member';
              const code = h.emp_code ? `(${h.emp_code})` : '';
              const tot = h.total || h.count || 0;
              const won = h.won || 0;
              const winPct = tot > 0 ? ((won / tot) * 100).toFixed(0) : '0';
              const dv = h.won_deal_value || h.deal_value || 0;
              const medal = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `${i + 1}.`;

              return `
                <div style="background:#0f172a; border:1px solid #334155; border-radius:8px; padding:10px 12px; display:flex; justify-content:space-between; align-items:center;">
                  <div style="display:flex; align-items:center; gap:8px; max-width:60%;">
                    <span style="font-size:12px; font-weight:700; color:#fbbf24; min-width:20px;">${medal}</span>
                    <div style="overflow:hidden;">
                      <div style="font-size:12px; font-weight:600; color:#f1f5f9; text-overflow:ellipsis; white-space:nowrap; overflow:hidden;">${name}</div>
                      <div style="font-size:10px; color:#64748b;">${code}</div>
                    </div>
                  </div>
                  <div style="text-align:right;">
                    <div style="font-size:12px; font-weight:700; color:#34d399;">${won} Won <span style="font-size:10px; color:#64748b;">/ ${tot}</span></div>
                    <div style="font-size:11px; font-weight:600; color:#818cf8;">${this.fmtVal(dv)} (${winPct}%)</div>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        `}
      </div>
    `;
  }

  private getHtChipStyle(active: boolean): string {
    if (active) {
      return 'white-space:nowrap; background:#2563eb; color:white; border:none; border-radius:16px; padding:5px 12px; font-size:10.5px; font-weight:700; cursor:pointer;';
    }
    return 'white-space:nowrap; background:#0f172a; color:#94a3b8; border:1px solid #334155; border-radius:16px; padding:5px 12px; font-size:10.5px; font-weight:600; cursor:pointer;';
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     EVENT LISTENERS
     ═══════════════════════════════════════════════════════════════════════════ */
  private attachEventListeners(): void {
    // Preset buttons
    this.container.querySelectorAll('.preset-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const target = e.currentTarget as HTMLElement;
        const preset = target.dataset.preset as any;
        if (preset) this.setPreset(preset);
      });
    });

    // Segment dropdown
    const catEl = document.getElementById('execCategoryFilter') as HTMLSelectElement;
    if (catEl) {
      catEl.addEventListener('change', () => {
        this.selectedSegment = catEl.value;
        this.loadData();
      });
    }

    // Custom date apply
    document.getElementById('execApplyDateBtn')?.addEventListener('click', () => {
      const fromEl = document.getElementById('execFromDate') as HTMLInputElement;
      const toEl = document.getElementById('execToDate') as HTMLInputElement;
      if (fromEl) this.fromDate = fromEl.value;
      if (toEl) this.toDate = toEl.value;
      this.loadData();
    });

    // Reset button
    document.getElementById('execResetBtn')?.addEventListener('click', () => {
      this.fromDate = '';
      this.toDate = '';
      this.selectedSegment = '';
      this.activePreset = 'overall';
      this.loadData();
    });

    // Refresh button
    document.getElementById('execRefreshBtn')?.addEventListener('click', () => {
      this.loadData();
    });

    // Nav tabs
    this.container.querySelectorAll('.nav-tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const target = e.currentTarget as HTMLElement;
        const tab = target.dataset.tab as any;
        if (tab) {
          this.switchTab(tab);
        }
      });
    });

    // Trends view toggle buttons
    document.getElementById('trendMonthlyBtn')?.addEventListener('click', () => {
      this.activeTrendView = 'monthly';
      this.render();
    });
    document.getElementById('trendWeeklyBtn')?.addEventListener('click', () => {
      this.activeTrendView = 'weekly';
      this.render();
    });

    // Employee Performance Section Toggles
    document.getElementById('empPerfMonthlyTab')?.addEventListener('click', () => {
      this.empPerfActiveSection = 'monthly';
      this.render();
    });
    document.getElementById('empPerfWeeklyTab')?.addEventListener('click', () => {
      this.empPerfActiveSection = 'weekly';
      this.render();
    });

    // Employee Performance Refresh
    document.getElementById('empPerfRefreshBtn')?.addEventListener('click', () => {
      this.loadEmployeePerformance();
    });

    // Employee Performance Search
    const empSearchEl = document.getElementById('empPerfSearchInput') as HTMLInputElement;
    if (empSearchEl) {
      empSearchEl.addEventListener('input', () => {
        this.empPerfSearch = empSearchEl.value;
        this.render();
        const newEl = document.getElementById('empPerfSearchInput') as HTMLInputElement;
        if (newEl) {
          newEl.focus();
          newEl.selectionStart = newEl.selectionEnd = newEl.value.length;
        }
      });
    }

    // Employee Performance Dept Select
    const empDeptEl = document.getElementById('empPerfDeptSelect') as HTMLSelectElement;
    if (empDeptEl) {
      empDeptEl.addEventListener('change', () => {
        this.empPerfDeptFilter = empDeptEl.value;
        this.render();
      });
    }

    // Toggle Employee Expansion
    this.container.querySelectorAll('.toggle-emp-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const target = e.currentTarget as HTMLElement;
        const empKey = target.dataset.emp;
        if (empKey) {
          this.expandedEmpMap[empKey] = !this.expandedEmpMap[empKey];
          this.render();
        }
      });
    });

    // ETC Batch Search
    const etcSearchEl = document.getElementById('etcBatchSearchInput') as HTMLInputElement;
    if (etcSearchEl) {
      etcSearchEl.addEventListener('input', () => {
        this.etcBatchSearch = etcSearchEl.value;
        this.render();
        const newEl = document.getElementById('etcBatchSearchInput') as HTMLInputElement;
        if (newEl) {
          newEl.focus();
          newEl.selectionStart = newEl.selectionEnd = newEl.value.length;
        }
      });
    }

    // ETC Batch Refresh
    document.getElementById('etcBatchRefreshBtn')?.addEventListener('click', () => {
      this.loadEtcBatchwise();
    });

    // ETC Expand / Collapse All
    document.getElementById('etcExpandAllBtn')?.addEventListener('click', () => {
      if (this.etcBatchData && this.etcBatchData.batches) {
        this.etcBatchData.batches.forEach(b => {
          if (b.batch_no) this.expandedBatchMap[b.batch_no] = true;
        });
        this.render();
      }
    });
    document.getElementById('etcCollapseAllBtn')?.addEventListener('click', () => {
      this.expandedBatchMap = {};
      this.render();
    });

    // Toggle Batch Students
    this.container.querySelectorAll('.toggle-batch-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const target = e.currentTarget as HTMLElement;
        const bNo = target.dataset.batch;
        if (bNo) {
          this.expandedBatchMap[bNo] = !this.expandedBatchMap[bNo];
          this.render();
        }
      });
    });

    // Handler Type buttons
    this.container.querySelectorAll('.ht-type-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const target = e.currentTarget as HTMLElement;
        const ht = target.dataset.ht as any;
        if (ht) {
          this.activeHandlerType = ht;
          this.render();
        }
      });
    });

    // Handler search input
    const hSearchEl = document.getElementById('execHandlerSearchInput') as HTMLInputElement;
    if (hSearchEl) {
      hSearchEl.addEventListener('input', () => {
        this.handlerSearch = hSearchEl.value;
        this.render();
        const newSearch = document.getElementById('execHandlerSearchInput') as HTMLInputElement;
        if (newSearch) {
          newSearch.focus();
          newSearch.selectionStart = newSearch.selectionEnd = newSearch.value.length;
        }
      });
    }

    // Workflow shortcuts
    this.container.querySelectorAll('.workflow-nav-card').forEach(card => {
      card.addEventListener('click', (e) => {
        const target = e.currentTarget as HTMLElement;
        const route = target.dataset.route as any;
        const tab = target.dataset.tab;
        if (route) {
          if (tab) {
            routerService.navigate(route, { tab });
          } else {
            routerService.navigate(route);
          }
        }
      });
    });

    // Category cards click -> jump to category master
    this.container.querySelectorAll('.cat-card').forEach(card => {
      card.addEventListener('click', (e) => {
        const target = e.currentTarget as HTMLElement;
        const cat = target.dataset.cat;
        routerService.navigate('category-leads-master' as any, { tab: cat || 'solar' });
      });
    });
  }
}
