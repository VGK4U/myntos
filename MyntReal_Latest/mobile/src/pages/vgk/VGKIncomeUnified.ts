/**
 * VGK Income — Unified Management (Mobile Parity)
 * DC Protocol: DC_MOBILE_VGK_INCOME_UNIFIED_001
 *
 * Staff-only management page for VGK Unified Cash Income, Bonanza Claims,
 * and Field Allowances with 3-level collapsible accordion view (Date → Partner → Entries),
 * mobile-optimized summary cards, stacked filters, and action modals.
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';

interface UnifiedRow {
  id: number;
  entry_number: string;
  kind: string;
  level: number | null;
  partner_name: string;
  partner_code: string;
  client_name: string;
  deal_value_received?: number | null;
  commission_pct?: number | null;
  commission_amount: number;
  admin_charges: number;
  tds_amount: number;
  net_payout: number;
  status: string;
  partner_points_balance?: number | null;
  available_actions: string[];
  company_id: number;
  income_date: string | null;
  created_at?: string | null;
  ledger_posted?: boolean;
  stage_1_approved_by?: string | null;
  stage_1_approved_at?: string | null;
  confirmed_at?: string | null;
  paid_at?: string | null;
  payment_mode?: string | null;
  payment_utr?: string | null;
  _is_bonanza?: boolean;
  _is_field_allowance?: boolean;
  _raw_bnz?: any;
  _raw_fa?: any;
}

export class VGKIncomeUnified {
  static readonly slug = 'vgk-income-unified';
  static readonly label = 'VGK Income — Unified';
  static readonly icon = '💹';

  private container: HTMLElement;
  private rows: UnifiedRow[] = [];
  private fullRows: UnifiedRow[] = [];
  private loading: boolean = true;

  // Filter states
  private filterStatus: string = '';
  private filterKind: string = '';
  private filterMonth: string = '';
  private filterDateFrom: string = '';
  private filterDateTo: string = '';
  private filterSearch: string = '';
  private filterPoints: string = '';

  // Accordion state tracking (open keys)
  private expandedDates: Set<string> = new Set();
  private expandedPartners: Set<string> = new Set();

  // Action modal state
  private activeModalRow: UnifiedRow | null = null;
  private activeModalAction: string = '';
  private paymentMode: 'BANK' | 'CASH' = 'BANK';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.renderContainer();
    await this.loadData();
  }

  private renderContainer(): void {
    this.container.innerHTML = `
      <div class="page-container" style="background:#f0fdf4;min-height:100vh;padding-bottom:30px">
        ${PageHeader.render({ title: 'VGK Income — Unified', showBack: true })}
        <div id="pageContent" style="padding:12px">
          <div style="text-align:center;padding:40px 10px;color:#059669">
            <i class="fas fa-spinner fa-spin fa-2x"></i>
            <div style="margin-top:10px;font-size:14px;font-weight:600">Loading Unified Income Data...</div>
          </div>
        </div>
      </div>
      <div id="actModalOverlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9999;align-items:center;justify-content:center;padding:16px"></div>
    `;
    PageHeader.attachListeners({ title: 'VGK Income — Unified', showBack: true });
  }

  private async loadData(): Promise<void> {
    this.loading = true;
    try {
      const qp = new URLSearchParams({ vgk_mode: 'true', per_page: '200' });
      if (this.filterStatus && !['Stage1Approved', 'Payout Completed'].includes(this.filterStatus)) {
        qp.set('status', this.filterStatus);
      }
      if (this.filterKind && !['BONANZA', 'FIELD_ALLOWANCE'].includes(this.filterKind)) {
        qp.set('kind', this.filterKind);
      }
      if (this.filterPoints) {
        qp.set('points_filter', this.filterPoints);
      }

      const fetchIncome = !this.filterKind || !['BONANZA', 'FIELD_ALLOWANCE'].includes(this.filterKind);
      const bnzStatusOk = !this.filterStatus || ['RELEASED', 'PAID', 'PENDING'].includes(this.filterStatus);
      const fetchBonanza = (!this.filterKind || this.filterKind === 'BONANZA') && bnzStatusOk;
      const fetchFA = !this.filterKind || this.filterKind === 'FIELD_ALLOWANCE';

      const faQp = new URLSearchParams({ per_page: '200' });
      if (this.filterStatus && ['Pending', 'Stage1Approved', 'Payout Completed'].includes(this.filterStatus)) {
        faQp.set('status', this.filterStatus);
      }
      if (this.filterMonth) {
        faQp.set('month_year', this.filterMonth.replace('-', '').substring(2));
      }
      if (this.filterSearch) {
        faQp.set('search', this.filterSearch);
      }

      const [incomeRes, bnzRes, faRes] = await Promise.all([
        fetchIncome ? apiService.get<any>(`/vgk/staff/vgk/cash-income/unified-list?${qp.toString()}`) : Promise.resolve(null),
        fetchBonanza ? apiService.get<any>('/bonanza/vgk/pending-payments?stage=all') : Promise.resolve(null),
        fetchFA ? apiService.get<any>(`/vgk/staff/vgk/field-allowances?${faQp.toString()}`) : Promise.resolve(null),
      ]);

      let combined: UnifiedRow[] = [];

      if (incomeRes && incomeRes.success) {
        const dataArr = Array.isArray(incomeRes.data) ? incomeRes.data : (incomeRes.data?.data || []);
        combined = [...dataArr];
      }

      if (bnzRes && bnzRes.success) {
        const claims = bnzRes.data?.claims || bnzRes.claims || [];
        const bnzRows = claims.map((c: any) => this.normalizeBonanzaRow(c));
        combined = [...combined, ...bnzRows];
      }

      if (faRes && faRes.success) {
        const faData = Array.isArray(faRes.data) ? faRes.data : (faRes.data?.data || []);
        const faRows = faData.map((r: any) => this.normalizeFaRow(r));
        combined = [...combined, ...faRows];
      }

      this.fullRows = [...combined];
      this.applyFilters();
    } catch (err) {
      console.error('[VGKIncomeUnified] Error loading data:', err);
      const content = document.getElementById('pageContent');
      if (content) {
        content.innerHTML = `
          <div style="background:#fee2e2;color:#991b1b;padding:16px;border-radius:12px;text-align:center">
            <i class="fas fa-exclamation-triangle fa-2x"></i>
            <div style="font-weight:700;margin-top:8px">Failed to load VGK Income records</div>
            <div style="font-size:12px;margin-top:4px">${(err as any)?.message || 'Please check network connection'}</div>
            <button id="retryBtn" style="margin-top:12px;background:#dc2626;color:#fff;border:none;padding:8px 16px;border-radius:8px;font-size:13px;font-weight:600">Retry</button>
          </div>
        `;
        document.getElementById('retryBtn')?.addEventListener('click', () => this.loadData());
      }
    } finally {
      this.loading = false;
    }
  }

  private normalizeBonanzaRow(c: any): UnifiedRow {
    const gross = c.amount || 0;
    const admin = Math.round(gross * 0.10 * 100) / 100;
    const net = Math.round((gross - admin) * 100) / 100;

    let status = 'PENDING';
    if (c.processed_status === 'Paid') status = 'PAID';
    else if (c.processed_status === 'Payment Released') status = 'RELEASED';

    const deal = c.deal_count > 1
      ? ` (${c.deal_count} files × ₹${Number(c.slab_extra_amount || 0).toLocaleString('en-IN')})`
      : '';

    const acts: string[] = [];
    if (status === 'PENDING') acts.push('approve_bnz');
    if (status === 'RELEASED') acts.push('pay_bnz');

    return {
      id: c.claim_id,
      entry_number: 'BNZ-' + c.claim_id,
      kind: 'BONANZA',
      level: null,
      partner_name: c.partner_name || 'Partner',
      partner_code: c.partner_code || '',
      client_name: (c.bonanza_name || 'Bonanza') + deal,
      commission_amount: gross,
      admin_charges: admin,
      tds_amount: 0,
      net_payout: net,
      status: status,
      available_actions: acts,
      company_id: c.is_solar ? 4 : (c.partner_company_id || 2),
      income_date: c.created_at || c.released_at || null,
      _is_bonanza: true,
      _raw_bnz: c,
    };
  }

  private normalizeFaRow(r: any): UnifiedRow {
    const gross = r.gross || r.amount_paid || 0;
    const acts: string[] = [];
    const st = r.status || 'Pending';
    if (st === 'Pending' || st === '') acts.push('fa_stage1');
    if (st === 'Stage1Approved') acts.push('fa_stage2');

    return {
      id: r.id,
      entry_number: `FA-${r.allowance_type || 'STD'}-${r.month_year || ''}`.toUpperCase().replace(/\s/g, '-'),
      kind: 'FIELD_ALLOWANCE',
      level: null,
      partner_name: r.user_name || r.user_emp_code || String(r.user_id),
      partner_code: r.user_emp_code || '',
      client_name: (r.allowance_type || '').replace(/_/g, ' ') + (r.month_year ? ' · ' + r.month_year : ''),
      commission_amount: gross,
      admin_charges: 0,
      tds_amount: 0,
      net_payout: gross,
      status: st === 'Payout Completed' ? 'PAID' : st,
      available_actions: acts,
      company_id: r.company_id || 2,
      income_date: r.created_at || null,
      _is_field_allowance: true,
      _raw_fa: r,
    };
  }

  private applyFilters(): void {
    let result = [...this.fullRows];

    if (this.filterStatus) {
      result = result.filter(r => {
        const st = r.status === 'Payout Completed' ? 'PAID' : r.status === 'Stage1Approved' ? 'STAGE1_APPROVED' : r.status;
        return st === this.filterStatus;
      });
    }

    if (this.filterKind) {
      result = result.filter(r => r.kind === this.filterKind);
    }

    if (this.filterSearch) {
      const q = this.filterSearch.toLowerCase();
      result = result.filter(r =>
        (r.entry_number || '').toLowerCase().includes(q) ||
        (r.partner_code || '').toLowerCase().includes(q) ||
        (r.partner_name || '').toLowerCase().includes(q) ||
        (r.client_name || '').toLowerCase().includes(q)
      );
    }

    if (this.filterDateFrom || this.filterDateTo) {
      result = result.filter(r => {
        const raw = r.income_date || r.created_at || null;
        if (!raw) return !this.filterDateFrom;
        const d = this.parseIsoDate(raw);
        if (!d) return false;
        const ymd = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
        if (this.filterDateFrom && ymd < this.filterDateFrom) return false;
        if (this.filterDateTo && ymd > this.filterDateTo) return false;
        return true;
      });
    }

    if (this.filterMonth) {
      const ym = this.filterMonth.replace('-', '').substring(2);
      result = result.filter(r => r._is_field_allowance || (r.entry_number || '').includes(ym));
    }

    this.rows = result;
    this.updateUI();
  }

  private updateUI(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    content.innerHTML = `
      <!-- Summary Cards Row -->
      ${this.renderSummaryCards()}

      <!-- Filters Panel (Mobile Stacked) -->
      ${this.renderFilters()}

      <!-- 3-Level Accordion List -->
      ${this.render3LevelList()}
    `;

    this.attachEventListeners();
  }

  private renderSummaryCards(): string {
    const order = ['DRAFT', 'PENDING', 'RELEASED', 'STAGE1_APPROVED', 'PAID', 'CANCELLED'];
    const agg: Record<string, { count: number; gross: number; net: number }> = {};
    let totalGross = 0;
    let totalNet = 0;

    for (const r of this.rows) {
      const key = r.status === 'Payout Completed' ? 'PAID' : r.status === 'Stage1Approved' ? 'STAGE1_APPROVED' : (r.status || 'DRAFT');
      if (!agg[key]) agg[key] = { count: 0, gross: 0, net: 0 };
      agg[key].count++;
      agg[key].gross += Number(r.commission_amount || 0);
      agg[key].net += Number(r.net_payout || 0);
      if (key !== 'CANCELLED') {
        totalGross += Number(r.commission_amount || 0);
        totalNet += Number(r.net_payout || 0);
      }
    }

    const cardsHtml = order.map(st => {
      const a = agg[st] || { count: 0, gross: 0, net: 0 };
      const isActive = this.filterStatus === st;
      const colorMap: Record<string, string> = {
        DRAFT: '#92400e', PENDING: '#1e40af', RELEASED: '#0d9488',
        STAGE1_APPROVED: '#5b21b6', PAID: '#15803d', CANCELLED: '#991b1b'
      };
      const borderColor = isActive ? colorMap[st] : '#d1fae5';
      const bgColor = isActive ? colorMap[st] : '#ffffff';
      const textColor = isActive ? '#ffffff' : '#374151';
      const valColor = isActive ? '#ffffff' : colorMap[st];

      return `
        <div class="sum-card-mb" data-status="${st}" style="flex:0 0 110px;background:${bgColor};border:1.5px solid ${borderColor};border-radius:10px;padding:8px 10px;cursor:pointer;scroll-snap-align:start">
          <div style="font-size:10px;font-weight:700;color:${textColor};text-transform:uppercase;letter-spacing:.05em">${st.replace('_', ' ')}</div>
          <div style="font-size:18px;font-weight:800;color:${valColor};margin-top:2px">${a.count}</div>
          <div style="font-size:10.5px;font-weight:600;color:${isActive ? '#e2e8f0' : '#6b7280'};margin-top:2px">${this.fmt(a.gross)}</div>
        </div>
      `;
    }).join('');

    const totalCardHtml = `
      <div class="sum-card-mb" data-status="" style="flex:0 0 140px;background:#064e3b;border:1.5px solid #064e3b;border-radius:10px;padding:8px 10px;cursor:pointer;scroll-snap-align:start">
        <div style="font-size:10px;font-weight:700;color:#a7f3d0;text-transform:uppercase;letter-spacing:.05em">TOTAL NET</div>
        <div style="font-size:18px;font-weight:800;color:#ffffff;margin-top:2px">${this.fmt(totalNet)}</div>
        <div style="font-size:10.5px;font-weight:600;color:#a7f3d0;margin-top:2px">Gross ${this.fmt(totalGross)}</div>
      </div>
    `;

    return `
      <div style="display:flex;gap:8px;overflow-x:auto;padding-bottom:6px;margin-bottom:12px;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch">
        ${cardsHtml}
        ${totalCardHtml}
      </div>
    `;
  }

  private renderFilters(): string {
    return `
      <div style="background:#fff;border-radius:12px;border:1.5px solid #d1fae5;padding:12px;margin-bottom:12px">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px">
          <div>
            <label style="font-size:11px;font-weight:700;color:#374151;display:block;margin-bottom:3px">STATUS</label>
            <select id="mbStatusSel" style="width:100%;padding:7px 8px;border:1.5px solid #d1fae5;border-radius:8px;font-size:12px;background:#fff">
              <option value="" ${this.filterStatus === '' ? 'selected' : ''}>All Statuses</option>
              <option value="DRAFT" ${this.filterStatus === 'DRAFT' ? 'selected' : ''}>DRAFT</option>
              <option value="PENDING" ${this.filterStatus === 'PENDING' ? 'selected' : ''}>PENDING</option>
              <option value="STAGE1_APPROVED" ${this.filterStatus === 'STAGE1_APPROVED' ? 'selected' : ''}>STAGE1 APPROVED</option>
              <option value="PAID" ${this.filterStatus === 'PAID' ? 'selected' : ''}>PAID</option>
              <option value="CANCELLED" ${this.filterStatus === 'CANCELLED' ? 'selected' : ''}>CANCELLED</option>
            </select>
          </div>
          <div>
            <label style="font-size:11px;font-weight:700;color:#374151;display:block;margin-bottom:3px">TYPE</label>
            <select id="mbKindSel" style="width:100%;padding:7px 8px;border:1.5px solid #d1fae5;border-radius:8px;font-size:12px;background:#fff">
              <option value="" ${this.filterKind === '' ? 'selected' : ''}>All Types</option>
              <option value="COMMISSION" ${this.filterKind === 'COMMISSION' ? 'selected' : ''}>Commission</option>
              <option value="ADVANCE" ${this.filterKind === 'ADVANCE' ? 'selected' : ''}>Solar Advance</option>
              <option value="SENIOR_COMM" ${this.filterKind === 'SENIOR_COMM' ? 'selected' : ''}>Senior Comm</option>
              <option value="BONANZA" ${this.filterKind === 'BONANZA' ? 'selected' : ''}>Bonanza</option>
              <option value="FIELD_ALLOWANCE" ${this.filterKind === 'FIELD_ALLOWANCE' ? 'selected' : ''}>Field Allowance</option>
            </select>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px">
          <div>
            <label style="font-size:11px;font-weight:700;color:#374151;display:block;margin-bottom:3px">FROM DATE</label>
            <input type="date" id="mbDateFromInp" value="${this.filterDateFrom}" style="width:100%;padding:6px 8px;border:1.5px solid #d1fae5;border-radius:8px;font-size:12px">
          </div>
          <div>
            <label style="font-size:11px;font-weight:700;color:#374151;display:block;margin-bottom:3px">TO DATE</label>
            <input type="date" id="mbDateToInp" value="${this.filterDateTo}" style="width:100%;padding:6px 8px;border:1.5px solid #d1fae5;border-radius:8px;font-size:12px">
          </div>
        </div>

        <div style="display:flex;gap:6px;align-items:center">
          <input type="text" id="mbSearchInp" placeholder="Search partner, code, entry #..." value="${this.filterSearch}" style="flex:1;padding:7px 10px;border:1.5px solid #d1fae5;border-radius:8px;font-size:12px">
          <button id="mbRefreshBtn" style="background:#059669;color:#fff;border:none;padding:7px 12px;border-radius:8px;font-size:12px;font-weight:700;display:flex;align-items:center;gap:4px">
            <i class="fas fa-sync-alt"></i>
          </button>
        </div>
      </div>
    `;
  }

  private render3LevelList(): string {
    if (!this.rows.length) {
      return `
        <div style="background:#fff;border-radius:12px;border:1.5px solid #d1fae5;padding:40px 16px;text-align:center;color:#6b7280">
          <i class="fas fa-inbox fa-3x" style="color:#d1fae5;margin-bottom:12px"></i>
          <div style="font-weight:700;font-size:15px;color:#374151">No income entries found</div>
          <div style="font-size:12px;margin-top:4px">Try clearing filters or search query</div>
        </div>
      `;
    }

    const dateMap: Record<string, {
      dateDisplay: string;
      count: number;
      net: number;
      gross: number;
      partners: Record<string, {
        name: string;
        code: string;
        count: number;
        net: number;
        gross: number;
        entries: UnifiedRow[];
      }>;
    }> = {};

    for (const r of this.rows) {
      const rawDt = r.income_date || r.created_at || null;
      const dKey = this.getDateKey(rawDt);
      const dateDisplay = this.fmtDate(rawDt);

      if (!dateMap[dKey]) {
        dateMap[dKey] = { dateDisplay, count: 0, net: 0, gross: 0, partners: {} };
      }
      dateMap[dKey].count++;
      dateMap[dKey].net += Number(r.net_payout || 0);
      dateMap[dKey].gross += Number(r.commission_amount || 0);

      const pCode = r.partner_code || '';
      const pName = r.partner_name || pCode || 'Unassigned';
      const pKey = (pCode || pName).replace(/[^a-zA-Z0-9]/g, '_');

      if (!dateMap[dKey].partners[pKey]) {
        dateMap[dKey].partners[pKey] = { name: pName, code: pCode, count: 0, net: 0, gross: 0, entries: [] };
      }
      dateMap[dKey].partners[pKey].count++;
      dateMap[dKey].partners[pKey].net += Number(r.net_payout || 0);
      dateMap[dKey].partners[pKey].gross += Number(r.commission_amount || 0);
      dateMap[dKey].partners[pKey].entries.push(r);
    }

    const sortedDates = Object.keys(dateMap).sort().reverse();

    if (this.expandedDates.size === 0 && sortedDates.length > 0) {
      this.expandedDates.add(sortedDates[0]);
      const firstPartnerKey = Object.keys(dateMap[sortedDates[0]].partners)[0];
      if (firstPartnerKey) {
        this.expandedPartners.add(`${sortedDates[0]}_${firstPartnerKey}`);
      }
    }

    let html = '<div style="display:flex;flex-direction:column;gap:10px">';

    for (const dKey of sortedDates) {
      const dGroup = dateMap[dKey];
      const isDateExpanded = this.expandedDates.has(dKey);

      html += `
        <div style="background:#fff;border-radius:12px;border:1.5px solid #d1fae5;overflow:hidden">
          <!-- Level 1 Date Header -->
          <div class="lvl1-date-hdr" data-dkey="${dKey}" style="background:#064e3b;color:#fff;padding:12px 14px;display:flex;justify-content:space-between;align-items:center;cursor:pointer">
            <div>
              <div style="display:flex;align-items:center;gap:8px;font-weight:800;font-size:14px">
                <i class="fas fa-chevron-${isDateExpanded ? 'down' : 'right'}" style="font-size:11px;color:#a7f3d0"></i>
                <span>${dGroup.dateDisplay}</span>
                <span style="background:#047857;color:#a7f3d0;font-size:10px;padding:2px 8px;border-radius:12px;font-weight:700">${dGroup.count} items</span>
              </div>
            </div>
            <div style="text-align:right">
              <div style="font-weight:800;font-size:14px;color:#a7f3d0">${this.fmt(dGroup.net)}</div>
              <div style="font-size:10.5px;opacity:.8">Gross ${this.fmt(dGroup.gross)}</div>
            </div>
          </div>

          <!-- Level 2 Partner Rows -->
          ${isDateExpanded ? `
            <div style="padding:8px 10px;background:#f0fdf4;display:flex;flex-direction:column;gap:8px">
              ${Object.keys(dGroup.partners).map(pKey => {
                const pGroup = dGroup.partners[pKey];
                const fullPKey = `${dKey}_${pKey}`;
                const isPartnerExpanded = this.expandedPartners.has(fullPKey);

                return `
                  <div style="background:#ffffff;border:1.5px solid #bbf7d0;border-radius:10px;overflow:hidden">
                    <div class="lvl2-partner-hdr" data-pkey="${fullPKey}" style="background:#ecfdf5;padding:10px 12px;display:flex;justify-content:space-between;align-items:center;cursor:pointer">
                      <div style="display:flex;align-items:center;gap:8px">
                        <i class="fas fa-chevron-${isPartnerExpanded ? 'down' : 'right'}" style="font-size:10px;color:#059669"></i>
                        <div>
                          <div style="font-weight:700;font-size:13px;color:#065f46">${this.escape(pGroup.name)}</div>
                          ${pGroup.code ? `<div style="font-family:monospace;font-size:11px;color:#6b7280">${this.escape(pGroup.code)}</div>` : ''}
                        </div>
                      </div>
                      <div style="text-align:right">
                        <div style="font-weight:700;font-size:13px;color:#059669">${this.fmt(pGroup.net)}</div>
                        <div style="font-size:10.5px;color:#6b7280">${pGroup.count} entries</div>
                      </div>
                    </div>

                    <!-- Level 3 Entries -->
                    ${isPartnerExpanded ? `
                      <div style="padding:8px;display:flex;flex-direction:column;gap:8px;background:#f9fafb">
                        ${pGroup.entries.map(entry => this.renderLevel3Card(entry)).join('')}
                      </div>
                    ` : ''}
                  </div>
                `;
              }).join('')}
            </div>
          ` : ''}
        </div>
      `;
    }

    html += '</div>';
    return html;
  }

  private renderLevel3Card(r: UnifiedRow): string {
    const kindCssMap: Record<string, string> = {
      ADVANCE: 'background:#fef3c7;color:#92400e',
      SLAB_BONUS: 'background:#d1fae5;color:#065f46',
      BONANZA: 'background:#ede9fe;color:#5b21b6',
      SENIOR_COMM: 'background:#fce7f3;color:#9d174d',
      FIELD_ALLOWANCE: 'background:#dbeafe;color:#1e40af',
    };
    const kindStyle = kindCssMap[r.kind] || 'background:#f3f4f6;color:#374151';

    const statusBadgeClassMap: Record<string, string> = {
      DRAFT: 'background:#fef3c7;color:#92400e',
      PENDING: 'background:#dbeafe;color:#1e40af',
      RELEASED: 'background:#ccfbf1;color:#0f766e',
      STAGE1_APPROVED: 'background:#ede9fe;color:#5b21b6',
      PAID: 'background:#dcfce7;color:#166534',
      CANCELLED: 'background:#fee2e2;color:#991b1b',
    };
    const badgeStyle = statusBadgeClassMap[r.status] || 'background:#f3f4f6;color:#374151';

    const actionBtns = (r.available_actions || []).map(a => this.renderActionBtn(r, a)).join('');

    return `
      <div style="background:#fff;border-radius:8px;border:1px solid #e5e7eb;border-left:4px solid #059669;padding:10px 12px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <div style="font-family:monospace;font-weight:700;font-size:12px;color:#111827">${this.escape(r.entry_number)}</div>
          <span style="border-radius:12px;padding:2px 8px;font-size:10px;font-weight:700;${kindStyle}">
            ${this.escape(r.kind)} ${r.level ? 'L' + r.level : ''}
          </span>
        </div>

        <div style="font-size:12px;color:#4b5563;margin-bottom:8px">
          <i class="fas fa-user-tag me-1" style="color:#9ca3af;font-size:10px"></i>
          <span>${this.escape(r.client_name || '—')}</span>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;background:#f9fafb;padding:8px;border-radius:6px;margin-bottom:8px;font-size:11.5px">
          <div>
            <span style="color:#6b7280">Gross:</span>
            <strong style="color:#059669">${this.fmt(r.commission_amount)}</strong>
          </div>
          <div>
            <span style="color:#6b7280">Net Payout:</span>
            <strong style="color:#15803d">${this.fmt(r.net_payout)}</strong>
          </div>
          <div>
            <span style="color:#6b7280">Admin:</span>
            <span style="color:#d97706">${r.admin_charges ? this.fmt(r.admin_charges) : '—'}</span>
          </div>
          <div>
            <span style="color:#6b7280">TDS:</span>
            <span style="color:#dc2626">${r.tds_amount ? this.fmt(r.tds_amount) : '—'}</span>
          </div>
        </div>

        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <span style="border-radius:12px;padding:2px 8px;font-size:10.5px;font-weight:700;${badgeStyle}">
            ${r.status}
          </span>
          <div style="font-size:11px;color:#6b7280">
            ${r.partner_points_balance !== undefined && r.partner_points_balance !== null
              ? `Points: <strong>${Number(r.partner_points_balance).toLocaleString('en-IN')}</strong>`
              : ''}
          </div>
        </div>

        ${actionBtns ? `
          <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;padding-top:8px;border-top:1px dashed #e5e7eb">
            ${actionBtns}
          </div>
        ` : ''}
      </div>
    `;
  }

  private renderActionBtn(r: UnifiedRow, action: string): string {
    const btnStyle = 'border:none;border-radius:6px;padding:6px 12px;font-size:11.5px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:4px;color:#fff;';

    if (action === 'confirm') {
      return `<button class="act-btn" data-id="${r.id}" data-act="confirm" style="${btnStyle}background:#3b82f6"><i class="fas fa-check"></i> Confirm</button>`;
    }
    if (action === 'stage1_approve') {
      return `<button class="act-btn" data-id="${r.id}" data-act="stage1_approve" style="${btnStyle}background:#7c3aed"><i class="fas fa-user-check"></i> Stage 1 Approve</button>`;
    }
    if (action === 'mark_paid') {
      return `<button class="act-btn" data-id="${r.id}" data-act="mark_paid" style="${btnStyle}background:#15803d"><i class="fas fa-rupee-sign"></i> Mark Paid</button>`;
    }
    if (action === 'reject') {
      return `<button class="act-btn" data-id="${r.id}" data-act="reject" style="${btnStyle}background:#fff;color:#dc2626;border:1.5px solid #fca5a5"><i class="fas fa-times"></i> Reject</button>`;
    }
    if (action === 'approve_bnz') {
      return `<button class="act-btn-bnz-app" data-claimid="${r.id}" style="${btnStyle}background:#059669"><i class="fas fa-paper-plane"></i> Stage 1 Release</button>`;
    }
    if (action === 'pay_bnz') {
      return `<button class="act-btn-bnz-pay" data-claimid="${r.id}" data-gross="${r.commission_amount}" style="${btnStyle}background:#15803d"><i class="fas fa-rupee-sign"></i> Stage 2 Pay</button>`;
    }
    if (action === 'fa_stage1') {
      return `<button class="act-btn-fa-1" data-faid="${r.id}" style="${btnStyle}background:#7c3aed"><i class="fas fa-check"></i> Stage 1 Approve</button>`;
    }
    if (action === 'fa_stage2') {
      return `<button class="act-btn-fa-2" data-faid="${r.id}" style="${btnStyle}background:#15803d"><i class="fas fa-rupee-sign"></i> Stage 2 Mark Paid</button>`;
    }
    return '';
  }

  private attachEventListeners(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    content.querySelector('#mbStatusSel')?.addEventListener('change', (e: any) => {
      this.filterStatus = e.target.value;
      this.applyFilters();
    });

    content.querySelector('#mbKindSel')?.addEventListener('change', (e: any) => {
      this.filterKind = e.target.value;
      this.applyFilters();
    });

    content.querySelector('#mbDateFromInp')?.addEventListener('change', (e: any) => {
      this.filterDateFrom = e.target.value;
      this.applyFilters();
    });

    content.querySelector('#mbDateToInp')?.addEventListener('change', (e: any) => {
      this.filterDateTo = e.target.value;
      this.applyFilters();
    });

    content.querySelector('#mbSearchInp')?.addEventListener('input', (e: any) => {
      this.filterSearch = e.target.value;
      this.applyFilters();
    });

    content.querySelector('#mbRefreshBtn')?.addEventListener('click', () => {
      this.loadData();
    });

    content.querySelectorAll<HTMLElement>('.sum-card-mb').forEach(card => {
      card.addEventListener('click', () => {
        const st = card.getAttribute('data-status') || '';
        this.filterStatus = (this.filterStatus === st) ? '' : st;
        this.applyFilters();
      });
    });

    content.querySelectorAll<HTMLElement>('.lvl1-date-hdr').forEach(hdr => {
      hdr.addEventListener('click', () => {
        const dKey = hdr.getAttribute('data-dkey');
        if (dKey) {
          if (this.expandedDates.has(dKey)) {
            this.expandedDates.delete(dKey);
          } else {
            this.expandedDates.add(dKey);
          }
          this.updateUI();
        }
      });
    });

    content.querySelectorAll<HTMLElement>('.lvl2-partner-hdr').forEach(hdr => {
      hdr.addEventListener('click', (e) => {
        e.stopPropagation();
        const pKey = hdr.getAttribute('data-pkey');
        if (pKey) {
          if (this.expandedPartners.has(pKey)) {
            this.expandedPartners.delete(pKey);
          } else {
            this.expandedPartners.add(pKey);
          }
          this.updateUI();
        }
      });
    });

    content.querySelectorAll<HTMLElement>('.act-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = Number(btn.getAttribute('data-id'));
        const act = btn.getAttribute('data-act') || '';
        const row = this.rows.find(x => x.id === id);
        if (row) this.openActionModal(row, act);
      });
    });

    content.querySelectorAll<HTMLElement>('.act-btn-bnz-app').forEach(btn => {
      btn.addEventListener('click', () => {
        const claimId = Number(btn.getAttribute('data-claimid'));
        this.approveBonanza(claimId);
      });
    });

    content.querySelectorAll<HTMLElement>('.act-btn-fa-1').forEach(btn => {
      btn.addEventListener('click', () => {
        const faId = Number(btn.getAttribute('data-faid'));
        this.faStage1(faId);
      });
    });

    content.querySelectorAll<HTMLElement>('.act-btn-fa-2').forEach(btn => {
      btn.addEventListener('click', () => {
        const faId = Number(btn.getAttribute('data-faid'));
        this.faStage2(faId);
      });
    });
  }

  private openActionModal(row: UnifiedRow, action: string): void {
    this.activeModalRow = row;
    this.activeModalAction = action;
    this.paymentMode = 'BANK';

    const overlay = document.getElementById('actModalOverlay');
    if (!overlay) return;

    const actionTitleMap: Record<string, string> = {
      confirm: 'Confirm Income Entry',
      stage1_approve: 'Stage 1 Approve',
      mark_paid: 'Mark as Paid (Stage 2)',
      reject: 'Reject Entry'
    };

    overlay.innerHTML = `
      <div style="background:#fff;border-radius:14px;padding:20px;width:100%;max-width:440px;box-shadow:0 20px 60px rgba(0,0,0,0.3)">
        <div style="font-size:16px;font-weight:800;color:#111827;margin-bottom:12px">
          ${actionTitleMap[action] || action}
        </div>
        <div style="font-size:12px;color:#6b7280;margin-bottom:12px">
          Entry: <strong style="color:#111827">${this.escape(row.entry_number)}</strong> · Partner: <strong>${this.escape(row.partner_name)}</strong>
        </div>

        ${action === 'mark_paid' ? `
          <div style="margin-bottom:12px">
            <label style="font-size:11px;font-weight:700;color:#374151;display:block;margin-bottom:4px">PAYMENT MODE</label>
            <div style="display:flex;gap:6px">
              <button type="button" id="modeBankBtn" style="flex:1;padding:8px;border:1.5px solid #059669;border-radius:8px;background:#059669;color:#fff;font-size:12px;font-weight:700">Bank Transfer</button>
              <button type="button" id="modeCashBtn" style="flex:1;padding:8px;border:1.5px solid #d1d5db;border-radius:8px;background:#fff;color:#374151;font-size:12px;font-weight:700">Cash</button>
            </div>
          </div>
          <div id="bankFields">
            <label style="font-size:11px;font-weight:700;color:#374151;display:block;margin-bottom:4px">UTR / REFERENCE NUMBER *</label>
            <input type="text" id="modalUtrInp" placeholder="e.g. UTR123456789" style="width:100%;padding:8px;border:1.5px solid #d1d5db;border-radius:8px;font-size:12px;margin-bottom:12px">
          </div>
        ` : ''}

        ${action === 'reject' ? `
          <div style="margin-bottom:12px">
            <label style="font-size:11px;font-weight:700;color:#374151;display:block;margin-bottom:4px">REJECTION REASON *</label>
            <textarea id="modalRejReason" rows="3" placeholder="Provide reason for rejection" style="width:100%;padding:8px;border:1.5px solid #d1d5db;border-radius:8px;font-size:12px"></textarea>
          </div>
        ` : ''}

        <div style="margin-bottom:14px">
          <label style="font-size:11px;font-weight:700;color:#374151;display:block;margin-bottom:4px">NOTES (OPTIONAL)</label>
          <input type="text" id="modalNotesInp" placeholder="Optional notes" style="width:100%;padding:8px;border:1.5px solid #d1d5db;border-radius:8px;font-size:12px">
        </div>

        <div style="display:flex;gap:8px;justify-content:flex-end">
          <button id="modalCancelBtn" style="background:#fff;border:1.5px solid #d1d5db;padding:8px 16px;border-radius:8px;font-size:13px;font-weight:600;color:#374151">Cancel</button>
          <button id="modalSubmitBtn" style="background:${action === 'reject' ? '#dc2626' : '#059669'};color:#fff;border:none;padding:8px 20px;border-radius:8px;font-size:13px;font-weight:700">Submit</button>
        </div>
      </div>
    `;

    overlay.style.display = 'flex';

    document.getElementById('modalCancelBtn')?.addEventListener('click', () => {
      overlay.style.display = 'none';
    });

    document.getElementById('modalSubmitBtn')?.addEventListener('click', () => {
      this.submitModalAction();
    });
  }

  private async submitModalAction(): Promise<void> {
    if (!this.activeModalRow) return;

    const row = this.activeModalRow;
    const action = this.activeModalAction;
    const notesInp = (document.getElementById('modalNotesInp') as HTMLInputElement)?.value.trim();

    const body: any = {
      entry_id: row.id,
      action: action,
    };
    if (notesInp) body.notes = notesInp;

    if (action === 'reject') {
      const reason = (document.getElementById('modalRejReason') as HTMLTextAreaElement)?.value.trim();
      if (!reason) {
        alert('Rejection reason is required');
        return;
      }
      body.rejection_reason = reason;
    } else if (action === 'mark_paid') {
      body.payment_mode = this.paymentMode;
      if (this.paymentMode === 'BANK') {
        const utr = (document.getElementById('modalUtrInp') as HTMLInputElement)?.value.trim();
        if (!utr) {
          alert('UTR reference number is required');
          return;
        }
        body.payment_utr = utr;
        body.bank_ledger_id = 1;
      }
    }

    try {
      const res = await apiService.post<any>(`/vgk/staff/vgk/cash-income/unified-action?company_id=${row.company_id || 2}`, body);
      if (res.success) {
        (document.getElementById('actModalOverlay') as HTMLElement).style.display = 'none';
        this.loadData();
      } else {
        alert('Action failed: ' + (res.error || 'Unknown error'));
      }
    } catch (err) {
      alert('Action error: ' + (err as any)?.message);
    }
  }

  private async approveBonanza(claimId: number): Promise<void> {
    if (!confirm('Release this bonanza payment? Wallet will be credited.')) return;
    try {
      const res = await apiService.post<any>(`/bonanza/vgk/claims/${claimId}/status`, { status: 'Payment Released' });
      if (res.success) {
        this.loadData();
      } else {
        alert('Release failed: ' + (res.error || 'Error'));
      }
    } catch (err) {
      alert('Release error: ' + (err as any)?.message);
    }
  }

  private async faStage1(faId: number): Promise<void> {
    if (!confirm('Approve this field allowance (Stage 1)?')) return;
    try {
      const res = await apiService.post<any>(`/vgk/staff/vgk/field-allowances/${faId}/stage1-approve`, {});
      if (res.success) {
        this.loadData();
      } else {
        alert('Approval failed: ' + (res.error || 'Error'));
      }
    } catch (err) {
      alert('Approval error: ' + (err as any)?.message);
    }
  }

  private async faStage2(faId: number): Promise<void> {
    if (!confirm('Mark this field allowance as Paid (Stage 2)?')) return;
    try {
      const res = await apiService.post<any>(`/vgk/staff/vgk/field-allowances/${faId}/stage2-mark-paid`, {});
      if (res.success) {
        this.loadData();
      } else {
        alert('Mark paid failed: ' + (res.error || 'Error'));
      }
    } catch (err) {
      alert('Mark paid error: ' + (err as any)?.message);
    }
  }

  private parseIsoDate(s: any): Date | null {
    if (!s || s === 'null' || s === 'undefined') return null;
    const str = String(s).trim();
    if (!str) return null;
    if (/^\d{4}-\d{2}-\d{2}$/.test(str)) return new Date(str + 'T00:00:00+05:30');
    const ist = (str.endsWith('Z') || str.includes('+')) ? str : str + '+05:30';
    const d = new Date(ist);
    if (!isNaN(d.getTime())) return d;
    const d2 = new Date(str);
    return isNaN(d2.getTime()) ? null : d2;
  }

  private fmtDate(s: any): string {
    const d = this.parseIsoDate(s);
    if (!d) return '—';
    return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  private getDateKey(s: any): string {
    const d = this.parseIsoDate(s);
    if (!d) return 'NO_DATE';
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }

  private fmt(n: any): string {
    return '₹' + Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
  }

  private escape(s: string): string {
    return String(s ?? '').replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c] || c));
  }
}

export default VGKIncomeUnified;
