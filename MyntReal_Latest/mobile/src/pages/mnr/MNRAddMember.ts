/**
 * MNR Add Member Page
 * DC Protocol: DC_MOBILE_MNR_ADD_MEMBER_001
 * Add new member to the network - Enhanced UI with referrer lookup
 */

import { apiService } from '../../services/api.service';
import { authService } from '../../services/auth.service';
import { PageHeader } from '../../components/PageHeader';
import { routerService } from '../../services/router.service';

interface Package {
  id: number;
  name: string;
  price: number;
}

interface ReferrerInfo {
  name: string;
  mnr_id: string;
  active_status: boolean;
}

export class MNRAddMember {
  private container: HTMLElement;
  private packages: Package[] = [];
  private loading: boolean = true;
  private currentUser: any = null;
  private referrerInfo: ReferrerInfo | null = null;
  private referrerLoading: boolean = false;
  private referrerError: string = '';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    const authState = authService.getAuthState();
    this.currentUser = authState.user;
    this.render();
    await this.loadPackages();
    this.setDefaultReferrer();
  }

  private async loadPackages(): Promise<void> {
    try {
      const response = await apiService.get<any>('/users/packages');
      if (response.success && response.data) {
        this.packages = response.data.packages || response.data || [];
      }
    } catch (error) {
      console.error('[MNRAddMember] Failed to load packages:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private setDefaultReferrer(): void {
    const referrerInput = document.getElementById('referrerId') as HTMLInputElement;
    if (referrerInput && this.currentUser?.mnr_id) {
      referrerInput.value = this.currentUser.mnr_id;
      this.referrerInfo = {
        name: this.currentUser.name || 'You',
        mnr_id: this.currentUser.mnr_id,
        active_status: true
      };
      this.updateReferrerDisplay();
    }
  }

  private render(): void {
    this.container.innerHTML = `
      <style>
        .add-member-page {
          background: linear-gradient(135deg, #0a1929 0%, #0d2137 100%);
          min-height: 100vh;
        }
        .add-member-content {
          padding: 16px;
        }
        .form-card {
          background: #ffffff;
          border-radius: 16px;
          overflow: hidden;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        }
        .form-header {
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          padding: 20px;
          text-align: center;
        }
        .form-header h2 {
          margin: 0;
          color: white;
          font-size: 18px;
          font-weight: 600;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
        }
        .form-header p {
          margin: 8px 0 0;
          color: rgba(255, 255, 255, 0.9);
          font-size: 13px;
        }
        .form-body {
          padding: 20px;
        }
        .form-section {
          margin-bottom: 24px;
        }
        .form-section-title {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 14px;
          font-weight: 600;
          color: #1f2937;
          margin-bottom: 16px;
          padding-bottom: 8px;
          border-bottom: 2px solid #e5e7eb;
        }
        .form-section-title .icon {
          width: 24px;
          height: 24px;
          background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%);
          border-radius: 6px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-size: 12px;
        }
        .form-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
          margin-bottom: 16px;
        }
        .form-row.three-col {
          grid-template-columns: 1fr 1fr 1fr;
        }
        .form-group {
          margin-bottom: 16px;
        }
        .form-row .form-group {
          margin-bottom: 0;
        }
        .form-group label {
          display: block;
          font-size: 12px;
          font-weight: 600;
          color: #374151;
          margin-bottom: 6px;
        }
        .form-group label .required {
          color: #ef4444;
        }
        .form-group input,
        .form-group select,
        .form-group textarea {
          width: 100%;
          padding: 12px 14px;
          border: 2px solid #e5e7eb;
          border-radius: 10px;
          font-size: 14px;
          color: #1f2937;
          background: #f9fafb;
          transition: all 0.2s ease;
          box-sizing: border-box;
        }
        .form-group input:focus,
        .form-group select:focus,
        .form-group textarea:focus {
          outline: none;
          border-color: #7c3aed;
          background: #ffffff;
          box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1);
        }
        .form-group input::placeholder,
        .form-group textarea::placeholder {
          color: #9ca3af;
        }
        .form-hint {
          display: block;
          font-size: 11px;
          color: #6b7280;
          margin-top: 4px;
        }

        /* Referrer Section */
        .referrer-section {
          background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 20px;
        }
        .referrer-title {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 14px;
          font-weight: 600;
          color: #92400e;
          margin-bottom: 12px;
        }
        .referrer-input-row {
          display: flex;
          gap: 10px;
          margin-bottom: 8px;
        }
        .referrer-input-row input {
          flex: 1;
          padding: 12px 14px;
          border: 2px solid #d97706;
          border-radius: 10px;
          font-size: 14px;
          color: #1f2937;
          background: #ffffff;
        }
        .referrer-input-row input:focus {
          outline: none;
          border-color: #b45309;
          box-shadow: 0 0 0 3px rgba(217, 119, 6, 0.2);
        }
        .lookup-btn {
          padding: 12px 16px;
          background: linear-gradient(135deg, #d97706 0%, #b45309 100%);
          border: none;
          border-radius: 10px;
          color: white;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          white-space: nowrap;
        }
        .lookup-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        .referrer-info {
          display: flex;
          align-items: center;
          gap: 12px;
          background: #ffffff;
          border-radius: 10px;
          padding: 12px;
          margin-top: 10px;
        }
        .referrer-avatar {
          width: 44px;
          height: 44px;
          background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-weight: 700;
          font-size: 16px;
        }
        .referrer-details {
          flex: 1;
        }
        .referrer-name {
          font-size: 14px;
          font-weight: 600;
          color: #1f2937;
        }
        .referrer-id {
          font-size: 12px;
          color: #6b7280;
        }
        .referrer-status {
          padding: 4px 10px;
          border-radius: 20px;
          font-size: 11px;
          font-weight: 600;
        }
        .referrer-status.active {
          background: #d1fae5;
          color: #047857;
        }
        .referrer-status.pending {
          background: #fee2e2;
          color: #b91c1c;
        }
        .referrer-error {
          color: #b91c1c;
          font-size: 12px;
          margin-top: 8px;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .referrer-loading {
          color: #92400e;
          font-size: 12px;
          margin-top: 8px;
          display: flex;
          align-items: center;
          gap: 6px;
        }

        /* Position Selection */
        .position-cards {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 10px;
          margin-top: 8px;
        }
        .position-card {
          padding: 16px 12px;
          border: 2px solid #e5e7eb;
          border-radius: 12px;
          text-align: center;
          cursor: pointer;
          transition: all 0.2s ease;
          background: #f9fafb;
        }
        .position-card:hover {
          border-color: #7c3aed;
          background: #faf5ff;
        }
        .position-card.selected {
          border-color: #7c3aed;
          background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%);
          color: white;
        }
        .position-card .icon {
          font-size: 24px;
          margin-bottom: 6px;
        }
        .position-card .label {
          font-size: 13px;
          font-weight: 600;
        }

        /* Submit Button */
        .submit-section {
          margin-top: 24px;
        }
        .submit-btn {
          width: 100%;
          padding: 16px;
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          border: none;
          border-radius: 12px;
          color: white;
          font-size: 16px;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
          box-shadow: 0 4px 14px rgba(16, 185, 129, 0.4);
          transition: all 0.2s ease;
        }
        .submit-btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(16, 185, 129, 0.5);
        }
        .submit-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
          transform: none;
        }
        .submit-btn svg {
          width: 20px;
          height: 20px;
        }

        .loading-state {
          text-align: center;
          padding: 40px;
          color: #6b7280;
        }
      </style>

      <div class="page-container add-member-page">
        ${PageHeader.render({ title: '➕ Add Member', showBack: true })}
        
        <div class="add-member-content" id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: '➕ Add Member', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    const referrerId = this.currentUser?.mnr_id || '';
    const referrerName = this.currentUser?.name || 'You';

    content.innerHTML = `
      <div class="form-card">
        <div class="form-header">
          <h2>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="8.5" cy="7" r="4"></circle>
              <line x1="20" y1="8" x2="20" y2="14"></line>
              <line x1="23" y1="11" x2="17" y2="11"></line>
            </svg>
            Member Registration
          </h2>
          <p>Add a new member to your referral network</p>
        </div>

        <div class="form-body">
          <form id="addMemberForm">
            <!-- Referrer Section -->
            <div class="referrer-section">
              <div class="referrer-title">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                  <circle cx="9" cy="7" r="4"></circle>
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                  <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                </svg>
                Referrer Information
              </div>
              <div class="referrer-input-row">
                <input type="text" id="referrerId" value="${referrerId}" placeholder="Enter MNR ID" />
                <button type="button" class="lookup-btn" id="lookupBtn">
                  Verify
                </button>
              </div>
              <span class="form-hint">Your MNR ID is pre-filled. Enter different ID to refer under someone else.</span>
              
              <div id="referrerDisplay">
                ${this.currentUser ? `
                  <div class="referrer-info">
                    <div class="referrer-avatar">${this.getInitials(referrerName)}</div>
                    <div class="referrer-details">
                      <div class="referrer-name">${referrerName}</div>
                      <div class="referrer-id">MNR ID: ${referrerId}</div>
                    </div>
                    <span class="referrer-status active">Active</span>
                  </div>
                ` : ''}
              </div>
            </div>

            <!-- Personal Details Section -->
            <div class="form-section">
              <div class="form-section-title">
                <div class="icon">1</div>
                Personal Details
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label>First Name <span class="required">*</span></label>
                  <input type="text" id="firstName" required placeholder="First name" />
                </div>
                <div class="form-group">
                  <label>Last Name <span class="required">*</span></label>
                  <input type="text" id="lastName" required placeholder="Last name" />
                </div>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label>Salutation <span class="required">*</span></label>
                  <select id="salutation" required>
                    <option value="">Select</option>
                    <option value="Mr">Mr</option>
                    <option value="Mrs">Mrs</option>
                    <option value="Ms">Ms</option>
                    <option value="Dr">Dr</option>
                  </select>
                </div>
                <div class="form-group">
                  <label>Mobile <span class="required">*</span></label>
                  <input type="tel" id="mobile" required placeholder="10 digits" maxlength="10" oninput="document.getElementById('mnrMobileOtpSection').style.display='none';document.getElementById('mnrMobileVerifiedBadge').style.display='none';document.getElementById('mnrMobilePhoneToken').value='';" />
                </div>
              </div>

              <!-- [DC-PHONE-OTP-001] WhatsApp OTP verification for MNR member add (mobile) -->
              <div class="form-group">
                <button type="button" id="mnrMobileSendOtpBtn" onclick="mnrMobileSendOTP()" style="width:100%;padding:11px;background:linear-gradient(135deg,#7c3aed,#5b21b6);border:none;border-radius:10px;color:#fff;font-size:14px;font-weight:600;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 1.17h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.7A16 16 0 0 0 13.3 14.09l.95-.95a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 21.02 15.5z"/></svg>
                  Send OTP to WhatsApp
                </button>
                <div style="font-size:11px;color:#ef4444;margin-top:5px;text-align:center"><i>WhatsApp OTP verification is required before registering</i></div>
              </div>
              <div id="mnrMobileOtpSection" style="display:none;background:#f0fdf4;border:2px solid #86efac;border-radius:12px;padding:14px;margin-bottom:16px;">
                <div style="font-size:12.5px;color:#166534;margin-bottom:10px;display:flex;align-items:center;gap:6px;">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="#25D366"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M12 0C5.373 0 0 5.373 0 12c0 2.125.558 4.126 1.535 5.856L0 24l6.335-1.652A11.954 11.954 0 0 0 12 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 21.818a9.818 9.818 0 0 1-5.006-1.371l-.36-.214-3.727.972.997-3.639-.235-.373A9.818 9.818 0 1 1 12 21.818z"/></svg>
                  OTP sent! Enter the 6-digit code from WhatsApp:
                </div>
                <div style="display:flex;gap:8px;">
                  <input type="text" id="mnrMobileOtpInput" maxlength="6" placeholder="● ● ● ● ● ●" style="flex:1;padding:12px;border:2px solid #22c55e;border-radius:10px;font-size:20px;font-weight:700;letter-spacing:6px;text-align:center;background:#fff;color:#166534;" />
                  <button type="button" id="mnrMobileVerifyBtn" onclick="mnrMobileVerifyOTP()" style="padding:12px 16px;background:#22c55e;border:none;border-radius:10px;color:#fff;font-size:14px;font-weight:600;cursor:pointer;">Verify</button>
                </div>
                <div style="margin-top:8px;font-size:11.5px;color:#6b7280;text-align:center">Didn't receive? <a href="#" onclick="mnrMobileSendOTP();return false;" style="color:#7c3aed;font-weight:600;">Resend OTP</a></div>
              </div>
              <div id="mnrMobileVerifiedBadge" style="display:none;background:#f0fdf4;border:2px solid #22c55e;border-radius:10px;padding:10px 14px;margin-bottom:16px;color:#166534;font-size:13px;font-weight:600;display:none;align-items:center;gap:8px;">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
                WhatsApp number verified
              </div>
              <input type="hidden" id="mnrMobilePhoneToken" value="" />

              <div class="form-group">
                <label>Password <span class="required">*</span></label>
                <input type="password" id="password" required placeholder="Create password (min 6 chars)" />
              </div>
            </div>

            <!-- Address Section -->
            <div class="form-section">
              <div class="form-section-title">
                <div class="icon">2</div>
                Address Details
              </div>

              <div class="form-group">
                <label>Address</label>
                <textarea id="address" rows="2" placeholder="Street address"></textarea>
              </div>

              <div class="form-row three-col">
                <div class="form-group">
                  <label>City</label>
                  <input type="text" id="city" placeholder="City" />
                </div>
                <div class="form-group">
                  <label>State</label>
                  <input type="text" id="state" placeholder="State" />
                </div>
                <div class="form-group">
                  <label>Pincode</label>
                  <input type="text" id="pincode" maxlength="6" placeholder="6 digits" />
                </div>
              </div>
            </div>

            <!-- Position Section -->
            <div class="form-section">
              <div class="form-section-title">
                <div class="icon">3</div>
                Placement Position
              </div>
              <span class="form-hint" style="margin-top: -10px; margin-bottom: 12px; display: block;">Choose where to place this member in your tree</span>
              
              <div class="position-cards">
                <div class="position-card" data-position="left">
                  <div class="icon">⬅️</div>
                  <div class="label">Group A</div>
                </div>
                <div class="position-card" data-position="right">
                  <div class="icon">➡️</div>
                  <div class="label">Group B</div>
                </div>
                <div class="position-card selected" data-position="auto">
                  <div class="icon">⚡</div>
                  <div class="label">Auto</div>
                </div>
              </div>
              <input type="hidden" id="position" value="auto" />
            </div>

            <!-- Submit -->
            <div class="submit-section">
              <button type="submit" class="submit-btn" id="submitBtn">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                  <circle cx="8.5" cy="7" r="4"></circle>
                  <line x1="20" y1="8" x2="20" y2="14"></line>
                  <line x1="23" y1="11" x2="17" y2="11"></line>
                </svg>
                Add Member
              </button>
            </div>
          </form>
        </div>
      </div>
    `;

    this.attachFormListeners();
  }

  private updateReferrerDisplay(): void {
    const display = document.getElementById('referrerDisplay');
    if (!display) return;

    if (this.referrerLoading) {
      display.innerHTML = `
        <div class="referrer-loading">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
            <circle cx="12" cy="12" r="10"></circle>
            <path d="M12 6v6l4 2"></path>
          </svg>
          Verifying MNR ID...
        </div>
      `;
      return;
    }

    if (this.referrerError) {
      display.innerHTML = `
        <div class="referrer-error">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="15" y1="9" x2="9" y2="15"></line>
            <line x1="9" y1="9" x2="15" y2="15"></line>
          </svg>
          ${this.referrerError}
        </div>
      `;
      return;
    }

    if (this.referrerInfo) {
      display.innerHTML = `
        <div class="referrer-info">
          <div class="referrer-avatar">${this.getInitials(this.referrerInfo.name)}</div>
          <div class="referrer-details">
            <div class="referrer-name">${this.referrerInfo.name}</div>
            <div class="referrer-id">MNR ID: ${this.referrerInfo.mnr_id}</div>
          </div>
          <span class="referrer-status ${this.referrerInfo.active_status ? 'active' : 'pending'}">
            ${this.referrerInfo.active_status ? 'Active' : 'Pending'}
          </span>
        </div>
      `;
    } else {
      display.innerHTML = '';
    }
  }

  private async lookupReferrer(mnrId: string): Promise<void> {
    if (!mnrId.trim()) {
      this.referrerError = 'Please enter an MNR ID';
      this.referrerInfo = null;
      this.updateReferrerDisplay();
      return;
    }

    this.referrerLoading = true;
    this.referrerError = '';
    this.updateReferrerDisplay();

    try {
      const response = await apiService.get<any>(`/users/${mnrId}/basic-info`);
      
      if (response.success && response.data) {
        this.referrerInfo = {
          name: response.data.name || 'Unknown',
          mnr_id: response.data.mnr_id || mnrId,
          active_status: response.data.active_status || false
        };
        this.referrerError = '';
      } else {
        this.referrerError = response.error || 'Member not found';
        this.referrerInfo = null;
      }
    } catch (error) {
      console.error('[MNRAddMember] Referrer lookup failed:', error);
      this.referrerError = 'Failed to verify MNR ID';
      this.referrerInfo = null;
    }

    this.referrerLoading = false;
    this.updateReferrerDisplay();
  }

  private getInitials(name: string): string {
    if (!name) return '?';
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  }

  private attachFormListeners(): void {
    const form = document.getElementById('addMemberForm');
    form?.addEventListener('submit', (e) => {
      e.preventDefault();
      this.handleSubmit();
    });

    // [DC-PHONE-OTP-001] Expose OTP helpers as global functions for inline onclick handlers
    (window as any).mnrMobileSendOTP = async () => {
      const mobile = (document.getElementById('mobile') as HTMLInputElement)?.value.replace(/[^0-9]/g, '');
      if (!mobile || mobile.length < 10) {
        alert('Please enter a valid 10-digit mobile number first.');
        return;
      }
      const btn = document.getElementById('mnrMobileSendOtpBtn') as HTMLButtonElement;
      if (btn) { btn.disabled = true; btn.textContent = 'Sending…'; }
      document.getElementById('mnrMobileOtpSection')!.style.display = 'none';
      document.getElementById('mnrMobileVerifiedBadge')!.style.display = 'none';
      document.getElementById('mnrMobilePhoneToken' as any)!.setAttribute('value', '');
      try {
        const r = await fetch('/api/v1/users/send-otp', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ phone: mobile })
        });
        const d = await r.json();
        if (r.ok && d.success) {
          document.getElementById('mnrMobileOtpSection')!.style.display = 'block';
          (document.getElementById('mnrMobileOtpInput') as HTMLInputElement).value = '';
          document.getElementById('mnrMobileOtpInput')!.focus();
        } else {
          alert(d.detail || d.message || 'Failed to send OTP. Please try again.');
        }
      } catch { alert('Network error. Please try again.'); }
      finally {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 1.17h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.7A16 16 0 0 0 13.3 14.09l.95-.95a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 21.02 15.5z"/></svg> Send OTP to WhatsApp`;
        }
      }
    };

    (window as any).mnrMobileVerifyOTP = async () => {
      const mobile = (document.getElementById('mobile') as HTMLInputElement)?.value.replace(/[^0-9]/g, '');
      const otpCode = (document.getElementById('mnrMobileOtpInput') as HTMLInputElement)?.value.trim();
      if (!otpCode || otpCode.length !== 6) {
        alert('Please enter the 6-digit OTP from WhatsApp.');
        return;
      }
      const btn = document.getElementById('mnrMobileVerifyBtn') as HTMLButtonElement;
      if (btn) { btn.disabled = true; btn.textContent = 'Verifying…'; }
      try {
        const r = await fetch('/api/v1/users/verify-otp', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ phone: mobile, otp_code: otpCode })
        });
        const d = await r.json();
        if (r.ok && d.success) {
          (document.getElementById('mnrMobilePhoneToken') as HTMLInputElement).value = d.phone_verified_token;
          document.getElementById('mnrMobileOtpSection')!.style.display = 'none';
          const badge = document.getElementById('mnrMobileVerifiedBadge')!;
          badge.style.display = 'flex';
        } else {
          alert(d.detail || d.message || 'Invalid OTP. Please try again.');
        }
      } catch { alert('Network error. Please try again.'); }
      finally { if (btn) { btn.disabled = false; btn.textContent = 'Verify'; } }
    };

    const lookupBtn = document.getElementById('lookupBtn');
    lookupBtn?.addEventListener('click', () => {
      const referrerId = (document.getElementById('referrerId') as HTMLInputElement)?.value.trim();
      this.lookupReferrer(referrerId);
    });

    const referrerInput = document.getElementById('referrerId') as HTMLInputElement;
    referrerInput?.addEventListener('blur', () => {
      const value = referrerInput.value.trim();
      if (value && value !== this.currentUser?.mnr_id) {
        this.lookupReferrer(value);
      } else if (value === this.currentUser?.mnr_id) {
        this.referrerInfo = {
          name: this.currentUser.name || 'You',
          mnr_id: this.currentUser.mnr_id,
          active_status: true
        };
        this.referrerError = '';
        this.updateReferrerDisplay();
      }
    });

    const positionCards = document.querySelectorAll('.position-card');
    positionCards.forEach(card => {
      card.addEventListener('click', () => {
        positionCards.forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        const positionInput = document.getElementById('position') as HTMLInputElement;
        if (positionInput) {
          positionInput.value = (card as HTMLElement).dataset.position || 'auto';
        }
      });
    });
  }

  private async handleSubmit(): Promise<void> {
    const firstName = (document.getElementById('firstName') as HTMLInputElement)?.value.trim();
    const lastName = (document.getElementById('lastName') as HTMLInputElement)?.value.trim();
    const salutation = (document.getElementById('salutation') as HTMLSelectElement)?.value;
    const mobile = (document.getElementById('mobile') as HTMLInputElement)?.value.trim();
    const password = (document.getElementById('password') as HTMLInputElement)?.value;
    const address = (document.getElementById('address') as HTMLTextAreaElement)?.value.trim();
    const city = (document.getElementById('city') as HTMLInputElement)?.value.trim();
    const state = (document.getElementById('state') as HTMLInputElement)?.value.trim();
    const pincode = (document.getElementById('pincode') as HTMLInputElement)?.value.trim();
    const referrerId = (document.getElementById('referrerId') as HTMLInputElement)?.value.trim();
    const position = (document.getElementById('position') as HTMLInputElement)?.value;

    if (!firstName || !lastName || !salutation || !mobile || !password) {
      alert('Please fill all required fields');
      return;
    }

    if (mobile.length !== 10) {
      alert('Please enter a valid 10-digit mobile number');
      return;
    }

    // [DC-PHONE-OTP-001] Phone verification is required
    const phoneVerifiedToken = (document.getElementById('mnrMobilePhoneToken') as HTMLInputElement)?.value.trim();
    if (!phoneVerifiedToken) {
      alert('Phone verification required. Please tap "Send OTP to WhatsApp", enter the code, and tap Verify before adding the member.');
      return;
    }

    if (password.length < 6) {
      alert('Password must be at least 6 characters');
      return;
    }

    const submitBtn = document.getElementById('submitBtn') as HTMLButtonElement;
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
          <circle cx="12" cy="12" r="10"></circle>
          <path d="M12 6v6l4 2"></path>
        </svg>
        Adding Member...
      `;
    }

    const fullName = `${salutation}. ${firstName} ${lastName}`.trim();

    try {
      const response = await apiService.post<any>('/users/register', {
        name: fullName,
        first_name: firstName,
        last_name: lastName,
        salutation: salutation,
        mobile,
        password,
        address: address || null,
        city: city || null,
        state: state || null,
        pincode: pincode || null,
        sponsor_id: referrerId || null,
        position: position === 'auto' ? 'Left' : position,
        phone_verified_token: phoneVerifiedToken
      });

      if (response.success) {
        const newMnrId = response.data?.mnr_id || 'Generated';
        alert(`Member added successfully!\n\nMNR ID: ${newMnrId}`);
        routerService.navigate('mnr-dashboard');
      } else {
        alert(response.error || 'Failed to add member');
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="8.5" cy="7" r="4"></circle>
              <line x1="20" y1="8" x2="20" y2="14"></line>
              <line x1="23" y1="11" x2="17" y2="11"></line>
            </svg>
            Add Member
          `;
        }
      }
    } catch (error) {
      console.error('[MNRAddMember] Submit failed:', error);
      alert('Failed to add member. Please try again.');
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = `
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
            <circle cx="8.5" cy="7" r="4"></circle>
            <line x1="20" y1="8" x2="20" y2="14"></line>
            <line x1="23" y1="11" x2="17" y2="11"></line>
          </svg>
          Add Member
        `;
      }
    }
  }
}
