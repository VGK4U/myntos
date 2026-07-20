/**
 * MNR Profile Page
 * DC Protocol: DC_MOBILE_MNR_PROFILE_001
 * View and manage MNR member profile
 */

import { authService } from '../../services/auth.service';
import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';
import { routerService } from '../../services/router.service';

export class MNRProfile {
  private container: HTMLElement;
  private user: any = null;
  private profile: any = null;
  private loading: boolean = true;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    const authState = authService.getAuthState();
    this.user = authState.user;
    this.render();
    await this.loadProfile();
  }

  private async loadProfile(): Promise<void> {
    this.loading = true;
    
    try {
      const response = await apiService.get<any>('/users/profile');
      if (response.success && response.data) {
        this.profile = response.data;
      }
    } catch (error) {
      console.error('[MNRProfile] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    const username = this.user?.name || this.user?.mnr_id || 'Member';
    const initials = this.getInitials(username);

    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: '👤 My Profile', showBack: true })}
        
        <div class="profile-header card">
          <div class="profile-avatar">${initials}</div>
          <h2 class="profile-name">${username}</h2>
          <p class="profile-id">${this.user?.mnr_id || ''}</p>
          <p class="profile-package">${this.user?.package_name || 'Standard'}</p>
        </div>

        <div id="profileContent">
          <div class="loading-state">Loading...</div>
        </div>

        <div class="menu-list">
          <button class="menu-item" data-page="mnr-referrals">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
            </svg>
            <span>My Referrals</span>
            <svg class="chevron" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
          <button class="menu-item" data-page="mnr-kyc">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="4" width="18" height="16" rx="2"/>
              <path d="M7 8h10"/>
              <path d="M7 12h10"/>
              <path d="M7 16h6"/>
            </svg>
            <span>KYC Documents</span>
            <svg class="chevron" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
          <button class="menu-item" data-page="mnr-bank">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="1" y="4" width="22" height="16" rx="2" ry="2"/>
              <line x1="1" y1="10" x2="23" y2="10"/>
            </svg>
            <span>Bank Details</span>
            <svg class="chevron" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
          <button class="menu-item" data-page="settings">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="3"/>
              <path d="M12 1v6m0 6v10"/>
            </svg>
            <span>Settings</span>
            <svg class="chevron" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
        </div>
      </div>
    `;

    this.attachListeners();
  }

  private attachListeners(): void {
    PageHeader.attachListeners({ title: '👤 My Profile', showBack: true });

    this.container.querySelectorAll('.menu-item[data-page]').forEach(btn => {
      btn.addEventListener('click', () => {
        const page = btn.getAttribute('data-page');
        if (page) routerService.navigate(page as any);
      });
    });
  }

  private updateContent(): void {
    const content = document.getElementById('profileContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    const p = this.profile || this.user || {};

    content.innerHTML = `
      <!-- Personal Information Section - Web Parity -->
      <div class="mnr-section-card personal-info">
        <div class="section-header-bar green">
          <h3>Personal Information</h3>
          <button class="edit-btn" id="editPersonalBtn">Edit</button>
        </div>
        <div class="section-content">
          <div class="info-grid">
            <div class="info-row">
              <span class="info-label">Name:</span>
              <span class="info-value">${p.name || 'Not provided'}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Email:</span>
              <span class="info-value">${p.email || 'Not provided'}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Mobile:</span>
              <span class="info-value">${p.mobile || 'Not provided'}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Gender:</span>
              <span class="info-value">${p.gender || 'Not provided'}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Actual DOB:</span>
              <span class="info-value">${p.actual_dob ? this.formatDate(p.actual_dob) : 'Not provided'}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Certificate DOB:</span>
              <span class="info-value">${p.certificate_dob ? this.formatDate(p.certificate_dob) : 'Not provided'}</span>
            </div>
          </div>
          <div class="address-section">
            <span class="info-label">Address:</span>
            <span class="info-value">${this.formatAddress(p)}</span>
          </div>
        </div>
      </div>

      <!-- KYC Documents Section - Web Parity -->
      <div class="mnr-section-card kyc-section">
        <div class="section-header-bar orange">
          <h3>KYC Documents</h3>
          <span class="status-badge ${p.kyc_status === 'Verified' ? 'verified' : 'pending'}">${p.kyc_status || 'Pending'}</span>
          <button class="edit-btn" id="editKycBtn">Edit</button>
        </div>
        <div class="section-content">
          <div class="info-grid">
            <div class="info-row">
              <span class="info-label">Aadhaar Number:</span>
              <span class="info-value">${p.aadhaar_number || 'Not provided'}</span>
            </div>
            <div class="info-row">
              <span class="info-label">PAN Number:</span>
              <span class="info-value">${p.pan_number || 'Not provided'}</span>
            </div>
          </div>
          <div class="doc-upload-grid">
            <div class="doc-item">
              <span class="doc-label">Aadhaar Front:</span>
              <span class="doc-status ${p.aadhaar_front_url ? 'uploaded' : 'not-uploaded'}">${p.aadhaar_front_url ? 'Uploaded' : 'Not Uploaded'}</span>
            </div>
            <div class="doc-item">
              <span class="doc-label">Aadhaar Back:</span>
              <span class="doc-status ${p.aadhaar_back_url ? 'uploaded' : 'not-uploaded'}">${p.aadhaar_back_url ? 'Uploaded' : 'Not Uploaded'}</span>
            </div>
            <div class="doc-item">
              <span class="doc-label">PAN Card:</span>
              <span class="doc-status ${p.pan_url ? 'uploaded' : 'not-uploaded'}">${p.pan_url ? 'Uploaded' : 'Not Uploaded'}</span>
            </div>
            <div class="doc-item">
              <span class="doc-label">Passport Photo:</span>
              <span class="doc-status ${p.passport_photo_url ? 'uploaded' : 'not-uploaded'}">${p.passport_photo_url ? 'Uploaded' : 'Not Uploaded'}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Bank Details Section - Web Parity -->
      <div class="mnr-section-card bank-section">
        <div class="section-header-bar purple">
          <h3>Bank Details</h3>
          <span class="status-badge ${p.bank_name ? 'submitted' : 'not-submitted'}">${p.bank_name ? 'Submitted' : 'Not Submitted'}</span>
          <button class="edit-btn" id="editBankBtn">Edit</button>
        </div>
        <div class="section-content">
          <div class="info-grid">
            <div class="info-row">
              <span class="info-label">Bank Name:</span>
              <span class="info-value">${p.bank_name || 'Not provided'}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Account Holder:</span>
              <span class="info-value">${p.account_holder_name || 'Not provided'}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Account Number:</span>
              <span class="info-value">${p.account_number ? this.maskNumber(p.account_number) : 'Not provided'}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Branch:</span>
              <span class="info-value">${p.branch || 'Not provided'}</span>
            </div>
            <div class="info-row">
              <span class="info-label">IFSC Code:</span>
              <span class="info-value">${p.ifsc_code || 'Not provided'}</span>
            </div>
            <div class="info-row">
              <span class="info-label">UPI ID:</span>
              <span class="info-value">${p.upi_id || 'Not provided'}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Back to Dashboard Button -->
      <button class="btn btn-secondary btn-full" id="backToDashboard">
        ← Back to Dashboard
      </button>
    `;

    this.attachContentListeners();
  }

  private attachContentListeners(): void {
    document.getElementById('editPersonalBtn')?.addEventListener('click', () => {
      routerService.navigate('mnr-profile-edit');
    });
    document.getElementById('editKycBtn')?.addEventListener('click', () => {
      routerService.navigate('mnr-kyc');
    });
    document.getElementById('editBankBtn')?.addEventListener('click', () => {
      routerService.navigate('mnr-bank');
    });
    document.getElementById('backToDashboard')?.addEventListener('click', () => {
      routerService.navigate('mnr-dashboard');
    });
  }

  private showToast(message: string): void {
    const toast = document.createElement('div');
    toast.className = 'toast-message';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
  }

  private formatAddress(p: any): string {
    const parts = [p.address, p.city, p.state, p.pincode].filter(Boolean);
    return parts.length > 0 ? parts.join(', ') : 'Not provided';
  }

  private maskNumber(num: string): string {
    if (!num || num.length <= 4) return num || 'N/A';
    return 'XXXXXXXX' + num.slice(-4);
  }

  private getInitials(name: string): string {
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return 'Not provided';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', { 
      day: '2-digit', 
      month: '2-digit', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}
