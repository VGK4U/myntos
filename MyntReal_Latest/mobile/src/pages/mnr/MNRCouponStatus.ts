/**
 * MNR Coupon Status Page - Web Table Parity
 * DC Protocol: DC_MOBILE_MNR_COUPON_STATUS_002
 * View all PIN/Coupon status with proper table format
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';
import { MobileTable } from '../../components/MobileTable';

interface Pin {
  id: string;
  coupon_code: string;
  coupon_type: string;
  status: string;
  amount: number;
  created_at: string;
  activated_at: string | null;
  used_by: string;
  activated_for: string;
}

interface PinSummary {
  total_pins: number;
  active_pins: number;
  used_pins: number;
}

export class MNRCouponStatus {
  private container: HTMLElement;
  private pins: Pin[] = [];
  private summary: PinSummary = { total_pins: 0, active_pins: 0, used_pins: 0 };
  private loading: boolean = true;
  private activeTab: string = 'all';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadPins();
  }

  private async loadPins(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<any>('/users/pins');
      if (response.success && response.data) {
        const rawPins = response.data.pins || response.data || [];
        this.pins = rawPins.map((p: any) => ({
          id: p.id || '',
          coupon_code: p.coupon_code || p.code || p.pin_code || '',
          coupon_type: p.coupon_type || p.package_type || p.type || 'Standard',
          status: p.status || 'Active',
          amount: p.amount || p.value || 0,
          created_at: p.created_at || '',
          activated_at: p.activated_at || p.used_at || null,
          used_by: p.used_by || p.activated_by || '-',
          activated_for: p.activated_for || p.used_for || '-'
        }));
        this.calculateSummary();
      }
    } catch (error) {
      console.error('[MNRCouponStatus] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private calculateSummary(): void {
    this.summary = {
      total_pins: this.pins.length,
      active_pins: this.pins.filter(p => p.status.toLowerCase() === 'active' || p.status.toLowerCase() === 'available').length,
      used_pins: this.pins.filter(p => p.status.toLowerCase() === 'used' || p.status.toLowerCase() === 'activated').length
    };
  }

  private getFilteredPins(): Pin[] {
    if (this.activeTab === 'all') return this.pins;
    if (this.activeTab === 'active') return this.pins.filter(p => p.status.toLowerCase() === 'active' || p.status.toLowerCase() === 'available');
    return this.pins.filter(p => p.status.toLowerCase() === 'used' || p.status.toLowerCase() === 'activated');
  }

  private render(): void {
    this.container.innerHTML = `
      <style>
        ${MobileTable.getStyles()}
        .coupon-status-page { padding: 16px; }
        
        .summary-row {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 10px;
          margin-bottom: 16px;
        }
        .summary-card {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 10px;
          padding: 14px;
          text-align: center;
        }
        .summary-card .label {
          font-size: 10px;
          color: #8892b0;
          text-transform: uppercase;
          margin-bottom: 4px;
        }
        .summary-card .value {
          font-size: 22px;
          font-weight: 700;
          color: #e6f1ff;
        }
        .summary-card:nth-child(2) .value { color: #10b981; }
        .summary-card:nth-child(3) .value { color: #3b82f6; }
        
        .tab-bar {
          display: flex;
          gap: 8px;
          margin-bottom: 16px;
        }
        .tab-btn {
          flex: 1;
          padding: 10px;
          background: rgba(22, 33, 62, 0.8);
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 8px;
          color: #8892b0;
          font-size: 13px;
          cursor: pointer;
          text-align: center;
        }
        .tab-btn.active {
          background: #64d2ff;
          border-color: #64d2ff;
          color: #0d1b2a;
          font-weight: 600;
        }
      </style>
      ${PageHeader.render({ title: '🎫 My Coupons', showBack: true })}
      <div class="coupon-status-page" id="pageContent">
        <div class="loading-state" style="text-align: center; padding: 40px; color: #8892b0;">Loading...</div>
      </div>
    `;

    PageHeader.attachListeners({ title: '🎫 My Coupons', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state" style="text-align: center; padding: 40px; color: #8892b0;">Loading...</div>';
      return;
    }

    const filteredPins = this.getFilteredPins();

    const table = new MobileTable({
      columns: [
        { key: 'coupon_code', label: 'Coupon Code', render: (v) => `<strong>${v}</strong>` },
        { key: 'coupon_type', label: 'Type' },
        { key: 'amount', label: 'Amount', render: (v) => v > 0 ? `₹${v.toLocaleString()}` : '-' },
        { key: 'status', label: 'Status', render: (v) => this.getStatusBadge(v) },
        { key: 'activated_for', label: 'Used For' },
        { key: 'created_at', label: 'Created', render: (v) => this.formatDate(v) },
        { key: 'activated_at', label: 'Activated', render: (v) => this.formatDate(v) }
      ],
      data: filteredPins,
      emptyMessage: 'No coupons found'
    });

    content.innerHTML = `
      <div class="summary-row">
        <div class="summary-card">
          <div class="label">Total</div>
          <div class="value">${this.summary.total_pins}</div>
        </div>
        <div class="summary-card">
          <div class="label">Active</div>
          <div class="value">${this.summary.active_pins}</div>
        </div>
        <div class="summary-card">
          <div class="label">Used</div>
          <div class="value">${this.summary.used_pins}</div>
        </div>
      </div>

      <div class="tab-bar">
        <button class="tab-btn ${this.activeTab === 'all' ? 'active' : ''}" data-tab="all">All</button>
        <button class="tab-btn ${this.activeTab === 'active' ? 'active' : ''}" data-tab="active">Active</button>
        <button class="tab-btn ${this.activeTab === 'used' ? 'active' : ''}" data-tab="used">Used</button>
      </div>

      <div class="table-summary-bar">
        <span>Showing <span class="count">${filteredPins.length}</span> coupons</span>
      </div>
      ${table.render()}
    `;

    this.attachListeners();
  }

  private attachListeners(): void {
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this.activeTab = btn.getAttribute('data-tab') || 'all';
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.updateContent();
      });
    });
  }

  private getStatusBadge(status: string): string {
    const s = status.toLowerCase();
    if (s === 'active' || s === 'available') return '<span class="badge badge-success">Active</span>';
    if (s === 'used' || s === 'activated') return '<span class="badge badge-info">Used</span>';
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
