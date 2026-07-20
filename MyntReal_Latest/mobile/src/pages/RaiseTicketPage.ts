/**
 * Raise Service Ticket Page
 * DC Protocol: DC_MOBILE_RAISE_TICKET_001
 * Create new EV service tickets
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import { routerService } from '../services/router.service';

interface Partner {
  id: number;
  partner_code: string;
  partner_name: string;
  category: string;
  city?: string;
}

export class RaiseTicketPage {
  private container: HTMLElement;
  private partners: Partner[] = [];
  private loading: boolean = false;
  private submitting: boolean = false;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadPartners();
  }

  private async loadPartners(): Promise<void> {
    try {
      const response = await apiService.get<any>('/tickets/service-centers');
      if (response.success && response.data) {
        this.partners = response.data;
        this.updatePartnerDropdown();
      }
    } catch (error) {
      console.error('[RaiseTicketPage] Failed to load partners:', error);
    }
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Raise Service Ticket', showBack: true })}
        
        <form id="ticketForm" class="form-container">
          <div class="form-section">
            <h4>Customer Details</h4>
            
            <div class="form-group">
              <label>Customer Name *</label>
              <input type="text" id="customerName" class="form-input" placeholder="Enter customer name" required>
            </div>

            <div class="form-group">
              <label>Mobile Number *</label>
              <input type="tel" id="customerMobile" class="form-input" placeholder="10-digit mobile" maxlength="10" required>
            </div>

            <div class="form-group">
              <label>Email</label>
              <input type="email" id="customerEmail" class="form-input" placeholder="customer@email.com">
            </div>
          </div>

          <div class="form-section">
            <h4>Vehicle Details</h4>
            
            <div class="form-group">
              <label>Vehicle Number *</label>
              <input type="text" id="vehicleNumber" class="form-input" placeholder="e.g., MH12AB1234" required>
            </div>

            <div class="form-group">
              <label>Vehicle Model</label>
              <input type="text" id="vehicleModel" class="form-input" placeholder="e.g., Ather 450X">
            </div>

            <div class="form-group">
              <label>Odometer Reading (km)</label>
              <input type="number" id="odometerReading" class="form-input" placeholder="Current km reading">
            </div>
          </div>

          <div class="form-section">
            <h4>Ticket Type</h4>
            
            <div class="form-group ticket-type-group">
              <div class="ticket-type-options">
                <label class="ticket-type-option selected" data-type="technical">
                  <input type="radio" name="ticketType" value="technical" checked>
                  <span class="type-icon">🔧</span>
                  <span class="type-label">Technical</span>
                </label>
                <label class="ticket-type-option" data-type="spares">
                  <input type="radio" name="ticketType" value="spares">
                  <span class="type-icon">🔩</span>
                  <span class="type-label">Spare Parts</span>
                </label>
              </div>
            </div>
          </div>

          <div class="form-section">
            <h4>Issue Details</h4>
            
            <div class="form-group">
              <label>Issue Category *</label>
              <select id="issueCategory" class="form-select" required>
                <option value="">Select category</option>
                <option value="Battery">Battery Issue</option>
                <option value="Motor">Motor Problem</option>
                <option value="Controller">Controller Issue</option>
                <option value="Charging">Charging Problem</option>
                <option value="Brakes">Brake Issue</option>
                <option value="Suspension">Suspension</option>
                <option value="Electrical">Electrical</option>
                <option value="Body">Body Damage</option>
                <option value="Service">Regular Service</option>
                <option value="Other">Other</option>
              </select>
            </div>

            <div class="form-group">
              <label>Priority *</label>
              <select id="priority" class="form-select" required>
                <option value="Low">Low</option>
                <option value="Medium" selected>Medium</option>
                <option value="High">High</option>
                <option value="Critical">Critical</option>
              </select>
            </div>

            <div class="form-group">
              <label>Issue Description *</label>
              <textarea id="issueDescription" class="form-textarea" rows="4" placeholder="Describe the issue in detail..." required></textarea>
            </div>
          </div>

          <div class="form-section">
            <h4>Assignment</h4>
            
            <div class="form-group">
              <label>Service Center</label>
              <select id="serviceCenter" class="form-select">
                <option value="">Select service center (optional)</option>
              </select>
            </div>
          </div>

          <div class="form-actions sticky-bottom">
            <button type="button" class="btn btn-secondary" id="cancelBtn">Cancel</button>
            <button type="submit" class="btn btn-primary" id="submitBtn">Create Ticket</button>
          </div>
        </form>
      </div>
    `;

    PageHeader.attachBackHandler();
    this.attachListeners();
  }

  private updatePartnerDropdown(): void {
    const select = document.getElementById('serviceCenter') as HTMLSelectElement;
    if (!select) return;

    const options = this.partners.map(p => 
      `<option value="${p.id}">${p.partner_name}${p.city ? ` - ${p.city}` : ''}</option>`
    );
    select.innerHTML = '<option value="">Select service center (optional)</option>' + options.join('');
  }

  private attachListeners(): void {
    document.getElementById('cancelBtn')?.addEventListener('click', () => {
      routerService.goBack();
    });

    document.getElementById('ticketForm')?.addEventListener('submit', (e) => {
      e.preventDefault();
      this.submitTicket();
    });

    const mobileInput = document.getElementById('customerMobile') as HTMLInputElement;
    mobileInput?.addEventListener('input', () => {
      mobileInput.value = mobileInput.value.replace(/\D/g, '').slice(0, 10);
    });

    const vehicleInput = document.getElementById('vehicleNumber') as HTMLInputElement;
    vehicleInput?.addEventListener('input', () => {
      vehicleInput.value = vehicleInput.value.toUpperCase();
    });

    this.container.querySelectorAll('.ticket-type-option').forEach(opt => {
      opt.addEventListener('click', () => {
        this.container.querySelectorAll('.ticket-type-option').forEach(o => o.classList.remove('selected'));
        opt.classList.add('selected');
        const radio = opt.querySelector('input[type="radio"]') as HTMLInputElement;
        if (radio) radio.checked = true;
      });
    });
  }

  private async submitTicket(): Promise<void> {
    if (this.submitting) return;

    const customerName = (document.getElementById('customerName') as HTMLInputElement).value.trim();
    const customerMobile = (document.getElementById('customerMobile') as HTMLInputElement).value.trim();
    const customerEmail = (document.getElementById('customerEmail') as HTMLInputElement).value.trim();
    const vehicleNumber = (document.getElementById('vehicleNumber') as HTMLInputElement).value.trim();
    const vehicleModel = (document.getElementById('vehicleModel') as HTMLInputElement).value.trim();
    const odometerReading = (document.getElementById('odometerReading') as HTMLInputElement).value;
    const issueCategory = (document.getElementById('issueCategory') as HTMLSelectElement).value;
    const priority = (document.getElementById('priority') as HTMLSelectElement).value;
    const issueDescription = (document.getElementById('issueDescription') as HTMLTextAreaElement).value.trim();
    const serviceCenter = (document.getElementById('serviceCenter') as HTMLSelectElement).value;

    if (!customerName || !customerMobile || !vehicleNumber || !issueCategory || !issueDescription) {
      alert('Please fill in all required fields');
      return;
    }

    if (customerMobile.length !== 10) {
      alert('Please enter a valid 10-digit mobile number');
      return;
    }

    this.submitting = true;
    const submitBtn = document.getElementById('submitBtn') as HTMLButtonElement;
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Creating...';
    }

    try {
      const ticketTypeRadio = document.querySelector('input[name="ticketType"]:checked') as HTMLInputElement;
      const ticketType = ticketTypeRadio?.value || 'technical';

      const payload = {
        ticket_type: ticketType,
        customer_name: customerName,
        customer_phone: customerMobile,
        customer_email: customerEmail || null,
        product_serial: vehicleNumber,
        vehicle_model: vehicleModel || null,
        odometer_reading: odometerReading ? parseInt(odometerReading) : null,
        issue_category: issueCategory,
        priority: priority,
        issue_description: issueDescription,
        partner_id: serviceCenter ? parseInt(serviceCenter) : null
      };

      const response = await apiService.post('/tickets/service/create', payload);

      if (response.success) {
        alert('Service ticket created successfully!');
        routerService.navigate('staff-service-queue');
      } else {
        alert(response.error || 'Failed to create ticket');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to create ticket');
    } finally {
      this.submitting = false;
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Ticket';
      }
    }
  }
}
