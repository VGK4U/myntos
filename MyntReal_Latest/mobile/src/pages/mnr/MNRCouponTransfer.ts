/**
 * MNR Coupon Transfer Page - Web Table Parity
 * DC Protocol: DC_MOBILE_MNR_COUPON_TRANSFER_002
 * Transfer PINs to other members with table format
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
}

interface TransferHistory {
  id: number;
  coupon_code: string;
  from_user: string;
  to_user: string;
  status: string;
  created_at: string;
  approved_at: string | null;
}

export class MNRCouponTransfer {
  private container: HTMLElement;
  private transferablePins: Pin[] = [];
  private transferHistory: TransferHistory[] = [];
  private loading: boolean = true;
  private selectedPin: string | null = null;
  private recipientId: string = '';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadData();
  }

  private async loadData(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const [pinsRes, historyRes] = await Promise.all([
        apiService.get<any>('/users/pins'),
        apiService.get<any>('/coupon-transfers/my-transfer-history')
      ]);

      if (pinsRes.success && pinsRes.data) {
        const allPins = pinsRes.data.pins || [];
        this.transferablePins = allPins.filter((p: any) => 
          p.status === 'Active' || p.status === 'Available'
        ).map((p: any) => ({
          id: p.id || '',
          coupon_code: p.coupon_code || p.code || '',
          coupon_type: p.coupon_type || p.package_type || 'Standard',
          status: p.status || 'Active',
          amount: p.amount || p.value || 0
        }));
      }

      if (historyRes.success && historyRes.data) {
        const transfers = historyRes.data.transfers || historyRes.data || [];
        this.transferHistory = transfers.map((t: any) => ({
          id: t.id || 0,
          coupon_code: t.coupon_code || t.code || '',
          from_user: t.from_user_name || t.from_user_id || '-',
          to_user: t.to_user_name || t.to_user_id || '-',
          status: t.status || 'Pending',
          created_at: t.created_at || '',
          approved_at: t.approved_at || null
        }));
      }
    } catch (error) {
      console.error('[MNRCouponTransfer] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <style>
        ${MobileTable.getStyles()}
        .coupon-transfer-page { padding: 16px; }
        
        .transfer-form {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 20px;
        }
        .transfer-form h4 {
          color: #e6f1ff;
          margin: 0 0 16px;
          font-size: 15px;
        }
        .form-group {
          margin-bottom: 16px;
        }
        .form-group label {
          display: block;
          font-size: 12px;
          color: #8892b0;
          text-transform: uppercase;
          margin-bottom: 8px;
        }
        .form-group select, .form-group input {
          width: 100%;
          padding: 12px;
          border-radius: 8px;
          border: 1px solid rgba(255,255,255,0.1);
          background: rgba(13, 27, 42, 0.8);
          color: #e6f1ff;
          font-size: 14px;
        }
        .form-group select:focus, .form-group input:focus {
          outline: none;
          border-color: #64d2ff;
        }
        .btn-transfer {
          width: 100%;
          padding: 14px;
          border-radius: 8px;
          border: none;
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          color: white;
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
        }
        .btn-transfer:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        
        .available-pins {
          background: rgba(16, 185, 129, 0.1);
          border: 1px solid rgba(16, 185, 129, 0.3);
          border-radius: 10px;
          padding: 14px;
          margin-bottom: 20px;
          text-align: center;
        }
        .available-pins .count {
          font-size: 28px;
          font-weight: 700;
          color: #10b981;
        }
        .available-pins .label {
          font-size: 12px;
          color: #8892b0;
        }
        
        .section-title {
          font-size: 15px;
          font-weight: 600;
          color: #e6f1ff;
          margin: 20px 0 12px;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        
        .notice {
          background: rgba(251, 191, 36, 0.1);
          border: 1px solid rgba(251, 191, 36, 0.3);
          border-radius: 8px;
          padding: 12px;
          margin-bottom: 16px;
          font-size: 12px;
          color: #fbbf24;
        }
      </style>
      ${PageHeader.render({ title: '🔄 Transfer Coupon', showBack: true })}
      <div class="coupon-transfer-page" id="pageContent">
        <div class="loading-state" style="text-align: center; padding: 40px; color: #8892b0;">Loading...</div>
      </div>
    `;

    PageHeader.attachListeners({ title: '🔄 Transfer Coupon', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state" style="text-align: center; padding: 40px; color: #8892b0;">Loading...</div>';
      return;
    }

    const historyTable = new MobileTable({
      columns: [
        { key: 'coupon_code', label: 'Coupon', render: (v) => `<strong>${v}</strong>` },
        { key: 'to_user', label: 'To User' },
        { key: 'status', label: 'Status', render: (v) => this.getStatusBadge(v) },
        { key: 'created_at', label: 'Requested', render: (v) => this.formatDate(v) },
        { key: 'approved_at', label: 'Approved', render: (v) => this.formatDate(v) }
      ],
      data: this.transferHistory,
      emptyMessage: 'No transfer history'
    });

    content.innerHTML = `
      <div class="available-pins">
        <div class="count">${this.transferablePins.length}</div>
        <div class="label">Available Coupons for Transfer</div>
      </div>

      ${this.transferablePins.length > 0 ? `
        <div class="transfer-form">
          <h4>🔄 Transfer a Coupon</h4>
          <div class="notice">
            ⚠️ Transfer requests require admin approval. The coupon will be transferred after approval.
          </div>
          <div class="form-group">
            <label>Select Coupon</label>
            <select id="pinSelect">
              <option value="">-- Select a coupon --</option>
              ${this.transferablePins.map(p => `
                <option value="${p.id}">${p.coupon_code} (${p.coupon_type})</option>
              `).join('')}
            </select>
          </div>
          <div class="form-group">
            <label>Recipient MNR ID</label>
            <input type="text" id="recipientInput" placeholder="Enter recipient's MNR ID" value="${this.recipientId}" />
          </div>
          <button class="btn-transfer" id="transferBtn" ${!this.selectedPin || !this.recipientId ? 'disabled' : ''}>
            Request Transfer
          </button>
        </div>
      ` : `
        <div class="notice">
          You don't have any active coupons available for transfer.
        </div>
      `}

      <div class="section-title">📋 Transfer History</div>
      
      <div class="table-summary-bar">
        <span>Total <span class="count">${this.transferHistory.length}</span> transfers</span>
      </div>
      ${historyTable.render()}
    `;

    this.attachListeners();
  }

  private attachListeners(): void {
    const pinSelect = document.getElementById('pinSelect') as HTMLSelectElement;
    const recipientInput = document.getElementById('recipientInput') as HTMLInputElement;
    const transferBtn = document.getElementById('transferBtn') as HTMLButtonElement;

    pinSelect?.addEventListener('change', () => {
      this.selectedPin = pinSelect.value || null;
      this.updateButtonState();
    });

    recipientInput?.addEventListener('input', () => {
      this.recipientId = recipientInput.value.trim();
      this.updateButtonState();
    });

    transferBtn?.addEventListener('click', () => this.requestTransfer());
  }

  private updateButtonState(): void {
    const btn = document.getElementById('transferBtn') as HTMLButtonElement;
    if (btn) {
      btn.disabled = !this.selectedPin || !this.recipientId;
    }
  }

  private async requestTransfer(): Promise<void> {
    if (!this.selectedPin || !this.recipientId) return;

    try {
      const response = await apiService.post<any>('/coupon-transfers/user-to-user', {
        coupon_id: this.selectedPin,
        to_user_id: this.recipientId
      });

      if (response.success) {
        alert('Transfer request submitted successfully!');
        this.selectedPin = null;
        this.recipientId = '';
        await this.loadData();
      } else {
        alert(response.error || 'Failed to submit transfer request');
      }
    } catch (error) {
      console.error('[MNRCouponTransfer] Transfer failed:', error);
      alert('Failed to submit transfer request');
    }
  }

  private getStatusBadge(status: string): string {
    const s = status.toLowerCase();
    if (s === 'approved' || s === 'completed') return '<span class="badge badge-success">Approved</span>';
    if (s === 'pending') return '<span class="badge badge-warning">Pending</span>';
    if (s === 'rejected') return '<span class="badge badge-danger">Rejected</span>';
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
