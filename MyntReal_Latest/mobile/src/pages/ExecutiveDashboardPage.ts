/**
 * Executive Dashboard Page (Mobile View)
 * DC Protocol: DC_MOBILE_STAFF_EXEC_DASH_001
 * Comprehensive mobile interface for Executive Dashboard & Leadership Analytics
 * Parity with web staff_executive_dashboard.html
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
  count?: number;
  total?: number;
  won?: number;
  deal_value?: number;
  won_deal_value?: number;
  win_rate?: number;
  [key: string]: any;
}

interface HandlerItem {
  id?: number;
  name?: string;
  emp_code?: string;
  role?: string;
  total?: number;
  won?: number;
  in_progress?: number;
  lost?: number;
  deal_value?: number;
  won_deal_value?: number;
  win_rate?: number;
}

export class ExecutiveDashboardPage {
  private container: HTMLElement;
  private loading: boolean = true;
  private activePreset: 'today' | 'this_week' | 'this_month' | 'overall' = 'overall';
  private fromDate: string = '';
  private toDate: string = '';
  private summary: AnalyticsSummary = {};
  private byCategory: BreakdownItem[] = [];
  private byStatus: BreakdownItem[] = [];
  private bySource: BreakdownItem[] = [];
  private handlers: HandlerItem[] = [];
  private activeTab: 'overview' | 'categories' | 'handlers' = 'overview';

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

  private setPreset(preset: 'today' | 'this_week' | 'this_month' | 'overall'): void {
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
    } else if (preset === 'this_month') {
      const s = new Date(today.getFullYear(), today.getMonth(), 1);
      this.fromDate = this.fmtDateISO(s);
      this.toDate = todayStr;
    }
    this.loadData();
  }

  private async loadData(): Promise<void> {
    this.loading = true;
    this.render();

    try {
      const p = new URLSearchParams();
      if (this.fromDate) p.set('created_from', this.fromDate);
      if (this.toDate) p.set('created_to', this.toDate);

      const resp = await apiService.get<any>(`/crm/lead-analytics?${p.toString()}`);
      if (resp && (resp.success !== false)) {
        const d = resp.data || resp;
        this.summary = d.summary || {};
        this.byCategory = d.by_category || [];
        this.byStatus = d.by_status || [];
        this.bySource = d.by_source || [];
        this.handlers = d.handlers || [];
      }
    } catch (e) {
      console.error('[ExecutiveDashboardPage] Failed to load lead analytics:', e);
    } finally {
      this.loading = false;
      this.render();
    }
  }

  private render(): void {
    const total = this.summary.total_leads || 0;
    const won = this.summary.won_leads || 0;
    const inProg = this.summary.in_progress_leads || 0;
    const lost = this.summary.lost_leads || 0;
    const winRate = total > 0 ? ((won / total) * 100).toFixed(1) : '0';

    this.container.innerHTML = `
      <div class="executive-dashboard-container" style="background:#0b1329; min-height:100vh; padding-bottom:80px; color:#f1f5f9; font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;">
        ${PageHeader.render({
          title: 'Executive Dashboard',
          subtitle: 'Leadership & Workflow Analytics',
          showMenu: true,
          showBack: true
        })}

        <div style="padding:14px;">
          <!-- Quick Presets -->
          <div style="display:flex; gap:6px; overflow-x:auto; padding-bottom:4px; margin-bottom:12px; -webkit-overflow-scrolling:touch;">
            <button class="preset-btn ${this.activePreset === 'today' ? 'active' : ''}" data-preset="today" style="${this.getPresetStyle(this.activePreset === 'today')}">Today</button>
            <button class="preset-btn ${this.activePreset === 'this_week' ? 'active' : ''}" data-preset="this_week" style="${this.getPresetStyle(this.activePreset === 'this_week')}">This Week</button>
            <button class="preset-btn ${this.activePreset === 'this_month' ? 'active' : ''}" data-preset="this_month" style="${this.getPresetStyle(this.activePreset === 'this_month')}">This Month</button>
            <button class="preset-btn ${this.activePreset === 'overall' ? 'active' : ''}" data-preset="overall" style="${this.getPresetStyle(this.activePreset === 'overall')}">Overall (All)</button>
          </div>

          <!-- Date Range Custom Filter Collapsible -->
          <div style="background:#1e293b; border:1px solid #334155; border-radius:10px; padding:10px 12px; margin-bottom:14px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
              <span style="font-size:11px; font-weight:700; color:#94a3b8; text-transform:uppercase; letter-spacing:0.5px;">Custom Date Range</span>
              <button id="execRefreshBtn" style="background:transparent; border:none; color:#38bdf8; font-size:12px; cursor:pointer; font-weight:600; display:flex; align-items:center; gap:4px;">
                <i class="fas fa-sync-alt ${this.loading ? 'fa-spin' : ''}"></i> Refresh
              </button>
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

          ${this.loading ? `
            <div style="text-align:center; padding:48px 16px;">
              <i class="fas fa-circle-notch fa-spin" style="font-size:28px; color:#38bdf8; margin-bottom:12px;"></i>
              <div style="color:#94a3b8; font-size:13px; font-weight:500;">Loading leadership metrics...</div>
            </div>
          ` : `
            <!-- Top KPI Cards Grid -->
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:14px;">
              <!-- Total Leads -->
              <div style="background:linear-gradient(135deg, #1e293b, #111827); border:1px solid #334155; border-radius:12px; padding:12px 14px;">
                <div style="font-size:11px; font-weight:700; color:#94a3b8; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">Total Leads</div>
                <div style="font-size:24px; font-weight:800; color:#ffffff;">${this.fmtNum(total)}</div>
                <div style="font-size:11px; color:#38bdf8; margin-top:2px;">Across all verticals</div>
              </div>

              <!-- Won Leads -->
              <div style="background:linear-gradient(135deg, #064e3b, #022c22); border:1px solid #059669; border-radius:12px; padding:12px 14px;">
                <div style="font-size:11px; font-weight:700; color:#6ee7b7; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">Won Deals</div>
                <div style="font-size:24px; font-weight:800; color:#34d399;">${this.fmtNum(won)}</div>
                <div style="font-size:11px; color:#a7f3d0; margin-top:2px;">${winRate}% Win Rate</div>
              </div>

              <!-- Deal Value Total -->
              <div style="background:linear-gradient(135deg, #1e1b4b, #0f172a); border:1px solid #4338ca; border-radius:12px; padding:12px 14px;">
                <div style="font-size:11px; font-weight:700; color:#c7d2fe; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">Total Pipeline Deal</div>
                <div style="font-size:18px; font-weight:800; color:#818cf8;">${this.fmtVal(this.summary.total_deal_value)}</div>
                <div style="font-size:11px; color:#a5b4fc; margin-top:2px;">Avg: ${this.fmtVal(this.summary.avg_deal_value)}</div>
              </div>

              <!-- Won Deal Value -->
              <div style="background:linear-gradient(135deg, #14532d, #052e16); border:1px solid #16a34a; border-radius:12px; padding:12px 14px;">
                <div style="font-size:11px; font-weight:700; color:#86efac; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">Won Deal Value</div>
                <div style="font-size:18px; font-weight:800; color:#4ade80;">${this.fmtVal(this.summary.won_deal_value)}</div>
                <div style="font-size:11px; color:#bbf7d0; margin-top:2px;">Closed Revenue</div>
              </div>
            </div>

            <!-- In Progress / Lost / Collections Row -->
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin-bottom:14px;">
              <div style="background:#1e293b; border:1px solid #334155; border-radius:10px; padding:10px; text-align:center;">
                <div style="font-size:10px; color:#fbbf24; font-weight:700; text-transform:uppercase;">In Progress</div>
                <div style="font-size:16px; font-weight:800; color:#fef08a; margin-top:2px;">${this.fmtNum(inProg)}</div>
              </div>
              <div style="background:#1e293b; border:1px solid #334155; border-radius:10px; padding:10px; text-align:center;">
                <div style="font-size:10px; color:#f87171; font-weight:700; text-transform:uppercase;">Lost</div>
                <div style="font-size:16px; font-weight:800; color:#fca5a5; margin-top:2px;">${this.fmtNum(lost)}</div>
              </div>
              <div style="background:#1e293b; border:1px solid #334155; border-radius:10px; padding:10px; text-align:center;">
                <div style="font-size:10px; color:#38bdf8; font-weight:700; text-transform:uppercase;">Collected</div>
                <div style="font-size:14px; font-weight:800; color:#7dd3fc; margin-top:2px;">${this.fmtVal(this.summary.total_collected)}</div>
              </div>
            </div>

            <!-- Segment Navigation Tabs -->
            <div style="display:flex; background:#0f172a; border:1px solid #334155; border-radius:10px; padding:3px; margin-bottom:14px;">
              <button class="nav-tab-btn ${this.activeTab === 'overview' ? 'active' : ''}" data-tab="overview" style="${this.getNavTabStyle(this.activeTab === 'overview')}">Overview & Stages</button>
              <button class="nav-tab-btn ${this.activeTab === 'categories' ? 'active' : ''}" data-tab="categories" style="${this.getNavTabStyle(this.activeTab === 'categories')}">Verticals</button>
              <button class="nav-tab-btn ${this.activeTab === 'handlers' ? 'active' : ''}" data-tab="handlers" style="${this.getNavTabStyle(this.activeTab === 'handlers')}">Handlers</button>
            </div>

            <!-- Active Tab Content -->
            ${this.activeTab === 'overview' ? this.renderOverviewTab(total) : ''}
            ${this.activeTab === 'categories' ? this.renderCategoriesTab(total) : ''}
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
      return 'flex:1; background:#1e293b; color:#38bdf8; border:none; border-radius:7px; padding:8px 6px; font-size:12px; font-weight:700; cursor:pointer;';
    }
    return 'flex:1; background:transparent; color:#64748b; border:none; padding:8px 6px; font-size:12px; font-weight:600; cursor:pointer;';
  }

  private renderOverviewTab(total: number): string {
    return `
      <!-- Status Pipeline Breakdown -->
      <div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:14px; margin-bottom:14px;">
        <div style="font-size:13px; font-weight:700; color:#ffffff; margin-bottom:12px; display:flex; align-items:center; gap:6px;">
          <i class="fas fa-filter" style="color:#38bdf8;"></i> Stage & Pipeline Breakdown
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
              <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
                <span style="font-weight:600; color:#e2e8f0;">${name}</span>
                <span style="font-weight:700; color:#94a3b8;">${this.fmtNum(count)} <span style="font-size:10px; font-weight:400; color:#64748b;">(${pct}%)</span></span>
              </div>
              <div style="background:#0f172a; border-radius:4px; height:7px; overflow:hidden;">
                <div style="width:${pct}%; background:${color}; height:100%; border-radius:4px;"></div>
              </div>
            </div>
          `;
        }).join('')}
      </div>

      <!-- Quick Shortcuts to Workflows -->
      <div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:14px; margin-bottom:14px;">
        <div style="font-size:13px; font-weight:700; color:#ffffff; margin-bottom:10px; display:flex; align-items:center; gap:6px;">
          <i class="fas fa-bolt" style="color:#f59e0b;"></i> Workflows & Category Masters
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
            <div style="font-size:10px; color:#64748b; margin-top:2px;">Franchise & Dealerships</div>
          </button>
          <button class="workflow-nav-card" data-route="category-leads-master" data-tab="real-dreams" style="background:#0f172a; border:1px solid #334155; border-radius:8px; padding:10px; text-align:left; color:#f1f5f9; cursor:pointer;">
            <div style="font-size:11px; font-weight:700; color:#ef4444;"><i class="fas fa-home"></i> Real Dreams</div>
            <div style="font-size:10px; color:#64748b; margin-top:2px;">Plots & Real Estate</div>
          </button>
        </div>
      </div>
    `;
  }

  private renderCategoriesTab(total: number): string {
    return `
      <div style="display:flex; flex-direction:column; gap:10px;">
        ${this.byCategory.length === 0 ? `
          <div style="background:#1e293b; border-radius:10px; padding:24px; text-align:center; color:#64748b; font-size:12px;">
            No category distribution found for this period.
          </div>
        ` : this.byCategory.map(cat => {
          const name = cat.category || cat.name || 'Unassigned';
          const count = cat.count || cat.total || 0;
          const won = cat.won || 0;
          const val = cat.deal_value || cat.won_deal_value || 0;
          const pct = total > 0 ? ((count / total) * 100).toFixed(1) : '0';
          const tabKey = name.toLowerCase().replace(/\s+/g, '-');

          return `
            <div class="cat-card" data-cat="${tabKey}" style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:14px; cursor:pointer; transition:transform 0.15s ease;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <div style="font-weight:700; font-size:14px; color:#ffffff; display:flex; align-items:center; gap:8px;">
                  <span style="width:8px; height:8px; border-radius:50%; background:#38bdf8;"></span>
                  ${name}
                </div>
                <span style="font-size:11px; color:#38bdf8; font-weight:600; display:flex; align-items:center; gap:4px;">
                  View Master <i class="fas fa-chevron-right" style="font-size:9px;"></i>
                </span>
              </div>

              <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:6px; background:#0f172a; border-radius:8px; padding:8px 10px; margin-bottom:8px;">
                <div>
                  <div style="font-size:9px; color:#64748b; text-transform:uppercase;">Leads</div>
                  <div style="font-size:14px; font-weight:700; color:#f1f5f9;">${this.fmtNum(count)}</div>
                </div>
                <div>
                  <div style="font-size:9px; color:#64748b; text-transform:uppercase;">Won</div>
                  <div style="font-size:14px; font-weight:700; color:#34d399;">${this.fmtNum(won)}</div>
                </div>
                <div>
                  <div style="font-size:9px; color:#64748b; text-transform:uppercase;">Deal Value</div>
                  <div style="font-size:13px; font-weight:700; color:#818cf8;">${this.fmtVal(val)}</div>
                </div>
              </div>

              <div style="background:#0b1329; border-radius:4px; height:5px; overflow:hidden;">
                <div style="width:${pct}%; background:#38bdf8; height:100%; border-radius:4px;"></div>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  private renderHandlersTab(): string {
    return `
      <div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:14px;">
        <div style="font-size:13px; font-weight:700; color:#ffffff; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center;">
          <span><i class="fas fa-trophy" style="color:#fbbf24;"></i> Handler Performance</span>
          <span style="font-size:11px; color:#94a3b8; font-weight:400;">${this.handlers.length} Handlers</span>
        </div>

        ${this.handlers.length === 0 ? `
          <div style="text-align:center; color:#64748b; padding:24px; font-size:12px;">No handler analytics for selected range</div>
        ` : `
          <div style="display:flex; flex-direction:column; gap:8px;">
            ${this.handlers.slice(0, 30).map((h, i) => {
              const name = h.name || 'Staff Member';
              const code = h.emp_code ? `(${h.emp_code})` : '';
              const tot = h.total || 0;
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

  private attachEventListeners(): void {
    // Preset buttons
    this.container.querySelectorAll('.preset-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const target = e.currentTarget as HTMLElement;
        const preset = target.dataset.preset as any;
        if (preset) this.setPreset(preset);
      });
    });

    // Custom date apply
    document.getElementById('execApplyDateBtn')?.addEventListener('click', () => {
      const fromEl = document.getElementById('execFromDate') as HTMLInputElement;
      const toEl = document.getElementById('execToDate') as HTMLInputElement;
      if (fromEl) this.fromDate = fromEl.value;
      if (toEl) this.toDate = toEl.value;
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
          this.activeTab = tab;
          this.render();
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
  }
}
