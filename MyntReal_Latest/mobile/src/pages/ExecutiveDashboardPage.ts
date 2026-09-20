/**
 * Executive Dashboard Page (Mobile View)
 * DC Protocol: DC_MOBILE_STAFF_EXEC_DASH_001
 * Comprehensive mobile interface for Executive Dashboard & Leadership Analytics
 * Full Parity with Web staff_executive_dashboard.html across all 4 platforms
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import { routerService } from '../services/router.service';
import { callController } from '../services/call-controller';

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
  code?: string;
  type?: string;
  mnr_id?: string;
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
  label?: string;
  total?: number;
  won?: number;
  submitted?: number;
  submitted_val?: number;
  submitted_value?: number;
  pipeline?: number;
  pipeline_val?: number;
  pipeline_value?: number;
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
  department_id?: number | string;
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

const SOLAR_SW_COLS = [
  { key: 'sp_completed', label: 'Completed', color: '#059669' },
  { key: 'sp_installation_pending', label: 'Installation Pending', color: '#3b82f6' },
  { key: 'sp_at_bank', label: 'At Bank', color: '#f97316' },
  { key: 'sp_documents_pending', label: 'Docs Pending', color: '#d97706' },
  { key: 'sp_application_submitted', label: 'App Submitted', color: '#8b5cf6' },
  { key: 'sp_loan_rejected', label: 'Loan Rejected', color: '#dc2626' },
  { key: 'sp_docs_issue', label: 'Docs Issue', color: '#b45309' },
  { key: 'sp_load_extension', label: 'Load Extension', color: '#7c3aed' },
  { key: 'sp_electricity_bill_change', label: 'Elec Bill Chg', color: '#0891b2' },
  { key: 'sp_net_meter_pending', label: 'Net Meter', color: '#9333ea' },
  { key: 'sp_balance_pending', label: 'Bal Pending', color: '#c2410c' },
  { key: 'sp_balance_received', label: 'Bal Received', color: '#065f46' },
  { key: 'sp_subsidy_pending', label: 'Subsidy Pending', color: '#0f766e' },
  { key: 'sp_not_interested', label: 'Not Interested', color: '#6b7280' },
  { key: 'sp_cancelled', label: 'Cancelled', color: '#9ca3af' },
  { key: 'sp_different_vendor', label: 'Diff Vendor', color: '#a78bfa' },
];

export class ExecutiveDashboardPage {
  private container: HTMLElement;
  private loading: boolean = true;
  private activePreset: 'today' | 'this_week' | 'last_week' | 'this_month' | 'last_month' | 'this_fy' | 'overall' = 'overall';
  private fromDate: string = '';
  private toDate: string = '';
  private selectedSegment: string = '';
  private activeTab: 'overview' | 'trends' | 'emp_perf' | 'stagewise' | 'handlers' | 'etc_batchwise' = 'overview';

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

  // Stagewise Tab state
  private stagewiseSearch: string = '';

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
  private activeHandlerType: 'ground' | 'handler' | 'support' | 'field' | 'guru' | 'zguru' | 'adguru' | 'partner' | 'source' = 'ground';

  // Executive Drilldown Modal State
  private isDrilldownOpen: boolean = false;
  private drilldownLoading: boolean = false;
  private drilldownTitle: string = '';
  private drilldownSubtitle: string = '';
  private drilldownLeads: any[] = [];
  private drilldownFilterText: string = '';
  private drilldownSelectedLead: any | null = null;
  private drilldownNotes: any[] = [];
  private drilldownNotesLoading: boolean = false;
  private drilldownCalls: any[] = [];
  private drilldownCallsLoading: boolean = false;
  private drilldownCallsOpen: boolean = false;
  private drilldownNewNote: string = '';
  private isFullscreenDrilldown: boolean = false;

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

  private switchTab(tab: 'overview' | 'trends' | 'emp_perf' | 'stagewise' | 'handlers' | 'etc_batchwise'): void {
    this.activeTab = tab;
    if (tab === 'emp_perf' && !this.empPerfData && !this.empPerfLoading) {
      this.loadEmployeePerformance();
    } else if (tab === 'etc_batchwise' && !this.etcBatchData && !this.etcBatchLoading) {
      this.loadEtcBatchwise();
    } else {
      this.render();
    }
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     STAGEWISE DATA BUILDER (PARITY WITH WEB _buildSwRows)
     ═══════════════════════════════════════════════════════════════════════════ */
  private buildSwRows(): { rows: BreakdownItem[]; labelCol: string; showCode: boolean } {
    if (!this.rawLeadData) return { rows: [], labelCol: 'Name', showCode: false };
    const t = this.activeHandlerType;
    const SD = (r: any) => ({
      sp_completed: r.sp_completed || 0, dv_sp_completed: r.dv_sp_completed || 0,
      sp_installation_pending: r.sp_installation_pending || 0, dv_sp_installation_pending: r.dv_sp_installation_pending || 0,
      sp_at_bank: r.sp_at_bank || 0, dv_sp_at_bank: r.dv_sp_at_bank || 0,
      sp_documents_pending: r.sp_documents_pending || 0, dv_sp_documents_pending: r.dv_sp_documents_pending || 0,
      sp_application_submitted: r.sp_application_submitted || 0, dv_sp_application_submitted: r.dv_sp_application_submitted || 0,
      sp_loan_rejected: r.sp_loan_rejected || 0, dv_sp_loan_rejected: r.dv_sp_loan_rejected || 0,
      sp_docs_issue: r.sp_docs_issue || 0, dv_sp_docs_issue: r.dv_sp_docs_issue || 0,
      sp_load_extension: r.sp_load_extension || 0, dv_sp_load_extension: r.dv_sp_load_extension || 0,
      sp_electricity_bill_change: r.sp_electricity_bill_change || 0, dv_sp_electricity_bill_change: r.dv_sp_electricity_bill_change || 0,
      sp_net_meter_pending: r.sp_net_meter_pending || 0, dv_sp_net_meter_pending: r.dv_sp_net_meter_pending || 0,
      sp_balance_pending: r.sp_balance_pending || 0, dv_sp_balance_pending: r.dv_sp_balance_pending || 0,
      sp_balance_received: r.sp_balance_received || 0, dv_sp_balance_received: r.dv_sp_balance_received || 0,
      sp_subsidy_pending: r.sp_subsidy_pending || 0, dv_sp_subsidy_pending: r.dv_sp_subsidy_pending || 0,
      sp_not_interested: r.sp_not_interested || 0, dv_sp_not_interested: r.dv_sp_not_interested || 0,
      sp_cancelled: r.sp_cancelled || 0, dv_sp_cancelled: r.dv_sp_cancelled || 0,
      sp_different_vendor: r.sp_different_vendor || 0, dv_sp_different_vendor: r.dv_sp_different_vendor || 0,
    });

    let rows: BreakdownItem[] = [];
    let labelCol = 'Name';
    let showCode = false;

    if (t === 'ground') {
      rows = (this.rawLeadData.by_ground_source || []).map((r: any) => ({ name: r.name || r.code || '—', code: r.code || '', type: r.type || '', total: r.total || 0, deal_value: r.deal_value || 0, completed: r.completed || 0, final_deal_value: r.final_deal_value || 0, ...SD(r) }));
      labelCol = 'Ground Source'; showCode = true;
    } else if (t === 'handler') {
      rows = (this.rawLeadData.by_handler || []).map((r: any) => ({ name: r.name || r.emp_code || '—', code: r.emp_code || '', total: r.total || 0, deal_value: r.deal_value || 0, completed: r.completed || 0, final_deal_value: r.final_deal_value || 0, ...SD(r) }));
      labelCol = 'Handler (Assigned)'; showCode = true;
    } else if (t === 'support') {
      rows = (this.byTelecaller || []).map((r: any) => ({ name: r.name || '—', code: r.emp_code || '', total: r.total || 0, deal_value: r.deal_value || 0, completed: r.completed || 0, final_deal_value: r.final_deal_value || 0, ...SD(r) }));
      labelCol = 'Telecaller'; showCode = true;
    } else if (t === 'field') {
      rows = (this.byFieldStaff || []).map((r: any) => ({ name: r.name || '—', code: r.emp_code || '', total: r.total || 0, deal_value: r.deal_value || 0, completed: r.completed || 0, final_deal_value: r.final_deal_value || 0, ...SD(r) }));
      labelCol = 'Showroom (Field)'; showCode = true;
    } else if (t === 'zguru') {
      rows = (this.rawLeadData.by_z_guru || []).map((r: any) => ({ name: r.name || r.mnr_id || '—', code: r.mnr_id || '', total: r.total || 0, deal_value: r.deal_value || 0, completed: r.completed || 0, final_deal_value: r.final_deal_value || 0, ...SD(r) }));
      labelCol = 'Extended'; showCode = true;
    } else if (t === 'adguru') {
      rows = (this.rawLeadData.by_adi_guru || []).map((r: any) => ({ name: r.name || r.mnr_id || '—', code: r.mnr_id || '', total: r.total || 0, deal_value: r.deal_value || 0, completed: r.completed || 0, final_deal_value: r.final_deal_value || 0, ...SD(r) }));
      labelCol = 'On Ground Support'; showCode = true;
    } else if (t === 'partner') {
      rows = (this.rawLeadData.by_partner || []).map((r: any) => ({ name: r.name || r.code || '—', code: r.code || '', total: r.total || 0, deal_value: r.deal_value || 0, completed: r.completed || 0, final_deal_value: r.final_deal_value || 0, ...SD(r) }));
      labelCol = 'Business Partner'; showCode = true;
    } else if (t === 'guru') {
      rows = (this.rawLeadData.by_guru || []).map((r: any) => ({ name: r.name || r.mnr_id || '—', code: r.mnr_id || '', total: r.total || 0, deal_value: r.deal_value || 0, completed: r.completed || 0, final_deal_value: r.final_deal_value || 0, ...SD(r) }));
      labelCol = 'Senior'; showCode = true;
    } else if (t === 'source') {
      rows = (this.bySource || []).map((r: any) => ({ name: r.source || r.name || '—', code: '', total: r.total || r.count || 0, deal_value: r.deal_value || 0, completed: r.completed || 0, final_deal_value: r.final_deal_value || 0, ...SD(r) }));
      labelCol = 'Lead Source';
    }
    return { rows, labelCol, showCode };
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     EXECUTIVE DRILLDOWN SERVICE CALLS
     ═══════════════════════════════════════════════════════════════════════════ */
  private async openExecDrillDown(htype: string, hkey: string, hname: string, hext?: string): Promise<void> {
    if (!htype || !hkey) return;
    this.isDrilldownOpen = true;
    this.drilldownLoading = true;
    this.drilldownTitle = hname || hkey;
    this.drilldownSubtitle = `Handler Leads · ${htype.toUpperCase()}`;
    this.drilldownLeads = [];
    this.drilldownSelectedLead = null;
    this.drilldownFilterText = '';
    this.render();

    try {
      const p = new URLSearchParams();
      if (this.fromDate) p.set('created_from', this.fromDate);
      if (this.toDate) p.set('created_to', this.toDate);
      if (this.selectedSegment) p.set('category', this.selectedSegment);
      p.set('handler_type', htype);
      p.set('handler_key', hkey);
      if (hext) p.set('handler_type_ext', hext);

      const resp = await apiService.get<any>(`/crm/exec-handler-leads?${p.toString()}`);
      if (resp && resp.success !== false) {
        this.drilldownLeads = resp.data || [];
        const total = resp.total || this.drilldownLeads.length;
        this.drilldownSubtitle = `${this.fmtNum(total)} leads retrieved`;
      }
    } catch (e: any) {
      console.error('[ExecutiveDashboardPage] Failed to fetch handler drilldown leads:', e);
      this.drilldownSubtitle = `Error: ${e.message || 'Failed to load'}`;
    } finally {
      this.drilldownLoading = false;
      this.render();
    }
  }

  private async openTrendDrillDown(periodType: string, label: string, metric: string, columnName: string): Promise<void> {
    this.isDrilldownOpen = true;
    this.drilldownLoading = true;
    this.drilldownTitle = `${columnName} — ${label}`;
    this.drilldownSubtitle = `Loading trend leads…`;
    this.drilldownLeads = [];
    this.drilldownSelectedLead = null;
    this.drilldownFilterText = '';
    this.render();

    try {
      const p = new URLSearchParams();
      if (this.fromDate) p.set('created_from', this.fromDate);
      if (this.toDate) p.set('created_to', this.toDate);
      if (this.selectedSegment) p.set('category', this.selectedSegment);
      p.set('period_type', periodType);
      p.set('label', label);
      p.set('metric', metric);

      const resp = await apiService.get<any>(`/crm/exec-trend-leads?${p.toString()}`);
      if (resp && resp.success !== false) {
        this.drilldownLeads = resp.data || [];
        const total = resp.total || this.drilldownLeads.length;
        this.drilldownSubtitle = `${this.fmtNum(total)} leads matching metric`;
      }
    } catch (e: any) {
      console.error('[ExecutiveDashboardPage] Failed to fetch trend leads:', e);
      this.drilldownSubtitle = `Error: ${e.message || 'Failed to load'}`;
    } finally {
      this.drilldownLoading = false;
      this.render();
    }
  }

  private async openEmpPerfDrillDown(section: string, periodKey: string, empCode: string, empName: string, metric: string, columnName: string): Promise<void> {
    this.isDrilldownOpen = true;
    this.drilldownLoading = true;
    const dispPeriod = periodKey === 'TOTAL' ? 'Total Period' : periodKey;
    this.drilldownTitle = `${columnName} — ${empName} (${dispPeriod})`;
    this.drilldownSubtitle = `Loading employee performance leads…`;
    this.drilldownLeads = [];
    this.drilldownSelectedLead = null;
    this.drilldownFilterText = '';
    this.render();

    try {
      const p = new URLSearchParams();
      if (this.fromDate) p.set('created_from', this.fromDate);
      if (this.toDate) p.set('created_to', this.toDate);
      if (this.selectedSegment) p.set('category', this.selectedSegment);
      p.set('period_type', section);
      p.set('period_key', periodKey);
      p.set('emp_code', empCode || '');
      p.set('metric', metric);

      const resp = await apiService.get<any>(`/crm/exec-emp-perf-leads?${p.toString()}`);
      if (resp && resp.success !== false) {
        this.drilldownLeads = resp.data || [];
        const total = resp.total || this.drilldownLeads.length;
        this.drilldownSubtitle = `${this.fmtNum(total)} employee records retrieved`;
      }
    } catch (e: any) {
      console.error('[ExecutiveDashboardPage] Failed to fetch emp perf leads:', e);
      this.drilldownSubtitle = `Error: ${e.message || 'Failed to load'}`;
    } finally {
      this.drilldownLoading = false;
      this.render();
    }
  }

  private async loadLeadNotes(leadId: number, companyId: any): Promise<void> {
    this.drilldownNotesLoading = true;
    this.drilldownNotes = [];
    this.render();

    try {
      const resp = await apiService.get<any>(`/crm/dashboard-v2/leads/${leadId}/notes?company_id=${companyId || ''}`);
      if (resp && resp.success !== false) {
        this.drilldownNotes = resp.data || [];
      }
    } catch (e) {
      console.error('[ExecutiveDashboardPage] Failed to load lead notes:', e);
    } finally {
      this.drilldownNotesLoading = false;
      this.render();
    }
  }

  private async loadLeadCalls(leadId: number): Promise<void> {
    this.drilldownCallsLoading = true;
    this.drilldownCalls = [];
    this.render();

    try {
      const resp = await apiService.get<any>(`/call-tracking/lead/${leadId}/calls`);
      if (resp && resp.success !== false) {
        this.drilldownCalls = resp.data || [];
      }
    } catch (e) {
      console.error('[ExecutiveDashboardPage] Failed to load lead calls:', e);
    } finally {
      this.drilldownCallsLoading = false;
      this.render();
    }
  }

  private async submitLeadNote(leadId: number, companyId: any, note: string): Promise<void> {
    if (!note.trim()) return;
    try {
      await apiService.post(`/crm/dashboard-v2/leads/${leadId}/notes?company_id=${companyId || ''}`, {
        note: note.trim(),
        is_private: false
      });
      this.drilldownNewNote = '';
      this.loadLeadNotes(leadId, companyId);
    } catch (e: any) {
      alert('Failed to save note: ' + (e.message || 'Server error'));
    }
  }

  private computeLeadDays(l: any): number | null {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const raw = l.solar_pipeline_status_updated_at || l.updated_at || l.submit_date || l.created_at;
    if (!raw) return null;
    const d = new Date(String(raw).slice(0, 10));
    d.setHours(0, 0, 0, 0);
    return isNaN(d.getTime()) ? null : Math.max(0, Math.floor((today.getTime() - d.getTime()) / 86400000));
  }

  private renderVsPrevBadge(curr: number, prev: number | undefined): string {
    if (prev === undefined || prev === null) return '<span style="color:#64748b;font-size:9.5px">—</span>';
    const diff = curr - prev;
    if (diff === 0) return '<span style="color:#94a3b8;font-size:9.5px;font-weight:600">0%</span>';
    const pct = prev > 0 ? ((diff / prev) * 100).toFixed(0) : (curr > 0 ? '+100' : '0');
    const isPos = diff > 0;
    const col = isPos ? '#34d399' : '#f87171';
    const icon = isPos ? '▲' : '▼';
    const sign = isPos ? '+' : '';
    return `<span style="color:${col};font-size:9.5px;font-weight:700;white-space:nowrap">${icon}${sign}${pct}%</span>`;
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     MAIN RENDER METHOD
     ═══════════════════════════════════════════════════════════════════════════ */
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

          <!-- Top KPI Cards (Web Parity) -->
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

          <!-- All 6 Authentic Tabs Bar (Full Parity with Web) -->
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
            <button class="nav-tab-btn ${this.activeTab === 'stagewise' ? 'active' : ''}" data-tab="stagewise" style="${this.getNavTabStyle(this.activeTab === 'stagewise')}">
              <i class="fas fa-table" style="margin-right:4px;"></i>Stage-Wise
            </button>
            <button class="nav-tab-btn ${this.activeTab === 'handlers' ? 'active' : ''}" data-tab="handlers" style="${this.getNavTabStyle(this.activeTab === 'handlers')}">
              <i class="fas fa-trophy" style="margin-right:4px;"></i>Handlers
            </button>
            <button class="nav-tab-btn ${this.activeTab === 'etc_batchwise' ? 'active' : ''}" data-tab="etc_batchwise" style="${this.getNavTabStyle(this.activeTab === 'etc_batchwise')}">
              <i class="fas fa-graduation-cap" style="margin-right:4px;"></i>ETC Batches
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
            ${this.activeTab === 'stagewise' ? this.renderStagewiseTab() : ''}
            ${this.activeTab === 'handlers' ? this.renderHandlersTab() : ''}
            ${this.activeTab === 'etc_batchwise' ? this.renderEtcBatchwiseTab() : ''}
          `}
        </div>

        <!-- Executive Drilldown Modal (Full Parity) -->
        ${this.renderExecutiveDrilldownModal()}
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
     TAB 1: OVERVIEW (5 Breakdowns matching Web + Stagewise shortcut)
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
              <div class="cat-card" data-cat="${name.toLowerCase().replace(/[^a-z0-9]/g, '-')}" style="background:#0f172a; border:1px solid #334155; border-radius:8px; padding:10px 12px; cursor:pointer;">
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

      <!-- 4. By Support Staff (Telecaller) Breakdown -->
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
                <div class="h-data-row" data-htype="support" data-hkey="${tc.emp_code || tc.name || ''}" data-hname="${name}" style="background:#0f172a; border:1px solid #334155; border-radius:8px; padding:8px 10px; display:flex; justify-content:space-between; align-items:center; cursor:pointer;">
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

      <!-- 5. By Field Staff (Showroom) Breakdown -->
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
                <div class="h-data-row" data-htype="field" data-hkey="${fs.emp_code || fs.name || ''}" data-hname="${name}" style="background:#0f172a; border:1px solid #334155; border-radius:8px; padding:8px 10px; display:flex; justify-content:space-between; align-items:center; cursor:pointer;">
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
     TAB 2: FULL 22-COLUMN MONTHLY & WEEKLY TRENDS MATRIX (Web Parity)
     ═══════════════════════════════════════════════════════════════════════════ */
  private renderTrendsTab(): string {
    const rows = this.activeTrendView === 'monthly' ? this.monthlyTrend : this.weeklyTrend;
    const title = this.activeTrendView === 'monthly' ? 'Monthly Trend — Last 12 Months' : 'Weekly Trend — Last 12 Weeks';
    const pt = this.activeTrendView;

    // Calculate totals across rows
    const trTot = rows.reduce((s, r) => s + (r.total || 0), 0);
    const trWon = rows.reduce((s, r) => s + (r.won || 0), 0);
    const trSub = rows.reduce((s, r) => s + (r.submitted || 0), 0);
    const trSubVal = rows.reduce((s, r) => s + (r.submitted_val || r.submitted_value || 0), 0);
    const trPipe = rows.reduce((s, r) => s + (r.pipeline || 0), 0);
    const trPipeVal = rows.reduce((s, r) => s + (r.pipeline_val || r.pipeline_value || 0), 0);
    const trEbChange = rows.reduce((s, r) => s + (r.eb_change || 0), 0);
    const trAtBank = rows.reduce((s, r) => s + (r.at_bank || 0), 0);
    const trFirstPmtRecd = rows.reduce((s, r) => s + (r.first_pmt_recd || 0), 0);
    const trInstPend = rows.reduce((s, r) => s + (r.inst_pending || 0), 0);
    const trNetMeterPend = rows.reduce((s, r) => s + (r.net_meter_pending || 0), 0);
    const trBalPend = rows.reduce((s, r) => s + (r.bal_pending || 0), 0);
    const trSubPend = rows.reduce((s, r) => s + (r.subsidy_pending || 0), 0);
    const trComp = rows.reduce((s, r) => s + (r.completed || 0), 0);
    const trCompVal = rows.reduce((s, r) => s + (r.comp_value || 0), 0);
    const trInst = rows.reduce((s, r) => s + (r.installed || 0), 0);

    const trSubWonPct = trWon > 0 ? ((trSub / trWon) * 100).toFixed(1) : '0.0';
    const trPipeSubPct = trSub > 0 ? ((trPipe / trSub) * 100).toFixed(1) : '0.0';
    const trCompSubPct = trSub > 0 ? ((trComp / trSub) * 100).toFixed(1) : '0.0';

    const cellClickAttr = (metric: string, colName: string, label: string) =>
      `class="trend-drilldown-cell" data-pt="${pt}" data-label="${label}" data-metric="${metric}" data-colname="${colName}" style="cursor:pointer; text-decoration:underline; text-decoration-color:rgba(255,255,255,0.3); padding:5px 6px; text-align:center; white-space:nowrap; border:1px solid #334155;"`;

    return `
      <div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:14px; margin-bottom:14px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
          <div>
            <div style="font-size:13px; font-weight:700; color:#ffffff; display:flex; align-items:center; gap:6px;">
              <i class="fas fa-chart-line" style="color:#38bdf8;"></i> ${title}
            </div>
            <div style="font-size:10px; color:#64748b; margin-top:2px;">Complete 22-column pipeline velocity &amp; conversion matrix</div>
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

        <div style="font-size:10px; color:#38bdf8; margin-bottom:8px; display:flex; align-items:center; gap:4px;">
          <i class="fas fa-hand-point-right"></i> Touch &amp; scroll horizontally to view all 22 columns. Tap any cell to view leads drilldown.
        </div>

        ${rows.length === 0 ? `
          <div style="text-align:center; color:#64748b; padding:24px; font-size:12px;">No trend data available</div>
        ` : `
          <div style="overflow-x:auto; width:100%; -webkit-overflow-scrolling:touch; border:1px solid #334155; border-radius:8px;">
            <table style="width:100%; border-collapse:collapse; font-size:10.5px; background:#0f172a; min-width:1200px;">
              <thead>
                <!-- Group Headers -->
                <tr style="background:#131d33; color:#94a3b8;">
                  <th rowspan="2" style="position:sticky; left:0; z-index:10; background:#131d33; padding:8px 10px; text-align:left; border:1px solid #334155; font-weight:700; min-width:110px;">PERIOD</th>
                  <th rowspan="2" style="padding:6px; text-align:center; border:1px solid #334155; font-weight:700;">OVERALL<br>LEADS</th>
                  <th colspan="5" style="text-align:center; background:rgba(16,185,129,0.15); color:#6ee7b7; font-weight:800; border:1px solid #334155; letter-spacing:0.5px; padding:5px;">WON VS SUBMITTED</th>
                  <th colspan="6" style="text-align:center; background:rgba(59,130,246,0.15); color:#93c5fd; font-weight:800; border:1px solid #334155; letter-spacing:0.5px; padding:5px;">PIPELINE</th>
                  <th colspan="10" style="text-align:center; background:rgba(99,102,241,0.15); color:#c7d2fe; font-weight:800; border:1px solid #334155; letter-spacing:0.5px; padding:5px;">PROGRESS</th>
                </tr>
                <!-- Subheader Columns -->
                <tr style="background:#1e293b; color:#cbd5e1; font-size:9px;">
                  <!-- WON VS SUBMITTED -->
                  <th style="padding:5px 4px; border:1px solid #334155; color:#34d399;">WON<br>(STATUS)</th>
                  <th style="padding:5px 4px; border:1px solid #334155; color:#10b981;">SUBMITTED<br>(STAGE)</th>
                  <th style="padding:5px 4px; border:1px solid #334155; color:#c084fc;">SUB/WON<br>%</th>
                  <th style="padding:5px 4px; border:1px solid #334155; color:#34d399;">SUB<br>VALUE</th>
                  <th style="padding:5px 4px; border:1px solid #334155; color:#38bdf8;">VS<br>PREV</th>

                  <!-- PIPELINE -->
                  <th style="padding:5px 4px; border:1px solid #334155; color:#60a5fa;">PIPELINE<br>(EXCL DEAD)</th>
                  <th style="padding:5px 4px; border:1px solid #334155; color:#c084fc;">PIPE/SUB<br>%</th>
                  <th style="padding:5px 4px; border:1px solid #334155; color:#60a5fa;">PIPE<br>VALUE</th>
                  <th style="padding:5px 4px; border:1px solid #334155; color:#38bdf8;">VS<br>PREV</th>
                  <th style="padding:5px 4px; border:1px solid #334155; color:#93c5fd;">EB<br>CHANGE</th>
                  <th style="padding:5px 4px; border:1px solid #334155; color:#93c5fd;">AT<br>BANK</th>

                  <!-- PROGRESS -->
                  <th style="padding:5px 4px; border:1px solid #334155; color:#34d399;">1ST PMT<br>RECD</th>
                  <th style="padding:5px 4px; border:1px solid #334155; color:#fb923c;">INST.<br>PENDING</th>
                  <th style="padding:5px 4px; border:1px solid #334155; color:#818cf8;">NET METER<br>PENDING</th>
                  <th style="padding:5px 4px; border:1px solid #334155; color:#f87171;">BAL.<br>PENDING</th>
                  <th style="padding:5px 4px; border:1px solid #334155; color:#c084fc;">SUBSIDY<br>PENDING</th>
                  <th style="padding:5px 4px; border:1px solid #334155; color:#a5b4fc;">COMPLETED</th>
                  <th style="padding:5px 4px; border:1px solid #334155; color:#c084fc;">COMP/<br>SUB%</th>
                  <th style="padding:5px 4px; border:1px solid #334155; color:#818cf8;">COMP<br>VALUE</th>
                  <th style="padding:5px 4px; border:1px solid #334155; color:#38bdf8;">VS<br>PREV</th>
                  <th style="padding:5px 4px; border:1px solid #334155; color:#34d399;">INSTALLED</th>
                </tr>
              </thead>
              <tbody>
                <!-- Total Row -->
                <tr style="background:#1e3a5f; color:white; font-weight:800; border-bottom:2px solid #38bdf8;">
                  <td style="position:sticky; left:0; z-index:9; background:#1e3a5f; padding:7px 10px; border:1px solid #334155; font-weight:800;">TOTAL</td>
                  <td ${cellClickAttr('total', 'Overall Leads', 'TOTAL')}>${this.fmtNum(trTot)}</td>
                  
                  <!-- Won vs Submitted Totals -->
                  <td ${cellClickAttr('won', 'Won (Status)', 'TOTAL')} style="background:#064e3b; color:#a7f3d0;">${this.fmtNum(trWon)}</td>
                  <td ${cellClickAttr('submitted', 'Submitted (Stage)', 'TOTAL')} style="background:#064e3b; color:#a7f3d0;">${this.fmtNum(trSub)}</td>
                  <td style="padding:5px 6px; text-align:center; background:#064e3b; color:#a7f3d0; border:1px solid #334155;">${trSubWonPct}%</td>
                  <td ${cellClickAttr('submitted', 'Submitted Value', 'TOTAL')} style="background:#064e3b; color:#a7f3d0;">${this.fmtVal(trSubVal)}</td>
                  <td style="padding:5px 6px; text-align:center; background:#064e3b; color:#a7f3d0; border:1px solid #334155;">—</td>

                  <!-- Pipeline Totals -->
                  <td ${cellClickAttr('pipeline', 'Pipeline (Excl Dead)', 'TOTAL')} style="background:#1e3a8a; color:#bfdbfe;">${this.fmtNum(trPipe)}</td>
                  <td style="padding:5px 6px; text-align:center; background:#1e3a8a; color:#bfdbfe; border:1px solid #334155;">${trPipeSubPct}%</td>
                  <td ${cellClickAttr('pipeline', 'Pipeline Value', 'TOTAL')} style="background:#1e3a8a; color:#bfdbfe;">${this.fmtVal(trPipeVal)}</td>
                  <td style="padding:5px 6px; text-align:center; background:#1e3a8a; color:#bfdbfe; border:1px solid #334155;">—</td>
                  <td ${cellClickAttr('eb_change', 'EB Change', 'TOTAL')} style="background:#1e3a8a; color:#bfdbfe;">${this.fmtNum(trEbChange)}</td>
                  <td ${cellClickAttr('at_bank', 'At Bank', 'TOTAL')} style="background:#1e3a8a; color:#bfdbfe;">${this.fmtNum(trAtBank)}</td>

                  <!-- Progress Totals -->
                  <td ${cellClickAttr('first_pmt_recd', '1st Payment Received', 'TOTAL')} style="background:#3b0764; color:#f5d0fe;">${this.fmtNum(trFirstPmtRecd)}</td>
                  <td ${cellClickAttr('inst_pending', 'Installation Pending', 'TOTAL')} style="background:#3b0764; color:#f5d0fe;">${this.fmtNum(trInstPend)}</td>
                  <td ${cellClickAttr('net_meter_pending', 'Net Meter Pending', 'TOTAL')} style="background:#3b0764; color:#f5d0fe;">${this.fmtNum(trNetMeterPend)}</td>
                  <td ${cellClickAttr('bal_pending', 'Balance Pending', 'TOTAL')} style="background:#3b0764; color:#f5d0fe;">${this.fmtNum(trBalPend)}</td>
                  <td ${cellClickAttr('subsidy_pending', 'Subsidy Pending', 'TOTAL')} style="background:#3b0764; color:#f5d0fe;">${this.fmtNum(trSubPend)}</td>
                  <td ${cellClickAttr('completed', 'Completed', 'TOTAL')} style="background:#3b0764; color:#f5d0fe;">${this.fmtNum(trComp)}</td>
                  <td style="padding:5px 6px; text-align:center; background:#3b0764; color:#f5d0fe; border:1px solid #334155;">${trCompSubPct}%</td>
                  <td ${cellClickAttr('completed', 'Completed Value', 'TOTAL')} style="background:#3b0764; color:#f5d0fe;">${this.fmtVal(trCompVal)}</td>
                  <td style="padding:5px 6px; text-align:center; background:#3b0764; color:#f5d0fe; border:1px solid #334155;">—</td>
                  <td ${cellClickAttr('installed', 'Installed', 'TOTAL')} style="background:#3b0764; color:#f5d0fe;">${this.fmtNum(trInst)}</td>
                </tr>

                <!-- Period Rows -->
                ${rows.map((r, i) => {
                  const label = r.label || r.period || r.month || r.week || 'Period';
                  const won = r.won || 0;
                  const sub = r.submitted || 0;
                  const subVal = r.submitted_val || r.submitted_value || 0;
                  const pipe = r.pipeline || 0;
                  const pipeVal = r.pipeline_val || r.pipeline_value || 0;
                  const ebChange = r.eb_change || 0;
                  const atBank = r.at_bank || 0;
                  const firstPmtRecd = r.first_pmt_recd || 0;
                  const instPend = r.inst_pending || 0;
                  const netMeterPend = r.net_meter_pending || 0;
                  const balPend = r.bal_pending || 0;
                  const subPend = r.subsidy_pending || 0;
                  const comp = r.completed || 0;
                  const compVal = r.comp_value || 0;
                  const installed = r.installed || 0;

                  const subWonPct = won > 0 ? ((sub / won) * 100).toFixed(1) : '—';
                  const pipeSubPct = sub > 0 ? ((pipe / sub) * 100).toFixed(1) : '—';
                  const compSubPct = sub > 0 ? ((comp / sub) * 100).toFixed(1) : '—';

                  const prevR = rows[i + 1];
                  const subVsPrev = prevR ? this.renderVsPrevBadge(sub, prevR.submitted) : '<span style="color:#64748b;font-size:9.5px">—</span>';
                  const pipeVsPrev = prevR ? this.renderVsPrevBadge(pipe, prevR.pipeline) : '<span style="color:#64748b;font-size:9.5px">—</span>';
                  const compVsPrev = prevR ? this.renderVsPrevBadge(comp, prevR.completed) : '<span style="color:#64748b;font-size:9.5px">—</span>';

                  const bg = i % 2 === 0 ? '#0f172a' : '#131e36';

                  return `
                    <tr style="background:${bg};">
                      <td style="position:sticky; left:0; z-index:8; background:${bg}; padding:6px 10px; border:1px solid #334155; font-weight:700; color:#38bdf8; white-space:nowrap;">${label}</td>
                      <td ${cellClickAttr('total', 'Overall Leads', label)}>${this.fmtNum(r.total)}</td>
                      
                      <!-- Won vs Submitted -->
                      <td ${cellClickAttr('won', 'Won (Status)', label)} style="color:#34d399; font-weight:700;">${this.fmtNum(won)}</td>
                      <td ${cellClickAttr('submitted', 'Submitted (Stage)', label)} style="color:#10b981; font-weight:700;">${this.fmtNum(sub)}</td>
                      <td style="padding:5px 6px; text-align:center; color:#c084fc; font-weight:600; border:1px solid #334155;">${subWonPct !== '—' ? subWonPct + '%' : '—'}</td>
                      <td ${cellClickAttr('submitted', 'Submitted Value', label)} style="color:#34d399;">${this.fmtVal(subVal)}</td>
                      <td style="padding:5px 6px; text-align:center; border:1px solid #334155;">${subVsPrev}</td>

                      <!-- Pipeline -->
                      <td ${cellClickAttr('pipeline', 'Pipeline (Excl Dead)', label)} style="color:#60a5fa; font-weight:700;">${this.fmtNum(pipe)}</td>
                      <td style="padding:5px 6px; text-align:center; color:#c084fc; font-weight:600; border:1px solid #334155;">${pipeSubPct !== '—' ? pipeSubPct + '%' : '—'}</td>
                      <td ${cellClickAttr('pipeline', 'Pipeline Value', label)} style="color:#60a5fa;">${this.fmtVal(pipeVal)}</td>
                      <td style="padding:5px 6px; text-align:center; border:1px solid #334155;">${pipeVsPrev}</td>
                      <td ${cellClickAttr('eb_change', 'EB Change', label)} style="color:#93c5fd;">${this.fmtNum(ebChange)}</td>
                      <td ${cellClickAttr('at_bank', 'At Bank', label)} style="color:#93c5fd;">${this.fmtNum(atBank)}</td>

                      <!-- Progress -->
                      <td ${cellClickAttr('first_pmt_recd', '1st Payment Received', label)} style="color:#34d399; font-weight:700;">${this.fmtNum(firstPmtRecd)}</td>
                      <td ${cellClickAttr('inst_pending', 'Installation Pending', label)} style="color:#fb923c;">${this.fmtNum(instPend)}</td>
                      <td ${cellClickAttr('net_meter_pending', 'Net Meter Pending', label)} style="color:#818cf8; font-weight:700;">${this.fmtNum(netMeterPend)}</td>
                      <td ${cellClickAttr('bal_pending', 'Balance Pending', label)} style="color:#f87171;">${this.fmtNum(balPend)}</td>
                      <td ${cellClickAttr('subsidy_pending', 'Subsidy Pending', label)} style="color:#c084fc;">${this.fmtNum(subPend)}</td>
                      <td ${cellClickAttr('completed', 'Completed', label)} style="color:#a5b4fc; font-weight:700;">${this.fmtNum(comp)}</td>
                      <td style="padding:5px 6px; text-align:center; color:#c084fc; font-weight:600; border:1px solid #334155;">${compSubPct !== '—' ? compSubPct + '%' : '—'}</td>
                      <td ${cellClickAttr('completed', 'Completed Value', label)} style="color:#818cf8;">${this.fmtVal(compVal)}</td>
                      <td style="padding:5px 6px; text-align:center; border:1px solid #334155;">${compVsPrev}</td>
                      <td ${cellClickAttr('installed', 'Installed', label)} style="color:#34d399; font-weight:700;">${this.fmtNum(installed)}</td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>
        `}
      </div>
    `;
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     TAB 3: EMPLOYEE WISE PERFORMANCE (Web Parity with Drilldowns)
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
                      <div class="emp-drilldown-cell" data-section="${this.empPerfActiveSection}" data-periodkey="TOTAL" data-empcode="${group.emp_code}" data-empname="${group.employee_name}" data-metric="overall_won" data-colname="Won Leads" style="font-size:14px; font-weight:800; color:#34d399; cursor:pointer; text-decoration:underline;">
                        ${s.overall_won} Won
                      </div>
                      <div class="emp-drilldown-cell" data-section="${this.empPerfActiveSection}" data-periodkey="TOTAL" data-empcode="${group.emp_code}" data-empname="${group.employee_name}" data-metric="overall_rev" data-colname="Overall Revenue" style="font-size:10.5px; font-weight:600; color:#818cf8; cursor:pointer; text-decoration:underline;">
                        ${this.fmtVal(s.overall_rev)}
                      </div>
                    </div>
                  </div>

                  <!-- Quick Stats Grid with Interactive Drilldowns -->
                  <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:6px; background:#1e293b; border-radius:6px; padding:8px; margin-bottom:8px; text-align:center;">
                    <div class="emp-drilldown-cell" data-section="${this.empPerfActiveSection}" data-periodkey="TOTAL" data-empcode="${group.emp_code}" data-empname="${group.employee_name}" data-metric="overall_new_leads" data-colname="Overall Leads" style="cursor:pointer;">
                      <div style="font-size:9px; color:#94a3b8;">Leads</div>
                      <div style="font-size:11px; font-weight:700; color:#f1f5f9; text-decoration:underline;">${s.overall_new_leads}</div>
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

                  <!-- Category Won Distribution Chips (Interactive Drilldowns) -->
                  <div style="display:flex; flex-wrap:wrap; gap:4px; margin-bottom:8px; font-size:9.5px;">
                    ${s.solar_won > 0 ? `
                      <span class="emp-drilldown-cell" data-section="${this.empPerfActiveSection}" data-periodkey="TOTAL" data-empcode="${group.emp_code}" data-empname="${group.employee_name}" data-metric="solar_won" data-colname="Solar Won" style="background:#064e3b; color:#6ee7b7; padding:2px 6px; border-radius:4px; cursor:pointer;">
                        ☀️ Solar: ${s.solar_won} (${this.fmtVal(s.solar_rev)})
                      </span>
                    ` : ''}
                    ${s.etc_won > 0 ? `
                      <span class="emp-drilldown-cell" data-section="${this.empPerfActiveSection}" data-periodkey="TOTAL" data-empcode="${group.emp_code}" data-empname="${group.employee_name}" data-metric="etc_won" data-colname="ETC Won" style="background:#3b0764; color:#d8b4fe; padding:2px 6px; border-radius:4px; cursor:pointer;">
                        🎓 ETC: ${s.etc_won} (${this.fmtVal(s.etc_rev)})
                      </span>
                    ` : ''}
                    ${s.b2b_won > 0 ? `
                      <span class="emp-drilldown-cell" data-section="${this.empPerfActiveSection}" data-periodkey="TOTAL" data-empcode="${group.emp_code}" data-empname="${group.employee_name}" data-metric="b2b_won" data-colname="EV B2B Won" style="background:#1e3a8a; color:#93c5fd; padding:2px 6px; border-radius:4px; cursor:pointer;">
                        ⚡ B2B: ${s.b2b_won} (${this.fmtVal(s.b2b_rev)})
                      </span>
                    ` : ''}
                    ${s.b2c_won > 0 ? `
                      <span class="emp-drilldown-cell" data-section="${this.empPerfActiveSection}" data-periodkey="TOTAL" data-empcode="${group.emp_code}" data-empname="${group.employee_name}" data-metric="b2c_won" data-colname="EV B2C Won" style="background:#701a75; color:#f5d0fe; padding:2px 6px; border-radius:4px; cursor:pointer;">
                        🛵 B2C: ${s.b2c_won}
                      </span>
                    ` : ''}
                    ${s.insurance_won > 0 ? `
                      <span class="emp-drilldown-cell" data-section="${this.empPerfActiveSection}" data-periodkey="TOTAL" data-empcode="${group.emp_code}" data-empname="${group.employee_name}" data-metric="insurance_won" data-colname="Insurance Won" style="background:#78350f; color:#fde68a; padding:2px 6px; border-radius:4px; cursor:pointer;">
                        🛡️ Ins: ${s.insurance_won}
                      </span>
                    ` : ''}
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
                            <span class="emp-drilldown-cell" data-section="${this.empPerfActiveSection}" data-periodkey="${r.period_key}" data-empcode="${group.emp_code}" data-empname="${group.employee_name}" data-metric="overall_new_leads" data-colname="Leads (${r.period_key})" style="color:#64748b; margin-left:6px; cursor:pointer; text-decoration:underline;">
                              (${r.overall_new_leads || 0} leads)
                            </span>
                          </div>
                          <div style="text-align:right;">
                            <span class="emp-drilldown-cell" data-section="${this.empPerfActiveSection}" data-periodkey="${r.period_key}" data-empcode="${group.emp_code}" data-empname="${group.employee_name}" data-metric="overall_won" data-colname="Won (${r.period_key})" style="color:#34d399; font-weight:700; cursor:pointer; text-decoration:underline;">
                              ${r.overall_won || 0} Won
                            </span>
                            <span class="emp-drilldown-cell" data-section="${this.empPerfActiveSection}" data-periodkey="${r.period_key}" data-empcode="${group.emp_code}" data-empname="${group.employee_name}" data-metric="overall_rev" data-colname="Revenue (${r.period_key})" style="color:#818cf8; margin-left:6px; cursor:pointer; text-decoration:underline;">
                              ${this.fmtVal(r.overall_rev)}
                            </span>
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
     TAB 4: STAGEWISE HANDLER BREAKDOWN TABLE (Web Parity with Side-by-Side Cnt & DV)
     ═══════════════════════════════════════════════════════════════════════════ */
  private renderStagewiseTab(): string {
    const { rows: allRows, labelCol, showCode } = this.buildSwRows();

    const q = this.stagewiseSearch.toLowerCase().trim();
    let rows = allRows.filter(r => {
      if (!q) return true;
      const n = (r.name || '').toLowerCase();
      const c = (r.code || '').toLowerCase();
      return n.includes(q) || c.includes(q);
    });

    const SW_COLS = [
      ...SOLAR_SW_COLS.map(c => ({ label: c.label, cntKey: c.key, dvKey: 'dv_' + c.key, color: c.color })),
      { label: 'Total', cntKey: 'total', dvKey: 'deal_value', color: '#38bdf8' },
      { label: 'Completed', cntKey: 'completed', dvKey: 'final_deal_value', color: '#10b981' },
    ];

    // Compute sums for total row
    const swTotals: Record<string, number> = {};
    SW_COLS.forEach(c => {
      swTotals[c.cntKey] = rows.reduce((s, r) => s + (r[c.cntKey] || 0), 0);
      swTotals[c.dvKey] = rows.reduce((s, r) => s + (r[c.dvKey] || 0), 0);
    });

    return `
      <div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:14px; margin-bottom:14px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
          <div>
            <div style="font-size:13px; font-weight:700; color:#ffffff; display:flex; align-items:center; gap:6px;">
              <i class="fas fa-table" style="color:#38bdf8;"></i> Stagewise Handler Breakdown
            </div>
            <div style="font-size:10px; color:#64748b; margin-top:2px;">Counts &amp; Values side-by-side across all solar stages</div>
          </div>
          <span style="font-size:11px; color:#94a3b8;">${rows.length} Handlers</span>
        </div>

        <!-- Handler Type Selector Chips -->
        <div style="display:flex; gap:6px; overflow-x:auto; padding-bottom:6px; margin-bottom:10px; -webkit-overflow-scrolling:touch;">
          <button class="sw-ht-btn ${this.activeHandlerType === 'ground' ? 'active' : ''}" data-ht="ground" style="${this.getHtChipStyle(this.activeHandlerType === 'ground')}">Ground Source</button>
          <button class="sw-ht-btn ${this.activeHandlerType === 'handler' ? 'active' : ''}" data-ht="handler" style="${this.getHtChipStyle(this.activeHandlerType === 'handler')}">Handler</button>
          <button class="sw-ht-btn ${this.activeHandlerType === 'support' ? 'active' : ''}" data-ht="support" style="${this.getHtChipStyle(this.activeHandlerType === 'support')}">Telecaller</button>
          <button class="sw-ht-btn ${this.activeHandlerType === 'field' ? 'active' : ''}" data-ht="field" style="${this.getHtChipStyle(this.activeHandlerType === 'field')}">Showroom</button>
          <button class="sw-ht-btn ${this.activeHandlerType === 'guru' ? 'active' : ''}" data-ht="guru" style="${this.getHtChipStyle(this.activeHandlerType === 'guru')}">Senior</button>
          <button class="sw-ht-btn ${this.activeHandlerType === 'zguru' ? 'active' : ''}" data-ht="zguru" style="${this.getHtChipStyle(this.activeHandlerType === 'zguru')}">Extended</button>
          <button class="sw-ht-btn ${this.activeHandlerType === 'adguru' ? 'active' : ''}" data-ht="adguru" style="${this.getHtChipStyle(this.activeHandlerType === 'adguru')}">On Ground Support</button>
          <button class="sw-ht-btn ${this.activeHandlerType === 'partner' ? 'active' : ''}" data-ht="partner" style="${this.getHtChipStyle(this.activeHandlerType === 'partner')}">Business Partner</button>
          <button class="sw-ht-btn ${this.activeHandlerType === 'source' ? 'active' : ''}" data-ht="source" style="${this.getHtChipStyle(this.activeHandlerType === 'source')}">Lead Source</button>
        </div>

        <!-- Search input -->
        <div style="margin-bottom:10px;">
          <input type="text" id="stagewiseSearchInput" placeholder="Search handler name or code..." value="${this.stagewiseSearch}" style="width:100%; background:#0f172a; border:1px solid #334155; color:#f1f5f9; border-radius:6px; padding:7px 10px; font-size:12px; outline:none;">
        </div>

        <div style="font-size:10px; color:#38bdf8; margin-bottom:8px; display:flex; align-items:center; gap:4px;">
          <i class="fas fa-hand-point-right"></i> Touch &amp; scroll horizontally to view stage metrics. Tap any handler row to drill down.
        </div>

        ${rows.length === 0 ? `
          <div style="text-align:center; color:#64748b; padding:24px; font-size:12px;">No handler data available for this type</div>
        ` : `
          <div style="overflow-x:auto; width:100%; -webkit-overflow-scrolling:touch; border:1px solid #334155; border-radius:8px;">
            <table style="width:100%; border-collapse:collapse; font-size:10px; background:#0f172a; min-width:1400px;">
              <thead>
                <!-- Group Row -->
                <tr style="background:#131d33; color:#94a3b8;">
                  <th rowspan="2" style="position:sticky; left:0; z-index:10; background:#131d33; padding:6px 8px; text-align:center; border:1px solid #334155; width:36px;">#</th>
                  <th rowspan="2" style="position:sticky; left:36px; z-index:10; background:#131d33; padding:6px 10px; text-align:left; border:1px solid #334155; min-width:140px;">${labelCol}</th>
                  ${SW_COLS.map(c => `
                    <th colspan="2" style="text-align:center; color:${c.color}; font-weight:800; border:1px solid #334155; padding:4px 6px; letter-spacing:0.3px;">${c.label}</th>
                  `).join('')}
                </tr>
                <!-- Subcolumn Row -->
                <tr style="background:#1e293b; color:#cbd5e1; font-size:9px;">
                  ${SW_COLS.map(c => `
                    <th style="padding:4px; text-align:center; border:1px solid #334155; color:${c.color};">Cnt</th>
                    <th style="padding:4px; text-align:right; border:1px solid #334155; color:${c.color};">DV</th>
                  `).join('')}
                </tr>
              </thead>
              <tbody>
                <!-- Total Row -->
                <tr style="background:#1e3a5f; color:white; font-weight:800; border-bottom:2px solid #38bdf8;">
                  <td style="position:sticky; left:0; z-index:9; background:#1e3a5f; text-align:center; padding:6px; border:1px solid #334155;">Σ</td>
                  <td style="position:sticky; left:36px; z-index:9; background:#1e3a5f; padding:6px 10px; border:1px solid #334155;">TOTAL</td>
                  ${SW_COLS.map(c => {
                    const cnt = swTotals[c.cntKey] || 0;
                    const dv = swTotals[c.dvKey] || 0;
                    return `
                      <td style="padding:5px 6px; text-align:center; border:1px solid #334155; font-weight:800;">${cnt > 0 ? this.fmtNum(cnt) : '—'}</td>
                      <td style="padding:5px 6px; text-align:right; border:1px solid #334155; font-weight:700; white-space:nowrap;">${dv > 0 ? this.fmtVal(dv) : '—'}</td>
                    `;
                  }).join('')}
                </tr>

                <!-- Data Rows -->
                ${rows.map((r, i) => {
                  const medal = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `${i + 1}`;
                  const bg = i % 2 === 0 ? '#0f172a' : '#131e36';
                  const hKey = this.activeHandlerType === 'source' ? (r.name || '') : (r.code || r.name || '');

                  return `
                    <tr class="h-data-row" data-htype="${this.activeHandlerType}" data-hkey="${hKey}" data-hname="${r.name || ''}" data-hext="${r.type || ''}" style="background:${bg}; cursor:pointer;">
                      <td style="position:sticky; left:0; z-index:8; background:${bg}; text-align:center; padding:6px; border:1px solid #334155; font-weight:700; color:#fbbf24;">${medal}</td>
                      <td style="position:sticky; left:36px; z-index:8; background:${bg}; padding:6px 10px; border:1px solid #334155; min-width:140px;">
                        <div style="font-weight:700; color:#f1f5f9; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:140px;">${r.name || '—'}</div>
                        ${showCode && r.code ? `<div style="font-size:9px; color:#38bdf8;">${r.code}</div>` : ''}
                      </td>
                      ${SW_COLS.map(c => {
                        const cnt = r[c.cntKey] || 0;
                        const dv = r[c.dvKey] || 0;
                        return `
                          <td style="padding:5px 6px; text-align:center; border:1px solid #334155; ${cnt > 0 ? 'font-weight:700; color:#ffffff;' : 'color:#475569;'}">${cnt > 0 ? this.fmtNum(cnt) : '—'}</td>
                          <td style="padding:5px 6px; text-align:right; border:1px solid #334155; white-space:nowrap; ${dv > 0 ? 'font-weight:600; color:#cbd5e1;' : 'color:#475569;'}">${dv > 0 ? this.fmtVal(dv) : '—'}</td>
                        `;
                      }).join('')}
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>
        `}
      </div>
    `;
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     TAB 5: HANDLERS LEADERBOARD (Web Parity with Handler Types)
     ═══════════════════════════════════════════════════════════════════════════ */
  private renderHandlersTab(): string {
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
    } else if (this.activeHandlerType === 'adguru') {
      handlerList = this.rawLeadData.by_adi_guru || [];
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
      const c = (h.emp_code || h.code || '').toLowerCase();
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
          <button class="ht-type-btn ${this.activeHandlerType === 'adguru' ? 'active' : ''}" data-ht="adguru" style="${this.getHtChipStyle(this.activeHandlerType === 'adguru')}">On Ground Support</button>
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
              const code = (h.emp_code || h.code) ? `(${h.emp_code || h.code})` : '';
              const tot = h.total || h.count || 0;
              const won = h.won || 0;
              const winPct = tot > 0 ? ((won / tot) * 100).toFixed(0) : '0';
              const dv = h.won_deal_value || h.deal_value || 0;
              const medal = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `${i + 1}.`;
              const hKey = this.activeHandlerType === 'source' ? (h.name || h.source || '') : (h.emp_code || h.code || h.name || '');

              return `
                <div class="h-data-row" data-htype="${this.activeHandlerType}" data-hkey="${hKey}" data-hname="${name}" data-hext="${h.type || ''}" style="background:#0f172a; border:1px solid #334155; border-radius:8px; padding:10px 12px; display:flex; justify-content:space-between; align-items:center; cursor:pointer;">
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

  /* ═══════════════════════════════════════════════════════════════════════════
     TAB 6: ETC STUDENTS BATCH WISE (Web Parity with Softphone & Location)
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

    const q = this.etcBatchSearch.toLowerCase().trim();
    const batches = rawBatches.filter(b => {
      if (!q) return true;
      const matchBatch = (b.batch_no || '').toLowerCase().includes(q) || (b.month || '').toLowerCase().includes(q);
      const matchStudents = (b.students || []).some(s =>
        (s.name || '').toLowerCase().includes(q) ||
        (s.phone || '').includes(q) ||
        (s.student_id || '').toLowerCase().includes(q) ||
        (s.registration_id || '').toLowerCase().includes(q) ||
        (s.district || '').toLowerCase().includes(q) ||
        (s.state || '').toLowerCase().includes(q)
      );
      return matchBatch || matchStudents;
    });

    return `
      <!-- 6 ETC KPI Cards -->
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
          <input type="text" id="etcBatchSearchInput" placeholder="Search batch, student, phone or district..." value="${this.etcBatchSearch}" style="flex:1; background:#0f172a; border:1px solid #334155; color:#f1f5f9; border-radius:6px; padding:7px 10px; font-size:12px; outline:none;">
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
                    ${students.map(s => {
                      const cleanPhone = (s.phone || '').replace(/\D/g, '');
                      const locationStr = [s.district, s.state].filter(Boolean).join(', ') || '—';

                      return `
                        <div style="background:#131d33; border:1px solid #1e293b; border-radius:6px; padding:8px 10px;">
                          <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:4px;">
                            <div>
                              <div style="font-size:11.5px; font-weight:600; color:#f1f5f9;">${s.name || 'Student'}</div>
                              <div style="font-size:9.5px; color:#64748b;">${s.student_id || s.registration_id || 'ID'} · ${s.course_type || 'Training'}</div>
                            </div>
                            <span style="font-size:9px; font-weight:700; padding:2px 6px; border-radius:4px; ${s.training_stage === 'training_completed' ? 'background:#064e3b; color:#6ee7b7;' : 'background:#1e3a8a; color:#93c5fd;'}">
                              ${s.training_stage === 'training_completed' ? 'COMPLETED' : 'TRAINING'}
                            </span>
                          </div>

                          <!-- Student Location & Phone with Direct Softphone Trigger -->
                          <div style="display:flex; justify-content:space-between; align-items:center; margin-top:4px; padding:4px 0; border-top:1px dashed #1e293b;">
                            <div style="font-size:10px; color:#94a3b8;">
                              <i class="fas fa-map-marker-alt" style="color:#ef4444; margin-right:3px;"></i> ${locationStr}
                            </div>
                            <div style="display:flex; gap:6px; align-items:center;">
                              ${s.phone ? `
                                <button class="call-student-btn" data-phone="${s.phone}" data-name="${s.name || ''}" data-studentid="${s.id || ''}" style="background:#059669; color:white; border:none; border-radius:4px; padding:3px 8px; font-size:9.5px; font-weight:700; cursor:pointer; display:flex; align-items:center; gap:4px;">
                                  <i class="fas fa-phone-alt"></i> Call
                                </button>
                                ${cleanPhone ? `
                                  <a href="https://wa.me/91${cleanPhone}" target="_blank" style="background:#16a34a; color:white; text-decoration:none; border-radius:4px; padding:3px 8px; font-size:9.5px; font-weight:700; display:flex; align-items:center; gap:4px;">
                                    <i class="fab fa-whatsapp"></i> Chat
                                  </a>
                                ` : ''}
                              ` : ''}
                            </div>
                          </div>

                          <div style="display:flex; justify-content:space-between; font-size:10px; margin-top:4px;">
                            <span style="color:#94a3b8;">Fee: ${this.fmtVal(s.deal_value)}</span>
                            <span style="color:#34d399; font-weight:600;">Paid: ${this.fmtVal(s.received)}</span>
                            <span style="color:#f87171; font-weight:600;">Bal: ${this.fmtVal(s.balance)}</span>
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
      `}
    `;
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     EXECUTIVE DRILLDOWN MODAL OVERLAY (Full Parity)
     ═══════════════════════════════════════════════════════════════════════════ */
  private renderExecutiveDrilldownModal(): string {
    if (!this.isDrilldownOpen) return '';

    const q = this.drilldownFilterText.toLowerCase().trim();
    const leads = this.drilldownLeads.filter(l => {
      if (!q) return true;
      const name = (l.lead_name || l.name || '').toLowerCase();
      const phone = (l.phone_raw || l.phone || '').toLowerCase();
      const city = (l.city || l.district || '').toLowerCase();
      const area = (l.area || '').toLowerCase();
      const stage = (l.solar_pipeline_status || l.status || '').toLowerCase();
      return name.includes(q) || phone.includes(q) || city.includes(q) || area.includes(q) || stage.includes(q);
    });

    const isFs = this.isFullscreenDrilldown;

    return `
      <div id="execDrilldownOverlay" style="position:fixed; inset:0; background:rgba(0,0,0,0.8); z-index:9999; display:flex; align-items:${isFs ? 'stretch' : 'flex-end'}; justify-content:center; padding:${isFs ? '0' : '0 0 10px 0'};">
        <div style="background:#0f172a; width:100%; max-width:${isFs ? '100vw' : '640px'}; height:${isFs ? '100vh' : '90vh'}; border-radius:${isFs ? '0' : '16px 16px 0 0'}; display:flex; flex-direction:column; overflow:hidden; border:1px solid #334155; box-shadow:0 -10px 40px rgba(0,0,0,0.6);">
          
          <!-- Modal Header -->
          <div style="background:linear-gradient(135deg, #1e3a5f, #0f2440); padding:12px 16px; display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #334155;">
            <div>
              <div style="color:#ffffff; font-weight:800; font-size:13.5px; display:flex; align-items:center; gap:6px;">
                <i class="fas fa-list-ul" style="color:#38bdf8;"></i> ${this.drilldownTitle}
              </div>
              <div style="font-size:10.5px; color:#94a3b8; margin-top:2px;">
                ${this.drilldownSubtitle}
              </div>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
              <button id="execFsToggleBtn" style="background:rgba(255,255,255,0.15); border:1px solid rgba(255,255,255,0.3); color:#ffffff; font-size:11px; padding:4px 8px; border-radius:4px; cursor:pointer;">
                <i class="fas ${isFs ? 'fa-compress' : 'fa-expand'}"></i>
              </button>
              <button id="closeExecDrilldownBtn" style="background:transparent; border:none; color:#f1f5f9; font-size:18px; cursor:pointer; padding:4px;">
                <i class="fas fa-times"></i>
              </button>
            </div>
          </div>

          <!-- Local search input inside modal -->
          <div style="padding:8px 12px; background:#1e293b; border-bottom:1px solid #334155;">
            <input type="text" id="execDrilldownSearchInput" placeholder="Filter leads by name, phone, area, city or stage..." value="${this.drilldownFilterText}" style="width:100%; background:#0f172a; border:1px solid #334155; color:#f1f5f9; border-radius:6px; padding:6px 10px; font-size:11.5px; outline:none;">
          </div>

          <!-- Modal Body / Leads List -->
          <div style="flex:1; overflow-y:auto; padding:12px; -webkit-overflow-scrolling:touch; display:flex; flex-direction:column; gap:10px;">
            ${this.drilldownLoading ? `
              <div style="text-align:center; padding:48px 16px;">
                <i class="fas fa-circle-notch fa-spin" style="font-size:24px; color:#38bdf8; margin-bottom:8px;"></i>
                <div style="color:#94a3b8; font-size:12px;">Retrieving detailed lead records...</div>
              </div>
            ` : leads.length === 0 ? `
              <div style="text-align:center; padding:40px 16px; color:#64748b; font-size:12px;">
                <i class="fas fa-inbox" style="font-size:28px; margin-bottom:8px; display:block;"></i>
                No leads found matching current criteria
              </div>
            ` : leads.map((l, i) => {
              const leadName = l.lead_name || l.name || 'Unnamed Lead';
              const cleanPhone = (l.phone_raw || l.phone || '').replace(/\D/g, '');
              const phoneDisplay = l.phone_raw || l.phone || '—';
              const categoryName = l.category_name || l.category || 'General';
              const stageName = (l.solar_pipeline_status || l.status || 'new').replace(/_/g, ' ').toUpperCase();
              const days = this.computeLeadDays(l);
              const daysBadge = days !== null ? `
                <span style="background:rgba(234,179,8,0.15); color:#fef08a; padding:1px 6px; border-radius:10px; font-size:9.5px; font-weight:700;">
                  ${days}d in stage
                </span>
              ` : '';

              const locStr = [l.area, l.city || l.district].filter(Boolean).join(', ');
              const mapsQuery = encodeURIComponent([l.area, l.city || l.district, l.state].filter(Boolean).join(', '));
              const mapsUrl = l.latitude && l.longitude
                ? `https://maps.google.com/?q=${l.latitude},${l.longitude}`
                : `https://maps.google.com/?q=${mapsQuery}`;

              const isSelected = this.drilldownSelectedLead && this.drilldownSelectedLead.id === l.id;

              return `
                <div style="background:#1e293b; border:1px solid ${isSelected ? '#38bdf8' : '#334155'}; border-radius:10px; padding:10px 12px; transition:border 0.2s;">
                  <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px;">
                    <div>
                      <div style="display:flex; align-items:center; gap:6px;">
                        <span style="font-size:10px; font-weight:800; color:#94a3b8;">#${i + 1}</span>
                        <div style="font-size:12.5px; font-weight:700; color:#f1f5f9;">${leadName}</div>
                      </div>
                      <div style="display:flex; align-items:center; gap:6px; margin-top:2px;">
                        <span style="font-size:9.5px; background:#0f172a; color:#38bdf8; padding:1px 6px; border-radius:4px; font-weight:600;">
                          ${categoryName}
                        </span>
                        <span style="font-size:9.5px; background:#064e3b; color:#6ee7b7; padding:1px 6px; border-radius:4px; font-weight:700;">
                          ${stageName}
                        </span>
                        ${daysBadge}
                      </div>
                    </div>
                    <div style="text-align:right;">
                      <div style="font-size:11px; font-weight:700; color:#f87171;">Bal: ${this.fmtVal(l.balance_pending || l.pending_balance)}</div>
                      <div style="font-size:10px; color:#818cf8;">Val: ${this.fmtVal(l.deal_value || l.won_deal_value)}</div>
                    </div>
                  </div>

                  <!-- Phone & Direct Softphone Dialer -->
                  <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px; padding:6px 0; border-top:1px dashed #334155;">
                    <div style="font-size:11px; color:#cbd5e1; font-weight:600;">
                      <i class="fas fa-phone-alt" style="color:#10b981; margin-right:4px;"></i> ${phoneDisplay}
                    </div>
                    <div style="display:flex; gap:6px;">
                      ${phoneDisplay !== '—' ? `
                        <button class="ed-call-lead-btn" data-phone="${phoneDisplay}" data-name="${leadName}" data-leadid="${l.id || ''}" style="background:#059669; color:white; border:none; border-radius:4px; padding:4px 8px; font-size:10px; font-weight:700; cursor:pointer; display:flex; align-items:center; gap:4px;">
                          <i class="fas fa-phone-alt"></i> Softphone
                        </button>
                        ${cleanPhone ? `
                          <a href="https://wa.me/91${cleanPhone}" target="_blank" style="background:#16a34a; color:white; text-decoration:none; border-radius:4px; padding:4px 8px; font-size:10px; font-weight:700; display:flex; align-items:center; gap:4px;">
                            <i class="fab fa-whatsapp"></i> Chat
                          </a>
                        ` : ''}
                      ` : ''}
                    </div>
                  </div>

                  <!-- Location & Maps -->
                  <div style="display:flex; justify-content:space-between; align-items:center; margin-top:4px; font-size:10.5px; color:#94a3b8;">
                    <div>
                      <i class="fas fa-map-marker-alt" style="color:#ef4444; margin-right:4px;"></i> ${locStr || 'Location not specified'}
                    </div>
                    ${locStr ? `
                      <a href="${mapsUrl}" target="_blank" style="color:#38bdf8; text-decoration:none; font-weight:600; display:flex; align-items:center; gap:3px;">
                        <i class="fas fa-external-link-alt" style="font-size:9px;"></i> Map
                      </a>
                    ` : ''}
                  </div>

                  <!-- Assigned Staff Details -->
                  <div style="display:flex; flex-wrap:wrap; gap:8px; font-size:9.5px; color:#64748b; margin-top:6px; padding-top:4px; border-top:1px dashed #334155;">
                    ${l.ground_source_name ? `<span>Ground: <strong style="color:#94a3b8;">${l.ground_source_name}</strong></span>` : ''}
                    ${l.telecaller_name ? `<span>Telecaller: <strong style="color:#94a3b8;">${l.telecaller_name}</strong></span>` : ''}
                    ${l.field_staff_name ? `<span>Showroom: <strong style="color:#94a3b8;">${l.field_staff_name}</strong></span>` : ''}
                  </div>

                  <!-- Notes & History Expand Button -->
                  <div style="margin-top:8px;">
                    <button class="ed-toggle-notes-btn" data-leadid="${l.id || ''}" data-companyid="${l.company_id || ''}" style="width:100%; background:#0f172a; border:1px solid #334155; color:#38bdf8; border-radius:6px; padding:5px; font-size:10.5px; font-weight:600; cursor:pointer; display:flex; justify-content:center; align-items:center; gap:4px;">
                      <i class="fas fa-sticky-note"></i> ${isSelected ? 'Hide Notes & History' : 'View Notes & Call History'}
                    </button>
                  </div>

                  <!-- Expanded Notes & Call History Drawer -->
                  ${isSelected ? `
                    <div style="margin-top:8px; background:#0f172a; border-radius:6px; padding:8px; border:1px solid #334155;">
                      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <span style="font-size:11px; font-weight:700; color:#ffffff;">Notes for ${leadName}</span>
                        <button class="ed-toggle-calls-btn" data-leadid="${l.id || ''}" style="background:transparent; border:none; color:#38bdf8; font-size:10.5px; cursor:pointer; font-weight:600;">
                          ${this.drilldownCallsOpen ? '▲ Hide Calls' : '📞 Call History'}
                        </button>
                      </div>

                      <!-- Call History Accordion -->
                      ${this.drilldownCallsOpen ? `
                        <div style="background:#131d33; border-radius:6px; padding:6px; margin-bottom:8px; border:1px solid #1e293b;">
                          <div style="font-size:10px; font-weight:700; color:#94a3b8; text-transform:uppercase; margin-bottom:4px;">Call Records (${this.drilldownCalls.length})</div>
                          ${this.drilldownCallsLoading ? `
                            <div style="font-size:10.5px; color:#64748b; text-align:center; padding:6px;"><i class="fas fa-spinner fa-spin"></i> Loading calls…</div>
                          ` : this.drilldownCalls.length === 0 ? `
                            <div style="font-size:10.5px; color:#64748b; padding:4px;">No past call records</div>
                          ` : this.drilldownCalls.map(c => `
                            <div style="font-size:10px; border-bottom:1px solid #1e293b; padding:4px 0; display:flex; justify-content:space-between;">
                              <div>
                                <span style="font-weight:700; color:#38bdf8;">${(c.call_type || 'OUTGOING').toUpperCase()}</span>
                                <span style="color:#94a3b8; margin-left:4px;">${c.staff_name || 'Agent'}</span>
                              </div>
                              <span style="color:#64748b;">${c.duration_seconds || 0}s</span>
                            </div>
                          `).join('')}
                        </div>
                      ` : ''}

                      <!-- Notes List -->
                      ${this.drilldownNotesLoading ? `
                        <div style="text-align:center; color:#64748b; padding:8px; font-size:11px;"><i class="fas fa-spinner fa-spin"></i> Loading comments…</div>
                      ` : this.drilldownNotes.length === 0 ? `
                        <div style="color:#64748b; font-size:10.5px; padding:6px; text-align:center;">No comments yet for this lead</div>
                      ` : `
                        <div style="display:flex; flex-direction:column; gap:4px; max-height:140px; overflow-y:auto; margin-bottom:6px;">
                          ${this.drilldownNotes.map(n => `
                            <div style="background:#131d33; padding:5px 8px; border-radius:4px; font-size:10.5px;">
                              <div style="font-size:9px; color:#64748b;">${(n.created_at || '').slice(0, 16).replace('T', ' ')} · ${n.created_by_id || 'Staff'}</div>
                              <div style="color:#e2e8f0; margin-top:2px;">${n.note || ''}</div>
                            </div>
                          `).join('')}
                        </div>
                      `}

                      <!-- Add New Note Form -->
                      <div style="display:flex; gap:6px; margin-top:6px;">
                        <input type="text" id="edNewNoteInput" placeholder="Add note / comment..." value="${this.drilldownNewNote}" style="flex:1; background:#131d33; border:1px solid #334155; color:#f1f5f9; border-radius:4px; padding:5px 8px; font-size:11px; outline:none;">
                        <button class="ed-submit-note-btn" data-leadid="${l.id || ''}" data-companyid="${l.company_id || ''}" style="background:#2563eb; color:white; border:none; border-radius:4px; padding:5px 10px; font-size:10.5px; font-weight:700; cursor:pointer;">
                          Post
                        </button>
                      </div>
                    </div>
                  ` : ''}
                </div>
              `;
            })}
          </div>
        </div>
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
     EVENT LISTENERS ATTACHMENT
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

    // Trend matrix cell click -> Drilldown
    this.container.querySelectorAll('.trend-drilldown-cell').forEach(cell => {
      cell.addEventListener('click', (e) => {
        const target = e.currentTarget as HTMLElement;
        const pt = target.dataset.pt || 'monthly';
        const label = target.dataset.label || '';
        const metric = target.dataset.metric || '';
        const colName = target.dataset.colname || '';
        if (label && metric) {
          this.openTrendDrillDown(pt, label, metric, colName);
        }
      });
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

    // Employee Performance cell click -> Drilldown
    this.container.querySelectorAll('.emp-drilldown-cell').forEach(cell => {
      cell.addEventListener('click', (e) => {
        e.stopPropagation();
        const target = e.currentTarget as HTMLElement;
        const section = target.dataset.section || 'monthly';
        const periodKey = target.dataset.periodkey || 'TOTAL';
        const empCode = target.dataset.empcode || '';
        const empName = target.dataset.empname || '';
        const metric = target.dataset.metric || '';
        const colName = target.dataset.colname || '';
        if (metric) {
          this.openEmpPerfDrillDown(section, periodKey, empCode, empName, metric, colName);
        }
      });
    });

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

    // Stagewise Handler Type buttons
    this.container.querySelectorAll('.sw-ht-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const target = e.currentTarget as HTMLElement;
        const ht = target.dataset.ht as any;
        if (ht) {
          this.activeHandlerType = ht;
          this.render();
        }
      });
    });

    // Stagewise search input
    const swSearchEl = document.getElementById('stagewiseSearchInput') as HTMLInputElement;
    if (swSearchEl) {
      swSearchEl.addEventListener('input', () => {
        this.stagewiseSearch = swSearchEl.value;
        this.render();
        const newSearch = document.getElementById('stagewiseSearchInput') as HTMLInputElement;
        if (newSearch) {
          newSearch.focus();
          newSearch.selectionStart = newSearch.selectionEnd = newSearch.value.length;
        }
      });
    }

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

    // Call Student button (Softphone Trigger)
    this.container.querySelectorAll('.call-student-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const target = e.currentTarget as HTMLElement;
        const phone = target.dataset.phone;
        const name = target.dataset.name;
        const studentId = target.dataset.studentid;
        if (phone) {
          callController.openCallDialer({
            phoneNumber: phone,
            name: name || 'Student Contact',
            entityId: studentId ? Number(studentId) : undefined,
            entityType: 'student',
            autoStart: true
          });
        }
      });
    });

    // Handler Type buttons (Leaderboard)
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

    // Handler row click -> Drilldown
    this.container.querySelectorAll('.h-data-row').forEach(row => {
      row.addEventListener('click', (e) => {
        const target = e.currentTarget as HTMLElement;
        const htype = target.dataset.htype;
        const hkey = target.dataset.hkey;
        const hname = target.dataset.hname;
        const hext = target.dataset.hext;
        if (htype && hkey) {
          this.openExecDrillDown(htype, hkey, hname || hkey, hext);
        }
      });
    });

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

    /* ── Executive Drilldown Modal Event Handlers ── */
    document.getElementById('closeExecDrilldownBtn')?.addEventListener('click', () => {
      this.isDrilldownOpen = false;
      this.drilldownSelectedLead = null;
      this.render();
    });

    document.getElementById('execFsToggleBtn')?.addEventListener('click', () => {
      this.isFullscreenDrilldown = !this.isFullscreenDrilldown;
      this.render();
    });

    const edSearchEl = document.getElementById('execDrilldownSearchInput') as HTMLInputElement;
    if (edSearchEl) {
      edSearchEl.addEventListener('input', () => {
        this.drilldownFilterText = edSearchEl.value;
        this.render();
        const newEl = document.getElementById('execDrilldownSearchInput') as HTMLInputElement;
        if (newEl) {
          newEl.focus();
          newEl.selectionStart = newEl.selectionEnd = newEl.value.length;
        }
      });
    }

    // Call Lead via Softphone
    this.container.querySelectorAll('.ed-call-lead-btn').forEach(btn => {
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

    // Toggle Lead Notes
    this.container.querySelectorAll('.ed-toggle-notes-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const target = e.currentTarget as HTMLElement;
        const leadId = target.dataset.leadid ? Number(target.dataset.leadid) : null;
        const companyId = target.dataset.companyid;

        if (this.drilldownSelectedLead && this.drilldownSelectedLead.id === leadId) {
          this.drilldownSelectedLead = null;
          this.drilldownCallsOpen = false;
          this.render();
        } else if (leadId) {
          this.drilldownSelectedLead = { id: leadId, company_id: companyId };
          this.drilldownCallsOpen = false;
          this.loadLeadNotes(leadId, companyId);
        }
      });
    });

    // Toggle Lead Calls
    this.container.querySelectorAll('.ed-toggle-calls-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const target = e.currentTarget as HTMLElement;
        const leadId = target.dataset.leadid ? Number(target.dataset.leadid) : null;
        if (leadId) {
          this.drilldownCallsOpen = !this.drilldownCallsOpen;
          if (this.drilldownCallsOpen) {
            this.loadLeadCalls(leadId);
          } else {
            this.render();
          }
        }
      });
    });

    // Note Input State
    const noteInputEl = document.getElementById('edNewNoteInput') as HTMLInputElement;
    if (noteInputEl) {
      noteInputEl.addEventListener('input', () => {
        this.drilldownNewNote = noteInputEl.value;
      });
    }

    // Submit Note
    this.container.querySelectorAll('.ed-submit-note-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const target = e.currentTarget as HTMLElement;
        const leadId = target.dataset.leadid ? Number(target.dataset.leadid) : null;
        const companyId = target.dataset.companyid;
        const val = this.drilldownNewNote;
        if (leadId && val.trim()) {
          this.submitLeadNote(leadId, companyId, val);
        }
      });
    });
  }
}
