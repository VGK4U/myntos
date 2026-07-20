/**
 * Partner Leads Page
 * DC Protocol: DC_MOBILE_PARTNER_LEADS_001
 * Complete leads management for Partners with full form matching web version
 */

import { apiService } from '../../services/api.service';
import { authService } from '../../services/auth.service';
import { routerService } from '../../services/router.service';
import { partnerSideDrawer } from '../../components/PartnerSideDrawer';

interface Lead {
  id: number;
  name: string;
  phone: string;
  phone_primary_whatsapp?: boolean;
  alternate_phone?: string;
  email?: string;
  status: string;
  priority: string;
  category_id?: number;
  category_name?: string;
  source?: string;
  description?: string;
  requirements?: string;
  looking_for?: string;
  budget_min?: number | null;
  budget_max?: number | null;
  address?: string;
  area?: string;
  city?: string;
  state?: string;
  pincode?: string;
  created_at: string;
  updated_at?: string;
  submit_date?: string | null;
  complete_date?: string | null;
  next_followup_date?: string;
}

const LEAD_STATUSES = ['new', 'contacted', 'qualified', 'converted', 'lost'];
const LEAD_PRIORITIES = ['low', 'medium', 'high'];

export class PartnerLeadsPage {
  private container: HTMLElement;
  private user: any = null;
  private leads: Lead[] = [];
  private loading: boolean = true;
  private selectedStatus: string = 'all';
  private dateFilter: string = '';
  private roleFilter: string = '';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    const authState = authService.getAuthState();
    this.user = authState.user;
    partnerSideDrawer.setUser(this.user);
    this.render();
    await this.loadLeads();
  }

  private async loadLeads(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const params = new URLSearchParams();
      params.append('role', 'partner');
      if (this.dateFilter) params.append('quick_filter', this.dateFilter);
      if (this.roleFilter) params.append('role_filter', this.roleFilter);
      
      const response = await apiService.get<any>(`/crm/unified-my-leads?${params.toString()}`);
      if (response.success && response.data) {
        this.leads = response.data.leads || response.data || [];
      }
    } catch (error) {
      console.error('[PartnerLeads] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private async lookupPincode(pincodeInput: HTMLInputElement): Promise<void> {
    const pincode = pincodeInput.value.trim();
    if (!pincode || pincode.length !== 6) return;

    try {
      const response = await fetch(`https://api.postalpincode.in/pincode/${pincode}`);
      const data = await response.json();

      if (data[0]?.Status === 'Success' && data[0]?.PostOffice?.length > 0) {
        const po = data[0].PostOffice[0];
        const areaInput = document.getElementById('leadArea') as HTMLInputElement;
        const cityInput = document.getElementById('leadCity') as HTMLInputElement;
        const stateInput = document.getElementById('leadState') as HTMLInputElement;

        if (areaInput) areaInput.value = po.Name || '';
        if (cityInput) cityInput.value = po.District || '';
        if (stateInput) stateInput.value = po.State || '';
      }
    } catch (error) {
      console.error('[PartnerLeads] Pincode lookup failed:', error);
    }
  }

  private render(): void {
    const username = this.user?.name || this.user?.partner_name || 'Partner';
    const initials = username.split(' ').map((n: string) => n[0]).join('').toUpperCase().slice(0, 2);

    this.container.innerHTML = `
      <style>
        .partner-leads-page { background: linear-gradient(135deg, #0a1929 0%, #0d2137 100%); min-height: 100vh; }
        .partner-header {
          background: linear-gradient(135deg, #1e88e5 0%, #1565c0 100%);
          padding: 16px;
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .partner-hamburger {
          background: rgba(255, 255, 255, 0.15);
          border: none;
          border-radius: 8px;
          padding: 10px;
          color: white;
          cursor: pointer;
        }
        .partner-header-info { flex: 1; display: flex; align-items: center; gap: 12px; }
        .partner-header-avatar {
          width: 44px; height: 44px; border-radius: 50%;
          background: rgba(255, 255, 255, 0.2);
          display: flex; align-items: center; justify-content: center;
          font-weight: 600; font-size: 16px; color: white;
          border: 2px solid rgba(255, 255, 255, 0.3);
        }
        .partner-header-text { display: flex; flex-direction: column; }
        .partner-header-name { font-size: 16px; font-weight: 600; color: white; }
        .partner-header-role { font-size: 12px; color: rgba(255, 255, 255, 0.8); }
        .add-lead-btn {
          background: rgba(255, 255, 255, 0.2);
          border: none; border-radius: 10px;
          padding: 10px 16px; color: white;
          font-weight: 600; cursor: pointer;
          display: flex; align-items: center; gap: 6px;
        }
        .leads-content { padding: 16px; }
        .status-tabs {
          display: flex; gap: 8px; overflow-x: auto;
          padding-bottom: 16px; margin-bottom: 16px;
          -webkit-overflow-scrolling: touch;
        }
        .status-tab {
          padding: 10px 16px; border-radius: 20px;
          background: rgba(255, 255, 255, 0.08);
          color: #a8c0d8; font-size: 13px; font-weight: 500;
          border: none; cursor: pointer; white-space: nowrap;
          transition: all 0.2s;
        }
        .status-tab.active {
          background: linear-gradient(135deg, #10b981 0%, #047857 100%);
          color: white;
        }
        .leads-list { display: flex; flex-direction: column; gap: 12px; }
        .lead-card {
          background: rgba(255, 255, 255, 0.06);
          border-radius: 16px; padding: 16px;
          border: 1px solid rgba(255, 255, 255, 0.08);
          cursor: pointer;
        }
        .lead-card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
        .lead-name { font-size: 16px; font-weight: 600; color: #e6f1ff; }
        .lead-contact-row { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
        .lead-phone-link { color: #1e88e5; font-size: 14px; text-decoration: none; }
        .lead-phone-link:hover { text-decoration: underline; }
        .whatsapp-link { color: #25d366; font-size: 16px; text-decoration: none; }
        .lead-status {
          padding: 4px 10px; border-radius: 12px;
          font-size: 11px; font-weight: 600; text-transform: uppercase;
        }
        .lead-status.new { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
        .lead-status.contacted { background: rgba(245, 158, 11, 0.2); color: #fbbf24; }
        .lead-status.qualified { background: rgba(16, 185, 129, 0.2); color: #34d399; }
        .lead-status.converted { background: rgba(139, 92, 246, 0.2); color: #a78bfa; }
        .lead-status.lost { background: rgba(239, 68, 68, 0.2); color: #f87171; }
        .lead-meta { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; font-size: 12px; color: #7a9cc6; margin-bottom: 12px; }
        .meta-item { background: rgba(255,255,255,0.05); padding: 3px 8px; border-radius: 6px; }
        .priority-badge { padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; }
        .priority-badge.high { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
        .priority-badge.medium { background: rgba(251, 191, 36, 0.2); color: #fbbf24; }
        .priority-badge.low { background: rgba(107, 114, 128, 0.2); color: #9ca3af; }
        .lead-actions { display: flex; gap: 8px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 12px; }
        .action-btn { flex: 1; display: flex; align-items: center; justify-content: center; padding: 10px 8px; border-radius: 8px; font-size: 16px; text-decoration: none; border: none; cursor: pointer; background: rgba(255,255,255,0.05); }
        .action-btn.call { color: #10b981; }
        .action-btn.whatsapp { color: #25d366; }
        .action-btn.view { color: #60a5fa; }
        .action-btn.edit { color: #fbbf24; }
        .filter-row { display: flex; gap: 8px; margin: 12px 0; }
        .filter-select { flex: 1; padding: 10px 12px; background: rgba(30, 58, 95, 0.6); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #e6f1ff; font-size: 13px; }
        .filter-select option { background: #1a2744; color: #e6f1ff; }
        .empty-state {
          text-align: center; padding: 60px 20px;
          color: #7a9cc6;
        }
        .empty-icon { font-size: 48px; margin-bottom: 16px; opacity: 0.5; }
        .loading-state { text-align: center; padding: 60px 20px; color: #7a9cc6; }
      </style>

      <div class="partner-leads-page">
        <div class="partner-header">
          <button class="partner-hamburger" id="menuBtn">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 12h18M3 6h18M3 18h18"/>
            </svg>
          </button>
          <div class="partner-header-info">
            <div class="partner-header-avatar">${initials}</div>
            <div class="partner-header-text">
              <div class="partner-header-name">My Leads</div>
              <div class="partner-header-role">${username}</div>
            </div>
          </div>
          <button class="add-lead-btn" id="addLeadBtn">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 5v14M5 12h14"/>
            </svg>
            Add
          </button>
        </div>

        <div class="leads-content">
          <div class="status-tabs">
            <button class="status-tab active" data-status="all">All</button>
            ${LEAD_STATUSES.map(s => `<button class="status-tab" data-status="${s}">${s.charAt(0).toUpperCase() + s.slice(1)}</button>`).join('')}
          </div>
          <div class="filter-row">
            <select id="dateFilter" class="filter-select">
              <option value="">All Leads</option>
              <option value="today" ${this.dateFilter === 'today' ? 'selected' : ''}>Today's Leads</option>
              <option value="overdue" ${this.dateFilter === 'overdue' ? 'selected' : ''}>Overdue</option>
              <option value="followup_today" ${this.dateFilter === 'followup_today' ? 'selected' : ''}>Follow-up Today</option>
              <option value="this_week" ${this.dateFilter === 'this_week' ? 'selected' : ''}>This Week</option>
              <option value="future" ${this.dateFilter === 'future' ? 'selected' : ''}>Future Leads</option>
            </select>
            <select id="roleFilter" class="filter-select">
              <option value="">All Roles</option>
              <option value="primary_holder" ${this.roleFilter === 'primary_holder' ? 'selected' : ''}>As Primary Holder</option>
              <option value="handler" ${this.roleFilter === 'handler' ? 'selected' : ''}>As Handler</option>
            </select>
          </div>
          <div class="leads-list" id="leadsList"></div>
        </div>
      </div>
    `;

    this.attachEventListeners();
    this.updateContent();
  }

  private attachEventListeners(): void {
    document.getElementById('menuBtn')?.addEventListener('click', () => partnerSideDrawer.toggle());
    document.getElementById('addLeadBtn')?.addEventListener('click', () => this.showAddLeadModal());

    document.querySelectorAll('.status-tab').forEach(tab => {
      tab.addEventListener('click', (e) => {
        document.querySelectorAll('.status-tab').forEach(t => t.classList.remove('active'));
        (e.target as HTMLElement).classList.add('active');
        this.selectedStatus = (e.target as HTMLElement).dataset.status || 'all';
        this.updateContent();
      });
    });

    const dateSelect = document.getElementById('dateFilter') as HTMLSelectElement;
    if (dateSelect) {
      dateSelect.addEventListener('change', () => {
        this.dateFilter = dateSelect.value;
        this.loadLeads();
      });
    }

    const roleSelect = document.getElementById('roleFilter') as HTMLSelectElement;
    if (roleSelect) {
      roleSelect.addEventListener('change', () => {
        this.roleFilter = roleSelect.value;
        this.loadLeads();
      });
    }
  }

  private updateContent(): void {
    const listEl = document.getElementById('leadsList');
    if (!listEl) return;

    if (this.loading) {
      listEl.innerHTML = '<div class="loading-state">Loading leads...</div>';
      return;
    }

    const filtered = this.selectedStatus === 'all' 
      ? this.leads 
      : this.leads.filter(l => l.status === this.selectedStatus);

    if (filtered.length === 0) {
      listEl.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">📋</div>
          <div>No leads found</div>
          <button class="add-lead-btn" id="addLeadEmpty" style="margin-top: 16px;">+ Add Lead</button>
        </div>
      `;
      document.getElementById('addLeadEmpty')?.addEventListener('click', () => this.showAddLeadModal());
      return;
    }

    listEl.innerHTML = filtered.map(lead => `
      <div class="lead-card" data-id="${lead.id}">
        <div class="lead-card-header">
          <div>
            <div class="lead-name">${lead.name}</div>
            <div class="lead-contact-row">
              <a href="tel:${lead.phone || ''}" class="lead-phone-link" onclick="event.stopPropagation()">${lead.phone || 'No phone'}</a>
              ${lead.phone ? `<a href="https://wa.me/91${(lead.phone || '').replace(/\D/g, '')}" class="whatsapp-link" target="_blank" onclick="event.stopPropagation()">💬</a>` : ''}
            </div>
          </div>
          <span class="lead-status ${lead.status}">${lead.status}</span>
        </div>
        <div class="lead-meta">
          <span class="meta-item">${lead.category_name || 'General'}</span>
          <span class="priority-badge ${lead.priority?.toLowerCase() || 'medium'}">${lead.priority || 'Medium'}</span>
          <span class="meta-item">${new Date(lead.created_at).toLocaleDateString()}</span>
          ${lead.submit_date ? `<span class="meta-item" style="font-size:10px;color:#6b7280">📤 ${new Date(lead.submit_date).toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'})}</span>` : ''}
          ${lead.complete_date ? `<span class="meta-item" style="font-size:10px;color:#059669">✅ ${new Date(lead.complete_date).toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'})}</span>` : ''}
        </div>
        <div class="lead-actions">
          <a href="tel:${lead.phone || ''}" class="action-btn call" onclick="event.stopPropagation()">📞</a>
          <a href="https://wa.me/91${(lead.phone || '').replace(/\D/g, '')}" class="action-btn whatsapp" target="_blank" onclick="event.stopPropagation()">💬</a>
          <button class="action-btn view" data-action="view" data-id="${lead.id}">👁</button>
          <button class="action-btn edit" data-action="edit" data-id="${lead.id}">✏️</button>
        </div>
      </div>
    `).join('');
  }

  private showAddLeadModal(): void {
    const modal = document.createElement('div');
    modal.id = 'addLeadModal';
    modal.innerHTML = `
      <style>
        #addLeadModal {
          position: fixed; top: 0; left: 0; right: 0; bottom: 0;
          background: rgba(0, 0, 0, 0.7); backdrop-filter: blur(4px);
          display: flex; align-items: center; justify-content: center;
          z-index: 9999; padding: 16px;
        }
        #addLeadModal .modal-content {
          max-height: 90vh; width: 100%; max-width: 420px;
          background: linear-gradient(180deg, #1e3a5f 0%, #0d1b2a 100%);
          border-radius: 20px; padding: 0; display: flex; flex-direction: column;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        }
        #addLeadModal .modal-header {
          background: linear-gradient(135deg, #1e88e5 0%, #1565c0 100%);
          padding: 20px 24px; border-radius: 20px 20px 0 0;
          display: flex; justify-content: space-between; align-items: center;
        }
        #addLeadModal .modal-header h3 { margin: 0; color: white; font-size: 20px; font-weight: 700; }
        #addLeadModal .modal-close {
          background: rgba(255, 255, 255, 0.2); border: none; color: white;
          width: 36px; height: 36px; border-radius: 10px; font-size: 22px; cursor: pointer;
        }
        #addLeadModal .modal-body { padding: 24px; overflow-y: auto; flex: 1; max-height: calc(90vh - 180px); }
        #addLeadModal .form-section { margin-bottom: 20px; }
        #addLeadModal .section-title {
          font-size: 12px; font-weight: 600; color: #1e88e5;
          text-transform: uppercase; letter-spacing: 1px;
          margin-bottom: 12px; padding-bottom: 8px;
          border-bottom: 1px solid rgba(30, 136, 229, 0.2);
        }
        #addLeadModal .form-group { margin-bottom: 16px; }
        #addLeadModal .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        #addLeadModal label {
          display: block; color: #a8c0d8; font-size: 13px;
          font-weight: 500; margin-bottom: 8px;
        }
        #addLeadModal .required { color: #f87171; }
        #addLeadModal input, #addLeadModal select, #addLeadModal textarea {
          width: 100%; padding: 14px 16px; border-radius: 12px;
          border: 2px solid rgba(255, 255, 255, 0.08);
          background: rgba(13, 27, 42, 0.6); color: #e6f1ff;
          font-size: 15px; box-sizing: border-box;
        }
        #addLeadModal input:focus, #addLeadModal select:focus, #addLeadModal textarea:focus {
          border-color: #1e88e5; outline: none;
        }
        #addLeadModal .checkbox-row { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
        #addLeadModal .checkbox-row input[type="checkbox"] { width: 18px; height: 18px; accent-color: #1e88e5; }
        #addLeadModal .checkbox-row label { margin-bottom: 0; font-size: 13px; }
        #addLeadModal .modal-footer {
          padding: 20px 24px; border-top: 1px solid rgba(255, 255, 255, 0.08);
          display: flex; gap: 12px; background: rgba(13, 27, 42, 0.5);
          border-radius: 0 0 20px 20px;
        }
        #addLeadModal .btn-cancel {
          flex: 1; padding: 16px 20px; background: rgba(255, 255, 255, 0.08);
          border: 2px solid rgba(255, 255, 255, 0.15); color: #a8c0d8;
          border-radius: 12px; font-size: 15px; font-weight: 600; cursor: pointer;
        }
        #addLeadModal .btn-submit {
          flex: 1.5; padding: 16px 20px;
          background: linear-gradient(135deg, #1e88e5 0%, #1565c0 100%);
          border: none; color: white; border-radius: 12px;
          font-size: 15px; font-weight: 700; cursor: pointer;
          box-shadow: 0 4px 15px rgba(30, 136, 229, 0.35);
        }
      </style>
      <div class="modal-content">
        <div class="modal-header">
          <h3>Add New Lead</h3>
          <button class="modal-close">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-section">
            <div class="section-title">Basic Information</div>
            <div class="form-group">
              <label>Name <span class="required">*</span></label>
              <input type="text" id="leadName" placeholder="Full name" required>
            </div>
            <div class="form-group">
              <label>Email</label>
              <input type="email" id="leadEmail" placeholder="email@example.com">
            </div>
          </div>

          <div class="form-section">
            <div class="section-title">Contact Details</div>
            <div class="form-group">
              <label>Mobile Number <span class="required">*</span></label>
              <input type="tel" id="leadMobile" placeholder="10-digit mobile number" required maxlength="10" inputmode="numeric">
              <div class="checkbox-row">
                <input type="checkbox" id="leadPhoneWhatsapp" checked>
                <label for="leadPhoneWhatsapp">WhatsApp Available</label>
              </div>
            </div>
            <div class="form-group">
              <label>Alternate Mobile</label>
              <input type="tel" id="leadMobileSecondary" placeholder="Alternate number" maxlength="10" inputmode="numeric">
              <div class="checkbox-row">
                <input type="checkbox" id="leadPhoneSecondaryWhatsapp">
                <label for="leadPhoneSecondaryWhatsapp">WhatsApp Available</label>
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="section-title">Lead Classification</div>
            <div class="form-row">
              <div class="form-group">
                <label>Category</label>
                <select id="leadCategory">
                  <option value="">Select category...</option>
                  <option value="1">EV</option>
                  <option value="2">Real Estate</option>
                  <option value="3">Insurance</option>
                  <option value="4">Franchise</option>
                  <option value="5">Solar</option>
                  <option value="6">General</option>
                </select>
              </div>
              <div class="form-group">
                <label>Priority</label>
                <select id="leadPriority">
                  <option value="medium">Normal</option>
                  <option value="high">High</option>
                  <option value="low">Low</option>
                </select>
              </div>
            </div>
            <div class="form-group">
              <label>Lead Source</label>
              <select id="leadSource">
                <option value="">Select source...</option>
                <option value="referral">Referral</option>
                <option value="website">Website</option>
                <option value="social_media">Social Media</option>
                <option value="whatsapp">WhatsApp</option>
                <option value="direct">Direct</option>
                <option value="event">Event</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>

          <div class="form-section">
            <div class="section-title">Requirements & Budget</div>
            <div class="form-group">
              <label>Looking For</label>
              <input type="text" id="leadLookingFor" placeholder="What is the lead looking for?">
            </div>
            <div class="form-group">
              <label>Requirements</label>
              <textarea id="leadRequirements" placeholder="Detailed requirements..." rows="2"></textarea>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Budget Min</label>
                <input type="number" id="leadBudgetMin" placeholder="Min budget" inputmode="numeric">
              </div>
              <div class="form-group">
                <label>Budget Max</label>
                <input type="number" id="leadBudgetMax" placeholder="Max budget" inputmode="numeric">
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="section-title">Location Details</div>
            <div class="form-group">
              <label>Address</label>
              <input type="text" id="leadAddress" placeholder="Street address">
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Area</label>
                <input type="text" id="leadArea" placeholder="Area/Locality">
              </div>
              <div class="form-group">
                <label>City</label>
                <input type="text" id="leadCity" placeholder="City">
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>State</label>
                <input type="text" id="leadState" placeholder="State">
              </div>
              <div class="form-group">
                <label>Pincode</label>
                <input type="text" id="leadPincode" placeholder="PIN code" maxlength="6" inputmode="numeric">
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="section-title">Follow-up & Notes</div>
            <div class="form-row">
              <div class="form-group">
                <label>Expected Close Date</label>
                <input type="date" id="leadExpectedCloseDate">
              </div>
              <div class="form-group">
                <label>Next Follow-up</label>
                <input type="date" id="leadNextFollowupDate">
              </div>
            </div>
            <div class="form-group">
              <label>Tags</label>
              <input type="text" id="leadTags" placeholder="Comma separated tags">
            </div>
            <div class="form-group">
              <label>Notes</label>
              <textarea id="leadNotes" placeholder="Additional notes..." rows="3"></textarea>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" id="btnCancelLead">Cancel</button>
          <button class="btn-submit" id="btnSaveLead">Create Lead</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    modal.querySelector('.modal-close')?.addEventListener('click', () => modal.remove());
    modal.querySelector('#btnCancelLead')?.addEventListener('click', () => modal.remove());
    modal.querySelector('#btnSaveLead')?.addEventListener('click', () => this.saveLead(modal));
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.remove();
    });

    // Pincode auto-lookup
    const pincodeInput = document.getElementById('leadPincode') as HTMLInputElement;
    if (pincodeInput) {
      pincodeInput.addEventListener('input', () => {
        if (pincodeInput.value.length === 6) {
          this.lookupPincode(pincodeInput);
        }
      });
    }
  }

  private async saveLead(modal: HTMLElement): Promise<void> {
    const name = (document.getElementById('leadName') as HTMLInputElement)?.value?.trim();
    const phone = (document.getElementById('leadMobile') as HTMLInputElement)?.value?.trim();
    const email = (document.getElementById('leadEmail') as HTMLInputElement)?.value?.trim();
    const categoryId = (document.getElementById('leadCategory') as HTMLSelectElement)?.value;
    const priority = (document.getElementById('leadPriority') as HTMLSelectElement)?.value;
    const description = (document.getElementById('leadNotes') as HTMLTextAreaElement)?.value?.trim();
    const source = (document.getElementById('leadSource') as HTMLSelectElement)?.value;
    const alternatePhone = (document.getElementById('leadMobileSecondary') as HTMLInputElement)?.value?.trim();
    const address = (document.getElementById('leadAddress') as HTMLInputElement)?.value?.trim();
    const phonePrimaryWhatsapp = (document.getElementById('leadPhoneWhatsapp') as HTMLInputElement)?.checked;
    const phoneSecondaryWhatsapp = (document.getElementById('leadPhoneSecondaryWhatsapp') as HTMLInputElement)?.checked;
    const requirements = (document.getElementById('leadRequirements') as HTMLTextAreaElement)?.value?.trim();
    const lookingFor = (document.getElementById('leadLookingFor') as HTMLInputElement)?.value?.trim();
    const budgetMin = (document.getElementById('leadBudgetMin') as HTMLInputElement)?.value;
    const budgetMax = (document.getElementById('leadBudgetMax') as HTMLInputElement)?.value;
    const area = (document.getElementById('leadArea') as HTMLInputElement)?.value?.trim();
    const city = (document.getElementById('leadCity') as HTMLInputElement)?.value?.trim();
    const state = (document.getElementById('leadState') as HTMLInputElement)?.value?.trim();
    const pincode = (document.getElementById('leadPincode') as HTMLInputElement)?.value?.trim();
    const expectedCloseDate = (document.getElementById('leadExpectedCloseDate') as HTMLInputElement)?.value;
    const nextFollowupDate = (document.getElementById('leadNextFollowupDate') as HTMLInputElement)?.value;
    const tags = (document.getElementById('leadTags') as HTMLInputElement)?.value?.trim();

    if (!name || !phone) {
      alert('Please enter name and mobile number');
      return;
    }

    if (phone.length !== 10 || !/^\d{10}$/.test(phone)) {
      alert('Please enter a valid 10-digit mobile number');
      return;
    }

    const submitBtn = document.getElementById('btnSaveLead') as HTMLButtonElement;
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Creating...';
    }

    try {
      const payload: any = {
        name,
        phone,
        email: email || null,
        category_id: categoryId ? parseInt(categoryId) : null,
        priority: priority || 'medium',
        status: 'new',
        description: description || null,
        source: source || 'partner_app',
        phone_primary_whatsapp: phonePrimaryWhatsapp || false,
        alternate_phone: alternatePhone || null,
        phone_secondary_whatsapp: phoneSecondaryWhatsapp || false,
        address: address || null,
        requirements: requirements || null,
        looking_for: lookingFor || null,
        budget_min: budgetMin ? parseFloat(budgetMin) : null,
        budget_max: budgetMax ? parseFloat(budgetMax) : null,
        area: area || null,
        city: city || null,
        state: state || null,
        pincode: pincode || null,
        expected_close_date: expectedCloseDate || null,
        next_followup_date: nextFollowupDate || null,
        tags: tags || null
      };

      const response = await apiService.post<any>('/crm/unified-my-leads?role=partner', payload);

      if (response.success) {
        modal.remove();
        alert('Lead added successfully!');
        await this.loadLeads();
      } else {
        alert(response.error || 'Failed to add lead');
      }
    } catch (error: any) {
      console.error('[PartnerLeads] Add lead failed:', error);
      alert(error.message || 'Failed to add lead. Please try again.');
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Lead';
      }
    }
  }
}
