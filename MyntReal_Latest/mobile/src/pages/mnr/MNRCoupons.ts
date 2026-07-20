/**
 * MNR Coupons/EV Benefits Page - Web Table Parity
 * DC Protocol: DC_MOBILE_MNR_COUPONS_002
 * Exact web table: Coupon Code, Benefit Type, Value, Status, Created, Redeemed
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';
import { MobileTable } from '../../components/MobileTable';

interface EVCoupon {
  id: number;
  coupon_code: string;
  benefit_type: string;
  value: number;
  status: string;
  created_at: string;
  redeemed_at: string | null;
}

interface EVStats {
  total_coupons: number;
  redeemed_coupons: number;
  available_coupons: number;
  total_value_redeemed: number;
}

export class MNRCoupons {
  private container: HTMLElement;
  private coupons: EVCoupon[] = [];
  private stats: EVStats | null = null;
  private loading: boolean = true;
  private activeTab: string = 'all';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadCoupons();
  }

  private async loadCoupons(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const [couponsRes, statsRes] = await Promise.all([
        apiService.get<any>('/ev-discount/my-coupons'),
        apiService.get<any>('/users/dashboard-data-fast')
      ]);

      if (couponsRes.success && couponsRes.data) {
        const couponsList = couponsRes.data.coupons || couponsRes.data || [];
        this.coupons = couponsList.map((c: any) => ({
          id: c.id || 0,
          coupon_code: c.coupon_code || c.code || '',
          benefit_type: c.benefit_type || c.type || 'EV Discount',
          value: c.value || c.discount_value || 0,
          status: c.status || 'Available',
          created_at: c.created_at || c.issue_date || '',
          redeemed_at: c.redeemed_at || c.used_at || null
        }));

        this.stats = {
          total_coupons: couponsList.length,
          redeemed_coupons: couponsList.filter((c: any) => c.status?.toLowerCase() === 'redeemed' || c.status?.toLowerCase() === 'used').length,
          available_coupons: couponsList.filter((c: any) => c.status?.toLowerCase() === 'available' || c.status?.toLowerCase() === 'active').length,
          total_value_redeemed: couponsList
            .filter((c: any) => c.status?.toLowerCase() === 'redeemed' || c.status?.toLowerCase() === 'used')
            .reduce((sum: number, c: any) => sum + (c.value || 0), 0)
        };
      }
    } catch (error) {
      console.error('[MNRCoupons] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <style>
        ${MobileTable.getStyles()}
        .mnr-coupons-page { padding: 16px; }
        .coupons-summary {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 12px;
          margin-bottom: 16px;
        }
        .stat-card {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 12px;
          padding: 16px;
          text-align: center;
        }
        .stat-card.primary {
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          grid-column: span 2;
        }
        .stat-card .label {
          font-size: 11px;
          color: #8892b0;
          text-transform: uppercase;
          margin-bottom: 4px;
        }
        .stat-card.primary .label { color: rgba(255,255,255,0.8); }
        .stat-card .value {
          font-size: 24px;
          font-weight: 700;
          color: #e6f1ff;
        }
        .stat-card.primary .value { color: white; }
        .tab-bar {
          display: flex;
          gap: 8px;
          margin-bottom: 16px;
          overflow-x: auto;
          padding-bottom: 8px;
        }
        .tab-btn {
          padding: 8px 16px;
          background: rgba(22, 33, 62, 0.8);
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 20px;
          color: #8892b0;
          font-size: 13px;
          white-space: nowrap;
          cursor: pointer;
        }
        .tab-btn.active {
          background: #64d2ff;
          border-color: #64d2ff;
          color: #0d1b2a;
          font-weight: 600;
        }
        .section-title {
          font-size: 16px;
          font-weight: 600;
          color: #e6f1ff;
          margin: 20px 0 12px;
        }
      </style>
      ${PageHeader.render({ title: 'EV Coupons', showBack: true })}
      <div class="mnr-coupons-page">
        <div id="summarySection"></div>
        
        <h3 class="section-title">Coupons</h3>
        <div class="tab-bar" id="tabBar">
          <button class="tab-btn ${this.activeTab === 'all' ? 'active' : ''}" data-tab="all">All</button>
          <button class="tab-btn ${this.activeTab === 'available' ? 'active' : ''}" data-tab="available">Available</button>
          <button class="tab-btn ${this.activeTab === 'redeemed' ? 'active' : ''}" data-tab="redeemed">Redeemed</button>
        </div>
        
        <div id="pageContent"></div>
      </div>
    `;
    this.attachListeners();
  }

  private attachListeners(): void {
    PageHeader.attachListeners({ title: 'EV Coupons', showBack: true });
    
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this.activeTab = btn.getAttribute('data-tab') || 'all';
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.updateContent();
      });
    });
  }

  private getFilteredCoupons(): EVCoupon[] {
    if (this.activeTab === 'all') return this.coupons;
    if (this.activeTab === 'available') return this.coupons.filter(c => 
      c.status.toLowerCase() === 'available' || c.status.toLowerCase() === 'active'
    );
    return this.coupons.filter(c => 
      c.status.toLowerCase() === 'redeemed' || c.status.toLowerCase() === 'used'
    );
  }

  private updateContent(): void {
    const summarySection = document.getElementById('summarySection');
    if (summarySection && this.stats) {
      summarySection.innerHTML = `
        <div class="coupons-summary">
          <div class="stat-card primary">
            <div class="label">Available Coupons</div>
            <div class="value">${this.stats.available_coupons}</div>
          </div>
          <div class="stat-card">
            <div class="label">Total Coupons</div>
            <div class="value">${this.stats.total_coupons}</div>
          </div>
          <div class="stat-card">
            <div class="label">Redeemed</div>
            <div class="value">${this.stats.redeemed_coupons}</div>
          </div>
        </div>
      `;
    }

    const content = document.getElementById('pageContent');
    if (!content) return;

    const filteredCoupons = this.getFilteredCoupons();

    const table = new MobileTable({
      columns: [
        { key: 'coupon_code', label: 'Coupon Code', render: (v) => `<strong>${v}</strong>` },
        { key: 'benefit_type', label: 'Benefit Type' },
        { key: 'value', label: 'Value', render: (v) => v > 0 ? `₹${v.toLocaleString()}` : '-' },
        { key: 'status', label: 'Status', render: (v) => this.getStatusBadge(v) },
        { key: 'created_at', label: 'Created', render: (v) => this.formatDate(v) },
        { key: 'redeemed_at', label: 'Redeemed', render: (v) => this.formatDate(v) }
      ],
      data: filteredCoupons,
      loading: this.loading,
      emptyMessage: 'No coupons found'
    });

    content.innerHTML = table.render();
  }

  private getStatusBadge(status: string): string {
    const s = status.toLowerCase();
    if (s === 'available' || s === 'active') return '<span class="badge badge-success">Available</span>';
    if (s === 'redeemed' || s === 'used') return '<span class="badge badge-info">Redeemed</span>';
    if (s === 'expired') return '<span class="badge badge-danger">Expired</span>';
    return `<span class="badge badge-secondary">${status}</span>`;
  }

  private formatDate(dateStr: string | null): string {
    if (!dateStr) return '-';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch {
      return dateStr;
    }
  }
}
