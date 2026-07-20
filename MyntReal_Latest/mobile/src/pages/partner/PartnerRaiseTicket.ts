/**
 * Partner Raise Ticket Page
 * DC Protocol: DC_MOBILE_PARTNER_TICKET_002
 * EV Service Ticket form matching public/staff version
 */

import { apiService } from '../../services/api.service';
import { authService } from '../../services/auth.service';
import { PageHeader } from '../../components/PageHeader';
import { routerService } from '../../services/router.service';

export class PartnerRaiseTicket {
  private container: HTMLElement;
  private submitting = false;
  private user: any = null;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    const authState = authService.getAuthState();
    this.user = authState.user;
    this.render();
  }

  private render(): void {
    const partnerName = this.user?.partner_name || this.user?.name || 'Partner';
    const partnerCode = this.user?.partner_code || '';

    this.container.innerHTML = `
      <style>
        .ticket-page {
          padding: 16px;
          padding-bottom: 100px;
          background: #0d1b2a;
          min-height: 100vh;
        }
        .section-card {
          background: rgba(22, 33, 62, 0.95);
          border-radius: 12px;
          margin-bottom: 16px;
          border: 1px solid rgba(255, 255, 255, 0.08);
          overflow: hidden;
        }
        .section-header {
          background: linear-gradient(135deg, rgba(30, 136, 229, 0.2) 0%, rgba(21, 101, 192, 0.15) 100%);
          padding: 14px 16px;
          display: flex;
          align-items: center;
          gap: 10px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }
        .section-header svg { color: #64b5f6; }
        .section-header h3 {
          font-size: 14px;
          font-weight: 600;
          color: white;
          margin: 0;
        }
        .section-body { padding: 16px; }
        .form-group { margin-bottom: 16px; }
        .form-group:last-child { margin-bottom: 0; }
        .form-group label {
          display: block;
          font-size: 12px;
          color: #8892b0;
          margin-bottom: 6px;
          font-weight: 500;
        }
        .form-group label .required { color: #ef4444; }
        .form-group input, .form-group select, .form-group textarea {
          width: 100%;
          padding: 12px 14px;
          border-radius: 8px;
          border: 1px solid rgba(255, 255, 255, 0.12);
          background: rgba(13, 27, 42, 0.9);
          color: #e6f1ff;
          font-size: 14px;
          transition: border-color 0.2s;
        }
        .form-group input:focus, .form-group select:focus, .form-group textarea:focus {
          outline: none;
          border-color: #1e88e5;
        }
        .form-group input::placeholder, .form-group textarea::placeholder {
          color: rgba(255, 255, 255, 0.35);
        }
        .form-group textarea { min-height: 100px; resize: vertical; }
        .form-group input[readonly] {
          background: rgba(255, 255, 255, 0.05);
          color: #64b5f6;
          cursor: not-allowed;
        }
        .form-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
        }
        .ticket-type-selector {
          display: flex;
          gap: 12px;
        }
        .ticket-type-option {
          flex: 1;
          padding: 14px 12px;
          border: 2px solid rgba(255, 255, 255, 0.15);
          border-radius: 10px;
          text-align: center;
          cursor: pointer;
          transition: all 0.2s;
        }
        .ticket-type-option.selected {
          border-color: #1e88e5;
          background: rgba(30, 136, 229, 0.15);
        }
        .ticket-type-option .type-icon { font-size: 24px; margin-bottom: 6px; }
        .ticket-type-option .type-label {
          font-weight: 600;
          color: white;
          font-size: 13px;
        }
        .submit-btn {
          width: 100%;
          padding: 16px;
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          border: none;
          border-radius: 10px;
          color: white;
          font-size: 16px;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
          margin-top: 8px;
          transition: all 0.2s;
        }
        .submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .submit-btn:active:not(:disabled) { transform: scale(0.98); }
        .partner-info-banner {
          background: linear-gradient(135deg, #1e88e5 0%, #1565c0 100%);
          border-radius: 10px;
          padding: 14px 16px;
          margin-bottom: 16px;
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .partner-avatar {
          width: 44px;
          height: 44px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.2);
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 600;
          font-size: 16px;
          color: white;
        }
        .partner-details h4 {
          color: white;
          font-size: 15px;
          font-weight: 600;
          margin: 0 0 4px;
        }
        .partner-details span {
          font-size: 12px;
          color: rgba(255, 255, 255, 0.8);
          background: rgba(255, 255, 255, 0.15);
          padding: 2px 8px;
          border-radius: 4px;
        }
        .toast {
          position: fixed;
          bottom: 100px;
          left: 50%;
          transform: translateX(-50%);
          background: #10b981;
          color: white;
          padding: 14px 24px;
          border-radius: 10px;
          font-size: 14px;
          font-weight: 500;
          z-index: 9999;
          animation: fadeInOut 3s ease;
          box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        .toast.error { background: #ef4444; }
        @keyframes fadeInOut {
          0%, 100% { opacity: 0; transform: translateX(-50%) translateY(10px); }
          10%, 90% { opacity: 1; transform: translateX(-50%) translateY(0); }
        }
      </style>
      ${PageHeader.render({ title: 'Create Service Ticket', showBack: true })}
      <div class="ticket-page">
        <!-- Partner Info Banner -->
        <div class="partner-info-banner">
          <div class="partner-avatar">${partnerName.charAt(0).toUpperCase()}</div>
          <div class="partner-details">
            <h4>${partnerName}</h4>
            <span>${partnerCode}</span>
          </div>
        </div>

        <!-- Customer Information -->
        <div class="section-card">
          <div class="section-header">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
            <h3>Customer Information</h3>
          </div>
          <div class="section-body">
            <div class="form-row">
              <div class="form-group">
                <label>Customer Name <span class="required">*</span></label>
                <input type="text" id="customerName" placeholder="Full name" required />
              </div>
              <div class="form-group">
                <label>Phone <span class="required">*</span></label>
                <input type="tel" id="customerPhone" placeholder="10-digit number" required />
              </div>
            </div>
            <div class="form-group">
              <label>Email</label>
              <input type="email" id="customerEmail" placeholder="email@example.com" />
            </div>
            <div class="form-group">
              <label>Address</label>
              <textarea id="customerAddress" rows="2" placeholder="Customer address (optional)"></textarea>
            </div>
          </div>
        </div>

        <!-- Request Type -->
        <div class="section-card">
          <div class="section-header">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
            </svg>
            <h3>Request Type</h3>
          </div>
          <div class="section-body">
            <div class="ticket-type-selector">
              <div class="ticket-type-option selected" data-type="technical">
                <div class="type-icon">🔧</div>
                <div class="type-label">Technical</div>
              </div>
              <div class="ticket-type-option" data-type="spares">
                <div class="type-icon">🔩</div>
                <div class="type-label">Spare Parts</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Issue Details -->
        <div class="section-card">
          <div class="section-header">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <h3>Issue Details</h3>
          </div>
          <div class="section-body">
            <div class="form-row">
              <div class="form-group">
                <label>Category <span class="required">*</span></label>
                <select id="issueCategory" required>
                  <option value="">Select Category</option>
                  <option value="EV Battery Issue">EV Battery Issue</option>
                  <option value="Motor/Controller Problem">Motor/Controller</option>
                  <option value="Charging Issue">Charging Issue</option>
                  <option value="Display/Electronics">Display/Electronics</option>
                  <option value="Brake/Suspension">Brake/Suspension</option>
                  <option value="Body/Frame Damage">Body/Frame Damage</option>
                  <option value="Warranty Claim">Warranty Claim</option>
                  <option value="General Service">General Service</option>
                  <option value="Other">Other</option>
                </select>
              </div>
              <div class="form-group">
                <label>Priority <span class="required">*</span></label>
                <select id="priority" required>
                  <option value="Medium">Medium</option>
                  <option value="Low">Low</option>
                  <option value="High">High</option>
                  <option value="Critical">Critical</option>
                </select>
              </div>
            </div>
            <div class="form-group">
              <label>Issue Description <span class="required">*</span></label>
              <textarea id="issueDescription" rows="4" placeholder="Describe the issue in detail..." required></textarea>
            </div>
          </div>
        </div>

        <!-- Product Information (Optional) -->
        <div class="section-card">
          <div class="section-header">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="1" y="3" width="15" height="13"/>
              <polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/>
              <circle cx="5.5" cy="18.5" r="2.5"/>
              <circle cx="18.5" cy="18.5" r="2.5"/>
            </svg>
            <h3>Product Information (Optional)</h3>
          </div>
          <div class="section-body">
            <div class="form-group">
              <label>Product Name</label>
              <input type="text" id="productName" placeholder="e.g., Electric Scooter Pro" />
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Serial Number</label>
                <input type="text" id="productSerial" placeholder="EV2024001234" />
              </div>
              <div class="form-group">
                <label>Model</label>
                <input type="text" id="productModel" placeholder="Model name" />
              </div>
            </div>
            <div class="form-group">
              <label>Warranty Status</label>
              <select id="warrantyStatus">
                <option value="">Select...</option>
                <option value="under_warranty">Under Warranty</option>
                <option value="out_of_warranty">Out of Warranty</option>
                <option value="amc">AMC</option>
              </select>
            </div>
          </div>
        </div>

        <button class="submit-btn" id="submitTicketBtn">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
          Submit Service Ticket
        </button>
      </div>
    `;

    PageHeader.attachListeners({ title: 'Create Service Ticket', showBack: true });
    this.attachListeners();
  }

  private attachListeners(): void {
    // Ticket type selection
    document.querySelectorAll('.ticket-type-option').forEach(opt => {
      opt.addEventListener('click', () => {
        document.querySelectorAll('.ticket-type-option').forEach(o => o.classList.remove('selected'));
        opt.classList.add('selected');
      });
    });

    // Submit handler
    document.getElementById('submitTicketBtn')?.addEventListener('click', () => this.submitTicket());
  }

  private async submitTicket(): Promise<void> {
    if (this.submitting) return;

    // Get form values
    const customerName = (document.getElementById('customerName') as HTMLInputElement)?.value.trim();
    const customerPhone = (document.getElementById('customerPhone') as HTMLInputElement)?.value.trim();
    const customerEmail = (document.getElementById('customerEmail') as HTMLInputElement)?.value.trim();
    const customerAddress = (document.getElementById('customerAddress') as HTMLTextAreaElement)?.value.trim();
    const issueCategory = (document.getElementById('issueCategory') as HTMLSelectElement)?.value;
    const priority = (document.getElementById('priority') as HTMLSelectElement)?.value;
    const issueDescription = (document.getElementById('issueDescription') as HTMLTextAreaElement)?.value.trim();
    const productName = (document.getElementById('productName') as HTMLInputElement)?.value.trim();
    const productSerial = (document.getElementById('productSerial') as HTMLInputElement)?.value.trim();
    const productModel = (document.getElementById('productModel') as HTMLInputElement)?.value.trim();
    const warrantyStatus = (document.getElementById('warrantyStatus') as HTMLSelectElement)?.value;
    
    const selectedType = document.querySelector('.ticket-type-option.selected') as HTMLElement;
    const ticketType = selectedType?.dataset.type || 'technical';

    // Validation
    if (!customerName || customerName.length < 2) {
      this.showToast('Please enter customer name (min 2 characters)', true);
      return;
    }
    if (!customerPhone || customerPhone.length < 10) {
      this.showToast('Please enter a valid phone number', true);
      return;
    }
    if (!issueCategory) {
      this.showToast('Please select an issue category', true);
      return;
    }
    if (!issueDescription || issueDescription.length < 10) {
      this.showToast('Please describe the issue (min 10 characters)', true);
      return;
    }

    this.submitting = true;
    const btn = document.getElementById('submitTicketBtn') as HTMLButtonElement;
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `
        <svg class="spinner" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" stroke-dasharray="60" stroke-dashoffset="20"/>
        </svg>
        Submitting...
      `;
    }

    try {
      // DC Protocol: Use correct partner endpoint for service tickets
      const response = await apiService.post<any>('/tickets/service/partner/create', {
        customer_name: customerName,
        customer_phone: customerPhone,
        customer_email: customerEmail || null,
        customer_address: customerAddress || null,
        issue_category: issueCategory,
        issue_description: issueDescription,
        ticket_type: ticketType,
        priority: priority,
        product_name: productName || null,
        product_serial: productSerial || null,
        product_model: productModel || null,
        warranty_status: warrantyStatus || null
      });

      if (response.success || response.data?.success) {
        const ticketId = response.data?.ticket_id || 'Created';
        this.showToast(`Ticket ${ticketId} created successfully!`);
        setTimeout(() => {
          routerService.navigate('partner-service');
        }, 1500);
      } else {
        this.showToast(response.error || response.data?.detail || 'Failed to create ticket', true);
      }
    } catch (error: any) {
      console.error('[PartnerRaiseTicket] Submit error:', error);
      this.showToast(error.message || 'Failed to create ticket', true);
    }

    this.submitting = false;
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="22" y1="2" x2="11" y2="13"/>
          <polygon points="22 2 15 22 11 13 2 9 22 2"/>
        </svg>
        Submit Service Ticket
      `;
    }
  }

  private showToast(message: string, isError = false): void {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast ${isError ? 'error' : ''}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.remove(), 3000);
  }
}
