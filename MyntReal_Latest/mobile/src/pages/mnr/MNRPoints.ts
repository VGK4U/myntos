/**
 * MNR Points Page - Web Table Parity
 * DC Protocol: DC_MOBILE_MNR_POINTS_002
 * Exact web table for transactions: Type, Points, Description, Date
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';
import { MobileTable } from '../../components/MobileTable';

interface MemberData {
  name: string;
  mnr_id: string;
  activation_date: string | null;
  coupon_purchase_date: string | null;
  coupon_status: string | null;
}

interface PointsBalance {
  current_balance: number;
  initial_points: number;
  total_credited: number;
  total_consumed: number;
  receipt_no: string | null;
  package_name: string;
  expiry_date: string | null;
  activation_date: string | null;
  is_exception: boolean;
  is_coupon_paid: boolean;
  member: MemberData | null;
}

interface PointsTransaction {
  id: number;
  transaction_type: string;
  amount: number;
  balance_after: number;
  category_name: string;
  lead_id: number | null;
  description: string;
  created_at: string;
}

export class MNRPoints {
  private container: HTMLElement;
  private balance: PointsBalance | null = null;
  private transactions: PointsTransaction[] = [];
  private loading: boolean = true;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadPoints();
  }

  private async loadPoints(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const [balanceRes, transRes] = await Promise.all([
        apiService.get<any>('/myntreal/points/me'),
        apiService.get<any>('/myntreal/points/me/history')
      ]);

      if (balanceRes.success && balanceRes.data) {
        const d = balanceRes.data;
        const memberData = d.member || null;
        const activationDate = memberData?.activation_date || d.activation_date || null;
        const exceptionCutoff = new Date('2025-12-01');
        const isException = activationDate ? new Date(activationDate) < exceptionCutoff : false;
        const isCouponPaid = d.is_coupon_paid || (memberData && memberData.is_coupon_paid) || false;

        this.balance = {
          current_balance: d.current_balance || 0,
          initial_points: d.initial_points || 0,
          total_credited: d.total_credited || 0,
          total_consumed: d.total_consumed || 0,
          receipt_no: d.receipt_no || null,
          package_name: d.package_name || 'None',
          expiry_date: d.expiry_date || null,
          activation_date: activationDate,
          is_exception: isException,
          is_coupon_paid: isCouponPaid,
          member: memberData ? {
            name: memberData.name || '',
            mnr_id: memberData.mnr_id || '',
            activation_date: memberData.activation_date || null,
            coupon_purchase_date: memberData.coupon_purchase_date || null,
            coupon_status: memberData.coupon_status || null
          } : null
        };
      }

      if (transRes.success && transRes.data) {
        const txns = transRes.data.transactions || transRes.data || [];
        this.transactions = txns.map((t: any) => ({
          id: t.id || 0,
          transaction_type: t.transaction_type || t.type || 'Credit',
          amount: t.amount || 0,
          balance_after: t.balance_after || 0,
          category_name: t.category_name || '',
          lead_id: t.lead_id || null,
          description: t.description || t.remarks || '',
          created_at: t.created_at || t.date || ''
        }));
      }
    } catch (error) {
      console.error('[MNRPoints] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <style>
        ${MobileTable.getStyles()}
        .mnr-points-page { padding: 16px; }
        .points-summary {
          display: grid;
          grid-template-columns: 1fr;
          gap: 12px;
          margin-bottom: 16px;
        }
        .balance-card {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          border-radius: 12px;
          padding: 20px;
          text-align: center;
          color: white;
        }
        .balance-card .label { font-size: 12px; opacity: 0.9; margin-bottom: 4px; }
        .balance-card .value { font-size: 36px; font-weight: 700; }
        .balance-card .package { font-size: 13px; margin-top: 8px; opacity: 0.8; }
        .points-breakdown {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 8px;
        }
        .points-stat {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 8px;
          padding: 12px;
          text-align: center;
        }
        .points-stat .label { font-size: 11px; color: #8892b0; text-transform: uppercase; }
        .points-stat .value { font-size: 18px; font-weight: 600; color: #e6f1ff; }
        .section-title {
          font-size: 16px;
          font-weight: 600;
          color: #e6f1ff;
          margin: 20px 0 12px;
        }
        .validity-section {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 10px;
          padding: 16px;
          margin-bottom: 16px;
          text-align: center;
        }
        .validity-section .title { color: #8892b0; font-size: 12px; margin-bottom: 4px; }
        .validity-section .expiry { color: #f59e0b; font-size: 14px; font-weight: 600; }
        .validity-section .remaining { color: #10b981; font-size: 16px; font-weight: 700; margin-top: 4px; }
        .exception-banner {
          background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
          border-radius: 10px;
          padding: 14px;
          margin-bottom: 16px;
          color: white;
          font-size: 12px;
          text-align: center;
        }
        .exception-banner .icon { font-size: 16px; margin-right: 6px; }
        .receipt-banner {
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          border-radius: 10px;
          padding: 14px;
          margin-bottom: 16px;
          color: white;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .receipt-banner .info { font-size: 13px; }
        .receipt-banner .receipt-no { font-weight: 700; font-size: 14px; }
        .btn-download {
          background: white;
          color: #059669;
          border: none;
          padding: 8px 14px;
          border-radius: 6px;
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 4px;
        }
        .available-points {
          background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
          border-radius: 12px;
          padding: 20px;
          text-align: center;
          color: white;
          margin-bottom: 16px;
        }
        .available-points .label { font-size: 12px; opacity: 0.9; margin-bottom: 4px; }
        .available-points .value { font-size: 36px; font-weight: 700; }
        .available-points .note { font-size: 11px; opacity: 0.8; margin-top: 8px; }
        .important-notice {
          background: rgba(220, 38, 38, 0.15);
          border-left: 4px solid #dc2626;
          padding: 14px 16px;
          border-radius: 8px;
          margin-bottom: 16px;
        }
        .important-notice h6 {
          color: #fca5a5;
          margin: 0 0 8px 0;
          font-weight: 600;
          font-size: 13px;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .important-notice ul {
          margin: 0;
          padding-left: 18px;
          color: #fca5a5;
          font-size: 12px;
        }
        .important-notice li { margin-bottom: 4px; }
        .important-notice strong { color: #fecaca; }
        .feedback-notice {
          background: rgba(234, 179, 8, 0.15);
          border-left: 4px solid #eab308;
          padding: 14px 16px;
          border-radius: 8px;
          margin-bottom: 16px;
        }
        .feedback-notice h6 {
          color: #fde68a;
          margin: 0 0 8px 0;
          font-weight: 600;
          font-size: 13px;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .feedback-notice p {
          color: #fde68a;
          font-size: 12px;
          margin: 0 0 8px 0;
        }
        .feedback-notice ul {
          margin: 0;
          padding-left: 18px;
          color: #fde68a;
          font-size: 12px;
        }
        .feedback-notice li { margin-bottom: 3px; }
        .feedback-notice .consent-note {
          color: #fbbf24;
          font-size: 11px;
          font-style: italic;
          margin-top: 10px;
          margin-bottom: 0;
        }
        .feedback-notice strong { color: #fef3c7; }
        .zynova-roles {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
          margin-bottom: 16px;
        }
        .zynova-role-card {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 10px;
          padding: 16px;
          text-align: center;
        }
        .zynova-role-card.real-estate { border-left: 3px solid #3b82f6; }
        .zynova-role-card.insurance { border-left: 3px solid #ef4444; }
        .zynova-role-card .segment-icon { font-size: 22px; margin-bottom: 6px; }
        .zynova-role-card .segment-name { font-size: 11px; color: #8892b0; margin-bottom: 4px; }
        .zynova-role-card .role-name { font-size: 14px; font-weight: 700; color: #e6f1ff; }
        .utilisation-chart {
          display: flex;
          align-items: center;
          gap: 16px;
          padding: 16px;
          background: rgba(22, 33, 62, 0.8);
          border-radius: 12px;
          margin-bottom: 16px;
        }
        .chart-circle {
          width: 100px;
          height: 100px;
          border-radius: 50%;
          background: conic-gradient(#059669 0deg, #059669 var(--used-deg), rgba(255,255,255,0.15) var(--used-deg), rgba(255,255,255,0.15) 360deg);
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
          flex-shrink: 0;
        }
        .chart-circle::before {
          content: '';
          position: absolute;
          width: 68px;
          height: 68px;
          background: rgba(10, 25, 47, 0.95);
          border-radius: 50%;
        }
        .chart-circle .percent {
          position: relative;
          z-index: 1;
          font-size: 16px;
          font-weight: 700;
          color: #e6f1ff;
        }
        .chart-legend { flex: 1; }
        .legend-item {
          display: flex;
          align-items: center;
          margin-bottom: 10px;
        }
        .legend-dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          margin-right: 8px;
          flex-shrink: 0;
        }
        .legend-dot.used { background: #059669; }
        .legend-dot.available { background: rgba(255,255,255,0.15); }
        .legend-text { flex: 1; color: #8892b0; font-size: 12px; }
        .legend-value { font-weight: 600; color: #e6f1ff; font-size: 13px; }
        .payment-slip-section {
          margin-top: 12px;
        }
        .payment-slip-buttons {
          display: flex;
          gap: 8px;
          justify-content: center;
          flex-wrap: wrap;
        }
        .btn-receipt-pdf {
          background: linear-gradient(135deg, #059669, #047857);
          border: none;
          color: white;
          border-radius: 8px;
          padding: 10px 18px;
          font-weight: 600;
          font-size: 12px;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 6px;
        }
        .btn-receipt-print {
          background: linear-gradient(135deg, #2563eb, #1d4ed8);
          border: none;
          color: white;
          border-radius: 8px;
          padding: 10px 18px;
          font-weight: 600;
          font-size: 12px;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 6px;
        }
        .exemption-msg {
          background: rgba(16, 185, 129, 0.15);
          color: #6ee7b7;
          padding: 10px 16px;
          border-radius: 8px;
          font-weight: 500;
          font-size: 12px;
          text-align: center;
        }
        .motivational-msg {
          background: linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(217, 119, 6, 0.2));
          color: #fde68a;
          padding: 16px;
          border-radius: 10px;
          font-weight: 600;
          text-align: center;
          font-size: 14px;
        }
        .motivational-msg .sub {
          font-size: 11px;
          font-weight: 400;
          margin-top: 6px;
          opacity: 0.8;
        }
        .page-subtitle {
          font-size: 12px;
          color: #8892b0;
          margin-top: 2px;
          text-align: center;
        }
      </style>
      ${PageHeader.render({ title: '💰 Points Balance and Utilisation', showBack: true })}
      <div class="mnr-points-page">
        <p class="page-subtitle">Track your MNR Points across all systems</p>
        <div id="importantNotices"></div>
        <div id="summarySection"></div>
        <h3 class="section-title">Transactions History</h3>
        <div id="pageContent"></div>
      </div>
    `;
    PageHeader.attachListeners({ title: '💰 Points Balance and Utilisation', showBack: true });
  }

  private updateContent(): void {
    const noticesSection = document.getElementById('importantNotices');
    if (noticesSection) {
      noticesSection.innerHTML = `
        <div class="important-notice">
          <h6>⚠️ Important Information</h6>
          <ul>
            <li>Points are <strong>non-refundable</strong> and <strong>non-transferable</strong></li>
            <li>Validity: <strong>24 months</strong> from the activation date</li>
            <li>Unused credits expire automatically without refund</li>
          </ul>
        </div>
        <div class="feedback-notice">
          <h6>📹 Feedback Video and Photos Requirement</h6>
          <p><strong>For members activated before 1st Dec 2025 who received exemption:</strong> Sharing feedback videos and photos is mandatory to be eligible for incentives or points benefits.</p>
          <p style="margin-bottom: 6px;"><strong>Eligible Engagement Activities:</strong></p>
          <ul>
            <li>Reels (video content)</li>
            <li>WhatsApp Status sharing</li>
            <li>Social Media posts</li>
            <li>Sharing & Ratings in Announcement sections</li>
            <li>Engaging with teams</li>
            <li>Attending Zoom calls</li>
          </ul>
          <p class="consent-note">ℹ️ Please note: Submitted feedback videos and photos may be publicly displayed on our platforms for promotional and community engagement purposes. By sharing your content, you acknowledge and consent to this use.</p>
        </div>
      `;
    }

    const summarySection = document.getElementById('summarySection');
    if (summarySection && this.balance) {
      const expiryInfo = this.getExpiryInfo();

      const total = this.balance.initial_points + this.balance.total_credited;
      const used = this.balance.total_consumed;
      const usedPercent = total > 0 ? Math.round((used / total) * 100) : 0;
      const usedDeg = (usedPercent / 100) * 360;

      let paymentSlipHTML = '';
      if (this.balance.is_exception) {
        paymentSlipHTML = `
          <div class="payment-slip-section">
            <div class="exemption-msg">
              ℹ️ Exception Coupon (Activated before Dec 1, 2025) - Payment receipt not available
            </div>
          </div>
        `;
      } else if (this.balance.is_coupon_paid) {
        paymentSlipHTML = `
          <div class="payment-slip-section">
            <div class="payment-slip-buttons">
              <button class="btn-receipt-pdf" id="btnDownloadPdf">📄 Download Receipt (PDF)</button>
              <button class="btn-receipt-print" id="btnPrintReceipt">🖨️ Print Receipt</button>
            </div>
          </div>
        `;
      } else {
        paymentSlipHTML = `
          <div class="payment-slip-section">
            <div class="motivational-msg">
              🚀 Your take an opportunity for a great Journey
              <div class="sub">Apply a coupon to unlock full benefits and download your payment receipt</div>
            </div>
          </div>
        `;
      }

      summarySection.innerHTML = `
        <div class="points-summary">
          <div class="balance-card">
            <div class="label">Current Balance</div>
            <div class="value">${this.balance.current_balance.toLocaleString()}</div>
            <div class="package">${this.balance.package_name} Package</div>
          </div>
          
          ${this.balance.expiry_date ? `
            <div class="validity-section">
              <div class="title">Points Validity Status</div>
              <div class="expiry">Expires: ${expiryInfo.formatted}</div>
              <div class="remaining">${expiryInfo.remaining}</div>
            </div>
          ` : ''}

          <div class="zynova-roles">
            <div class="zynova-role-card real-estate">
              <div class="segment-icon">🏢</div>
              <div class="segment-name">VGK Real Dreams</div>
              <div class="role-name">-</div>
            </div>
            <div class="zynova-role-card insurance">
              <div class="segment-icon">🛡️</div>
              <div class="segment-name">VGK Care</div>
              <div class="role-name">-</div>
            </div>
          </div>
          
          <div class="available-points">
            <div class="label">Available MNR Points</div>
            <div class="value">${this.balance.current_balance.toLocaleString()}</div>
            <div class="note">Points can be used for incentives across all MyntReal systems</div>
            ${paymentSlipHTML}
          </div>
          
          ${this.balance.receipt_no ? `
            <div class="receipt-banner">
              <div class="info">
                <div>Payment Receipt Available</div>
                <div class="receipt-no">Receipt: ${this.balance.receipt_no}</div>
              </div>
              <button class="btn-download" id="btnDownloadReceipt">
                📄 Download
              </button>
            </div>
          ` : ''}
          
          <div class="points-breakdown">
            <div class="points-stat">
              <div class="label">Initial</div>
              <div class="value">${this.balance.initial_points.toLocaleString()}</div>
            </div>
            <div class="points-stat">
              <div class="label">Credited</div>
              <div class="value" style="color: #10b981;">+${this.balance.total_credited.toLocaleString()}</div>
            </div>
            <div class="points-stat">
              <div class="label">Consumed</div>
              <div class="value" style="color: #ef4444;">-${this.balance.total_consumed.toLocaleString()}</div>
            </div>
          </div>

          <div class="section-title" style="margin-top: 16px;">📊 Points Utilisation</div>
          <div class="utilisation-chart" style="--used-deg: ${usedDeg}deg;">
            <div class="chart-circle" style="--used-deg: ${usedDeg}deg;">
              <span class="percent">${usedPercent}%</span>
            </div>
            <div class="chart-legend">
              <div class="legend-item">
                <div class="legend-dot used"></div>
                <span class="legend-text">Points Used</span>
                <span class="legend-value">${used.toLocaleString()}</span>
              </div>
              <div class="legend-item">
                <div class="legend-dot available"></div>
                <span class="legend-text">Points Available</span>
                <span class="legend-value">${this.balance.current_balance.toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>
      `;
      
      const downloadBtn = document.getElementById('btnDownloadReceipt');
      if (downloadBtn) {
        downloadBtn.addEventListener('click', () => this.downloadReceipt());
      }

      const pdfBtn = document.getElementById('btnDownloadPdf');
      if (pdfBtn) {
        pdfBtn.addEventListener('click', () => this.downloadReceipt());
      }

      const printBtn = document.getElementById('btnPrintReceipt');
      if (printBtn) {
        printBtn.addEventListener('click', () => this.printReceipt());
      }
    }

    const content = document.getElementById('pageContent');
    if (!content) return;

    const table = new MobileTable({
      columns: [
        { key: 'transaction_type', label: 'Type', render: (v) => this.getTypeBadge(v) },
        { key: 'amount', label: 'Amount', render: (v, row) => {
          const type = row.transaction_type.toLowerCase();
          const isDebit = type.includes('debit') || type.includes('consume') || type.includes('redeem') || type.includes('used') || type.includes('consumption');
          const isCredit = type.includes('credit') || type.includes('allocation') || type.includes('bonus') || type.includes('reward') || type.includes('initial');
          let color = '#e6f1ff';
          let sign = '';
          if (isDebit || v < 0) {
            color = '#ef4444';
            sign = v > 0 ? '-' : '';
          } else if (isCredit || v >= 0) {
            color = '#10b981';
            sign = v < 0 ? '' : '+';
          }
          return `<span style="color: ${color}; font-weight: 600;">${sign}${Math.abs(v).toLocaleString()}</span>`;
        }},
        { key: 'balance_after', label: 'Balance', render: (v) => `<span style="color: #e6f1ff;">${(v || 0).toLocaleString()}</span>` },
        { key: 'description', label: 'Description' },
        { key: 'created_at', label: 'Date', render: (v) => this.formatDate(v) }
      ],
      data: this.transactions,
      loading: this.loading,
      emptyMessage: 'No transactions yet'
    });

    content.innerHTML = `
      <div class="table-summary-bar">
        <span>Total <span class="count">${this.transactions.length}</span> transactions</span>
      </div>
      ${table.render()}
    `;
  }

  private getTypeBadge(type: string): string {
    const t = type.toLowerCase();
    if (t.includes('credit') || t.includes('allocation') || t.includes('bonus') || t.includes('reward') || t.includes('initial')) {
      return '<span class="badge badge-success">Credit</span>';
    }
    if (t.includes('debit') || t.includes('consume') || t.includes('redeem') || t.includes('used')) {
      return '<span class="badge badge-danger">Debit</span>';
    }
    if (t.includes('consumption')) {
      return '<span class="badge badge-warning" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24;">Consumption</span>';
    }
    return `<span class="badge badge-secondary">${type}</span>`;
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

  private getExpiryInfo(): { formatted: string; remaining: string } {
    if (!this.balance?.expiry_date) {
      return { formatted: 'Not set', remaining: '' };
    }
    
    try {
      const expiry = new Date(this.balance.expiry_date);
      const now = new Date();
      const diffMs = expiry.getTime() - now.getTime();
      
      if (diffMs <= 0) {
        return { 
          formatted: expiry.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' }),
          remaining: 'Expired' 
        };
      }
      
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
      const months = Math.floor(diffDays / 30);
      const days = diffDays % 30;
      
      let remaining = '';
      if (months > 0) remaining += `${months} month${months > 1 ? 's' : ''} `;
      if (days > 0) remaining += `${days} day${days > 1 ? 's' : ''} `;
      remaining += 'remaining';
      
      return {
        formatted: expiry.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' }),
        remaining
      };
    } catch {
      return { formatted: 'Invalid', remaining: '' };
    }
  }

  private async downloadReceipt(): Promise<void> {
    if (!this.balance?.receipt_no && !this.balance?.is_coupon_paid) {
      alert('No receipt available');
      return;
    }
    
    try {
      const baseUrl = apiService.getBaseUrl();
      const token = apiService.getToken();
      const receiptUrl = `${baseUrl}/receipt/membership-receipt`;
      const link = document.createElement('a');
      link.href = receiptUrl;
      link.target = '_blank';
      link.click();
    } catch (error) {
      const receiptInfo = this.balance?.receipt_no ? `Receipt: ${this.balance.receipt_no}\n\n` : '';
      alert(receiptInfo + 'PDF download will be available soon.');
    }
  }

  private async printReceipt(): Promise<void> {
    try {
      const baseUrl = apiService.getBaseUrl();
      const receiptUrl = `${baseUrl}/receipt/membership-receipt`;
      const printWindow = window.open(receiptUrl, '_blank');
      if (printWindow) {
        printWindow.onload = () => printWindow.print();
      }
    } catch (error) {
      alert('Print receipt will be available soon.');
    }
  }
}
