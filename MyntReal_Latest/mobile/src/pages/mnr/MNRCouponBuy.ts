/**
 * MNR Coupon Buy Page - Web Parity
 * DC Protocol: DC_MOBILE_MNR_COUPON_BUY_002
 * Purchase PINs/Coupons - matches web Buy Coupon functionality
 * Only Platinum (₹15,000) and Diamond (₹7,500) packages available for purchase
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';
import { MobileTable } from '../../components/MobileTable';
import { Camera, CameraResultType, CameraSource } from '@capacitor/camera';

interface PinPackage {
  type: string;
  price: number;
  name: string;
  description: string;
  directBonus: string;
  icon: string;
  color: string;
}

interface PurchaseRequest {
  id: number;
  package_type: string;
  quantity: number;
  amount_paid: number;
  status: string;
  created_at: string;
  transaction_id: string;
}

const PIN_PACKAGES: PinPackage[] = [
  { 
    type: 'Platinum', 
    price: 15000, 
    name: 'Platinum Package', 
    description: 'Maximum benefits, best value',
    directBonus: '₹3,000 direct referral bonus',
    icon: '👑',
    color: '#f59e0b'
  },
  { 
    type: 'Diamond', 
    price: 7500, 
    name: 'Diamond Package', 
    description: 'Great value, excellent benefits',
    directBonus: '₹1,500 direct referral bonus (up to 2x)',
    icon: '💎',
    color: '#06b6d4'
  }
];

const PAYMENT_MODES = [
  'Google Pay',
  'PhonePe',
  'Paytm',
  'Bank Transfer (NEFT/RTGS/IMPS)',
  'UPI',
  'Cash Deposit',
  'Other'
];

export class MNRCouponBuy {
  private container: HTMLElement;
  private purchaseRequests: PurchaseRequest[] = [];
  private loading: boolean = true;
  private submitting: boolean = false;
  private selectedPackage: string | null = null;
  private quantity: number = 1;
  private transactionId: string = '';
  private transactionDate: string = new Date().toISOString().split('T')[0];
  private paymentMode: string = '';
  private screenshotFile: File | null = null;
  private screenshotPreview: string = '';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadPurchaseHistory();
  }

  private async loadPurchaseHistory(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<any>('/users/pins/purchase-requests');
      if (response.success && response.data) {
        this.purchaseRequests = (response.data.requests || response.data || []).map((r: any) => ({
          id: r.id || 0,
          package_type: r.package_type || r.type || '',
          quantity: r.quantity || 1,
          amount_paid: r.amount_paid || r.amount || 0,
          status: r.status || 'Pending',
          created_at: r.created_at || '',
          transaction_id: r.transaction_id || ''
        }));
      }
    } catch (error) {
      console.error('[MNRCouponBuy] Failed to load history:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <style>
        ${MobileTable.getStyles()}
        .coupon-buy-page { padding: 16px; }
        
        .info-banner {
          background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
          color: white;
        }
        .info-banner h4 { margin: 0 0 8px; font-size: 15px; }
        .info-banner p { margin: 0; font-size: 13px; opacity: 0.9; line-height: 1.5; }
        
        .payment-scanner-card {
          background: linear-gradient(135deg, #f8fff8 0%, #d1fae5 100%);
          border: 2px solid #10b981;
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
          text-align: center;
        }
        .payment-scanner-card h5 {
          color: #059669;
          margin: 0 0 12px;
          font-size: 14px;
        }
        .scanner-notice {
          background: #fef3c7;
          border-radius: 8px;
          padding: 10px;
          margin-top: 12px;
          font-size: 12px;
          color: #92400e;
        }
        
        .section-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin: 20px 0 12px;
          font-size: 15px;
          font-weight: 600;
          color: #e6f1ff;
        }
        
        .packages-grid {
          display: grid;
          gap: 12px;
        }
        
        .package-card {
          background: rgba(22, 33, 62, 0.8);
          border: 2px solid rgba(255,255,255,0.1);
          border-radius: 12px;
          padding: 16px;
          cursor: pointer;
          transition: all 0.2s;
        }
        .package-card:hover {
          border-color: rgba(100, 210, 255, 0.5);
          transform: translateY(-2px);
        }
        .package-card.selected {
          border-color: #64d2ff;
          background: rgba(100, 210, 255, 0.1);
        }
        .package-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }
        .package-icon { font-size: 24px; }
        .package-name {
          font-size: 16px;
          font-weight: 600;
          color: #e6f1ff;
        }
        .package-price {
          font-size: 20px;
          font-weight: 700;
          color: #10b981;
        }
        .package-desc {
          font-size: 13px;
          color: #8892b0;
          margin: 0 0 8px;
        }
        .package-bonus {
          display: inline-block;
          background: rgba(16, 185, 129, 0.2);
          color: #10b981;
          padding: 4px 10px;
          border-radius: 20px;
          font-size: 12px;
          font-weight: 500;
        }
        
        .purchase-form {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 12px;
          padding: 16px;
          margin-top: 16px;
        }
        .purchase-form h4 {
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
        .quantity-selector {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .qty-btn {
          width: 40px;
          height: 40px;
          border-radius: 8px;
          border: 1px solid rgba(100, 210, 255, 0.3);
          background: rgba(100, 210, 255, 0.1);
          color: #64d2ff;
          font-size: 20px;
          cursor: pointer;
        }
        .qty-btn:active {
          background: rgba(100, 210, 255, 0.2);
        }
        .quantity-selector input {
          width: 60px;
          text-align: center;
          padding: 8px;
          border-radius: 8px;
          border: 1px solid rgba(255,255,255,0.1);
          background: rgba(13, 27, 42, 0.8);
          color: #e6f1ff;
          font-size: 16px;
        }
        .total-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 0;
          border-top: 1px solid rgba(255,255,255,0.1);
        }
        .total-label { color: #8892b0; font-size: 14px; }
        .total-amount { color: #10b981; font-size: 24px; font-weight: 700; }
        
        .payment-notice {
          background: rgba(251, 191, 36, 0.1);
          border: 1px solid rgba(251, 191, 36, 0.3);
          border-radius: 8px;
          padding: 12px;
          margin-top: 16px;
          font-size: 13px;
          color: #fbbf24;
        }
        
        .history-section { margin-top: 24px; }
        
        .form-input, .form-select {
          width: 100%;
          padding: 12px;
          border-radius: 8px;
          border: 1px solid rgba(255,255,255,0.15);
          background: rgba(13, 27, 42, 0.8);
          color: #e6f1ff;
          font-size: 14px;
        }
        .form-input:focus, .form-select:focus {
          outline: none;
          border-color: #64d2ff;
        }
        .form-row {
          display: flex;
          gap: 12px;
        }
        .form-group.half {
          flex: 1;
        }
        
        .screenshot-upload {
          background: rgba(13, 27, 42, 0.8);
          border: 2px dashed rgba(255,255,255,0.2);
          border-radius: 12px;
          padding: 20px;
          cursor: pointer;
          text-align: center;
          transition: border-color 0.2s;
        }
        .screenshot-upload:hover {
          border-color: #64d2ff;
        }
        .upload-placeholder span {
          font-size: 32px;
          display: block;
          margin-bottom: 8px;
        }
        .upload-placeholder p {
          color: #8892b0;
          margin: 0 0 4px;
          font-size: 14px;
        }
        .upload-placeholder small {
          color: #5a6a8a;
          font-size: 12px;
        }
        .screenshot-preview {
          position: relative;
        }
        .screenshot-preview img {
          max-width: 100%;
          max-height: 200px;
          border-radius: 8px;
        }
        .remove-screenshot {
          position: absolute;
          top: 8px;
          right: 8px;
          width: 28px;
          height: 28px;
          border-radius: 50%;
          background: rgba(239, 68, 68, 0.9);
          color: white;
          border: none;
          font-size: 16px;
          cursor: pointer;
        }
        
        .approval-workflow {
          background: rgba(251, 191, 36, 0.1);
          border: 1px solid rgba(251, 191, 36, 0.3);
          border-radius: 8px;
          padding: 12px;
          margin: 16px 0;
        }
        .approval-workflow h5 {
          color: #fbbf24;
          margin: 0 0 8px;
          font-size: 14px;
        }
        .approval-workflow ol {
          margin: 0;
          padding-left: 20px;
          color: #d1d5db;
          font-size: 12px;
          line-height: 1.6;
        }
        
        .submit-btn {
          width: 100%;
          padding: 14px;
          font-size: 16px;
          font-weight: 600;
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          color: white;
          border: none;
          border-radius: 10px;
          cursor: pointer;
          margin-top: 8px;
        }
        .submit-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
      </style>
      ${PageHeader.render({ title: '🛒 Purchase Coupon', showBack: true })}
      <div class="coupon-buy-page" id="pageContent">
        <div class="loading-state">Loading...</div>
      </div>
    `;

    PageHeader.attachListeners({ title: '🛒 Purchase Coupon', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state" style="text-align: center; padding: 40px; color: #8892b0;">Loading...</div>';
      return;
    }

    content.innerHTML = `
      <div class="info-banner">
        <h4>Package Information</h4>
        <p>
          • <strong>Platinum (₹15,000)</strong>: Maximum benefits, ₹3,000 direct referral bonus<br>
          • <strong>Diamond (₹7,500)</strong>: Great value, ₹1,500 direct referral bonus (up to 2x)
        </p>
      </div>

      <div class="payment-scanner-card">
        <h5>🔒 Payment Scanner - Verify Before Payment</h5>
        <p style="font-size: 13px; color: #374151; margin: 0;">
          Please verify the company name <strong>"MNR MEGA NATURAL RESOURCES"</strong> before making payment
        </p>
        <div class="scanner-notice">
          ⚠️ Make payment to the company bank account and upload payment screenshot as proof
        </div>
      </div>

      <div class="section-header">
        <span>📦</span> Select Package
      </div>
      
      <div class="packages-grid">
        ${PIN_PACKAGES.map(pkg => `
          <div class="package-card ${this.selectedPackage === pkg.type ? 'selected' : ''}" data-type="${pkg.type}">
            <div class="package-header">
              <div>
                <span class="package-icon">${pkg.icon}</span>
                <span class="package-name">${pkg.name}</span>
              </div>
              <span class="package-price">₹${pkg.price.toLocaleString()}</span>
            </div>
            <p class="package-desc">${pkg.description}</p>
            <span class="package-bonus">${pkg.directBonus}</span>
          </div>
        `).join('')}
      </div>

      ${this.selectedPackage ? this.renderPurchaseForm() : ''}

      ${this.purchaseRequests.length > 0 ? this.renderHistory() : ''}
    `;

    this.attachListeners();
  }

  private renderPurchaseForm(): string {
    const pkg = PIN_PACKAGES.find(p => p.type === this.selectedPackage);
    if (!pkg) return '';

    const totalAmount = pkg.price * this.quantity;

    return `
      <div class="purchase-form">
        <h4>Purchase Details</h4>
        
        <div class="form-row">
          <div class="form-group">
            <label>Quantity</label>
            <div class="quantity-selector">
              <button class="qty-btn" id="decreaseQty">-</button>
              <input type="number" id="quantityInput" value="${this.quantity}" min="1" max="10" readonly />
              <button class="qty-btn" id="increaseQty">+</button>
            </div>
          </div>
        </div>
        
        <h4 style="margin-top: 20px;">Payment Details</h4>
        
        <div class="form-group">
          <label>Transaction ID *</label>
          <input type="text" class="form-input" id="transactionId" placeholder="Enter transaction/UTR number" value="${this.transactionId}" />
        </div>
        
        <div class="form-row">
          <div class="form-group half">
            <label>Transaction Date *</label>
            <input type="date" class="form-input" id="transactionDate" value="${this.transactionDate}" />
          </div>
          <div class="form-group half">
            <label>Amount Paid *</label>
            <input type="number" class="form-input" id="amountPaid" value="${totalAmount}" readonly />
          </div>
        </div>
        
        <div class="form-group">
          <label>Payment Mode *</label>
          <select class="form-select" id="paymentMode">
            <option value="">Select Payment Mode</option>
            ${PAYMENT_MODES.map(mode => `<option value="${mode}" ${this.paymentMode === mode ? 'selected' : ''}>${mode}</option>`).join('')}
          </select>
        </div>
        
        <div class="form-group">
          <label>Payment Screenshot *</label>
          <div class="screenshot-upload" id="screenshotUpload">
            ${this.screenshotPreview ? `
              <div class="screenshot-preview">
                <img src="${this.screenshotPreview}" alt="Screenshot" />
                <button class="remove-screenshot" id="removeScreenshot">✕</button>
              </div>
            ` : `
              <div class="upload-placeholder">
                <span>📷</span>
                <p>Tap to upload payment screenshot</p>
                <small>Max 500 KB, jpg/png/pdf</small>
              </div>
            `}
          </div>
        </div>
        
        <div class="total-row">
          <span class="total-label">Total Amount</span>
          <span class="total-amount">₹${totalAmount.toLocaleString()}</span>
        </div>
        
        <div class="approval-workflow">
          <h5>⚠️ Approval Workflow:</h5>
          <ol>
            <li>Admin/Super Admin will verify your payment details</li>
            <li>Finance Admin will approve the transaction</li>
            <li>Upon approval, coupon will be assigned to your account</li>
          </ol>
        </div>
        
        <button class="btn btn-primary submit-btn" id="submitPurchaseBtn" ${this.submitting ? 'disabled' : ''}>
          ${this.submitting ? 'Submitting...' : 'Submit Purchase Request'}
        </button>
      </div>
    `;
  }

  private renderHistory(): string {
    const table = new MobileTable({
      columns: [
        { key: 'package_type', label: 'Package', render: (v) => `<strong>${v}</strong>` },
        { key: 'quantity', label: 'Qty' },
        { key: 'amount_paid', label: 'Amount', render: (v) => `₹${v.toLocaleString()}` },
        { key: 'status', label: 'Status', render: (v) => this.getStatusBadge(v) },
        { key: 'created_at', label: 'Date', render: (v) => this.formatDate(v) }
      ],
      data: this.purchaseRequests.slice(0, 5),
      emptyMessage: 'No purchase history'
    });

    return `
      <div class="history-section">
        <div class="section-header">
          <span>📋</span> Recent Purchase Requests
        </div>
        ${table.render()}
      </div>
    `;
  }

  private getStatusBadge(status: string): string {
    const s = status.toLowerCase();
    if (s === 'approved' || s === 'completed') return '<span class="badge badge-success">Approved</span>';
    if (s === 'pending') return '<span class="badge badge-warning">Pending</span>';
    if (s === 'rejected') return '<span class="badge badge-danger">Rejected</span>';
    return `<span class="badge badge-secondary">${status}</span>`;
  }

  private attachListeners(): void {
    document.querySelectorAll('.package-card').forEach(card => {
      card.addEventListener('click', () => {
        const type = card.getAttribute('data-type');
        if (type) {
          this.selectedPackage = type;
          this.quantity = 1;
          this.updateContent();
        }
      });
    });

    document.getElementById('decreaseQty')?.addEventListener('click', () => {
      if (this.quantity > 1) {
        this.quantity--;
        this.updateTotalOnly();
      }
    });

    document.getElementById('increaseQty')?.addEventListener('click', () => {
      if (this.quantity < 10) {
        this.quantity++;
        this.updateTotalOnly();
      }
    });

    document.getElementById('transactionId')?.addEventListener('input', (e) => {
      this.transactionId = (e.target as HTMLInputElement).value;
    });

    document.getElementById('transactionDate')?.addEventListener('change', (e) => {
      this.transactionDate = (e.target as HTMLInputElement).value;
    });

    document.getElementById('paymentMode')?.addEventListener('change', (e) => {
      this.paymentMode = (e.target as HTMLSelectElement).value;
    });

    document.getElementById('screenshotUpload')?.addEventListener('click', () => {
      if (!this.screenshotPreview) {
        this.captureScreenshot();
      }
    });

    document.getElementById('removeScreenshot')?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.screenshotFile = null;
      this.screenshotPreview = '';
      this.updateContent();
    });

    document.getElementById('submitPurchaseBtn')?.addEventListener('click', () => {
      this.submitPurchaseRequest();
    });
  }

  private updateTotalOnly(): void {
    const pkg = PIN_PACKAGES.find(p => p.type === this.selectedPackage);
    if (!pkg) return;
    const totalAmount = pkg.price * this.quantity;
    
    const qtyInput = document.getElementById('quantityInput') as HTMLInputElement;
    const amountInput = document.getElementById('amountPaid') as HTMLInputElement;
    const totalSpan = document.querySelector('.total-amount');
    
    if (qtyInput) qtyInput.value = String(this.quantity);
    if (amountInput) amountInput.value = String(totalAmount);
    if (totalSpan) totalSpan.textContent = `₹${totalAmount.toLocaleString()}`;
  }

  private async captureScreenshot(): Promise<void> {
    try {
      const image = await Camera.getPhoto({
        quality: 80,
        allowEditing: false,
        resultType: CameraResultType.DataUrl,
        source: CameraSource.Prompt
      });

      if (image.dataUrl) {
        this.screenshotPreview = image.dataUrl;
        const blob = await fetch(image.dataUrl).then(r => r.blob());
        this.screenshotFile = new File([blob], `payment_screenshot.${image.format || 'jpg'}`, { type: `image/${image.format || 'jpeg'}` });
        this.updateContent();
      }
    } catch (error) {
      console.error('[MNRCouponBuy] Camera error:', error);
    }
  }

  private async submitPurchaseRequest(): Promise<void> {
    if (this.submitting) return;

    if (!this.selectedPackage) {
      alert('Please select a package');
      return;
    }
    if (!this.transactionId.trim()) {
      alert('Please enter Transaction ID');
      return;
    }
    if (!this.transactionDate) {
      alert('Please enter Transaction Date');
      return;
    }
    if (!this.paymentMode) {
      alert('Please select Payment Mode');
      return;
    }
    if (!this.screenshotFile) {
      alert('Please upload Payment Screenshot');
      return;
    }

    const pkg = PIN_PACKAGES.find(p => p.type === this.selectedPackage);
    if (!pkg) return;

    this.submitting = true;
    this.updateContent();

    try {
      const formData = new FormData();
      formData.append('package_type', pkg.type);
      formData.append('quantity', String(this.quantity));
      formData.append('transaction_id', this.transactionId);
      formData.append('transaction_date', this.transactionDate);
      formData.append('amount_paid', String(pkg.price * this.quantity));
      formData.append('payment_mode', this.paymentMode);
      formData.append('screenshot', this.screenshotFile);

      const response = await apiService.postFormData('/users/pins/purchase-request', formData);

      if (response.success) {
        alert('Purchase request submitted successfully! Awaiting admin approval.');
        this.resetForm();
        await this.loadPurchaseHistory();
      } else {
        alert(response.error || 'Failed to submit purchase request');
      }
    } catch (error: any) {
      console.error('[MNRCouponBuy] Submit error:', error);
      alert(error.message || 'Failed to submit purchase request');
    } finally {
      this.submitting = false;
      this.updateContent();
    }
  }

  private resetForm(): void {
    this.selectedPackage = null;
    this.quantity = 1;
    this.transactionId = '';
    this.transactionDate = new Date().toISOString().split('T')[0];
    this.paymentMode = '';
    this.screenshotFile = null;
    this.screenshotPreview = '';
  }

  private formatDate(dateStr: string): string {
    try {
      return new Date(dateStr).toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
      });
    } catch {
      return dateStr || '-';
    }
  }
}
