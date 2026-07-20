/**
 * MNR KYC Page
 * DC Protocol: DC_MOBILE_MNR_KYC_001
 * View and manage KYC document status with upload capability
 */

import { apiService } from '../../services/api.service';
import { authService } from '../../services/auth.service';
import { PageHeader } from '../../components/PageHeader';

interface KYCDocument {
  type: string;
  key: string;
  status: string;
  number: string;
  verified_on: string | null;
  canUpload: boolean;
  url?: string;
}

interface KYCStatus {
  overall_status: string;
  profile_photo: KYCDocument;
  passport_photo: KYCDocument;
  aadhaar: KYCDocument;
  pan: KYCDocument;
  bank: KYCDocument;
}

export class MNRKYC {
  private container: HTMLElement;
  private kycStatus: KYCStatus | null = null;
  private loading: boolean = true;
  private uploading: string | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadKYC();
  }

  private async loadKYC(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<any>('/users/profile');
      if (response.success && response.data) {
        const p = response.data;
        this.kycStatus = {
          overall_status: p.kyc_status || 'Pending',
          profile_photo: {
            type: 'Profile Photo',
            key: 'profile_photo',
            status: p.profile_photo_url ? 'Uploaded' : 'Required',
            number: p.profile_photo_url ? 'Photo uploaded' : 'Please upload',
            verified_on: null,
            canUpload: true,
            url: p.profile_photo_url
          },
          passport_photo: {
            type: 'Passport Size Photo',
            key: 'passport_photo',
            status: p.passport_photo_url ? 'Uploaded' : 'Required',
            number: p.passport_photo_url ? 'Photo uploaded' : 'Please upload',
            verified_on: null,
            canUpload: true,
            url: p.passport_photo_url
          },
          aadhaar: {
            type: 'Aadhaar Card',
            key: 'aadhaar',
            status: p.aadhaar_number ? 'Verified' : 'Pending',
            number: p.aadhaar_number ? this.maskNumber(p.aadhaar_number) : 'Not provided',
            verified_on: null,
            canUpload: !p.aadhaar_number,
            url: p.aadhaar_front_url
          },
          pan: {
            type: 'PAN Card',
            key: 'pan',
            status: p.pan_number ? 'Verified' : 'Pending',
            number: p.pan_number ? this.maskNumber(p.pan_number) : 'Not provided',
            verified_on: null,
            canUpload: !p.pan_number,
            url: p.pan_url
          },
          bank: {
            type: 'Bank Passbook',
            key: 'bank',
            status: p.bank_name ? 'Verified' : 'Pending',
            number: p.bank_name || 'Not linked',
            verified_on: null,
            canUpload: !p.bank_name
          }
        };
      }
    } catch (error) {
      console.error('[MNRKYC] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: '📄 KYC Documents', showBack: true })}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
      
      <input type="file" id="kycFileInput" accept="image/*,.pdf" style="display:none">
    `;

    PageHeader.attachListeners({ title: '📄 KYC Documents', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    const kyc = this.kycStatus;
    const overallStatus = kyc?.overall_status || 'Pending';
    const statusClass = overallStatus.toLowerCase().replace(' ', '-');

    content.innerHTML = `
      <div class="kyc-status-banner card ${statusClass}">
        <div class="status-icon">
          ${overallStatus === 'Verified' ? '✓' : overallStatus === 'Rejected' ? '✗' : '⏳'}
        </div>
        <div class="status-info">
          <h3>KYC Status: ${overallStatus}</h3>
          <p>${this.getStatusMessage(overallStatus)}</p>
        </div>
      </div>

      <h3 class="section-title">Photo Documents</h3>
      <div class="kyc-documents photo-docs">
        ${this.renderDocument(kyc?.profile_photo)}
        ${this.renderDocument(kyc?.passport_photo)}
      </div>

      <h3 class="section-title">Identity Documents</h3>
      <div class="kyc-documents">
        ${this.renderDocument(kyc?.aadhaar)}
        ${this.renderDocument(kyc?.pan)}
        ${this.renderDocument(kyc?.bank)}
      </div>

      <div class="notice-card card info">
        <h4>📋 Upload Guidelines</h4>
        <ul>
          <li>Documents must be clear and readable</li>
          <li>Accepted formats: JPG, PNG, PDF</li>
          <li>Maximum file size: 5 MB</li>
          <li>Ensure all details are visible</li>
        </ul>
      </div>

      <div class="kyc-info card">
        <h4>Important Notes</h4>
        <ul class="info-list">
          <li>KYC verification is mandatory for withdrawals</li>
          <li>Documents are verified within 24-48 hours</li>
          <li>Ensure all details match your bank records</li>
          <li>Contact support if verification is delayed</li>
        </ul>
      </div>
    `;

    this.attachUploadListeners();
  }

  private attachUploadListeners(): void {
    document.querySelectorAll('.upload-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const docType = (e.currentTarget as HTMLElement).dataset.doc;
        if (docType) {
          this.initiateUpload(docType);
        }
      });
    });

    document.querySelectorAll('.view-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const url = (e.currentTarget as HTMLElement).dataset.url;
        if (url) window.open(url, '_blank');
      });
    });

    const fileInput = document.getElementById('kycFileInput') as HTMLInputElement;
    if (fileInput) {
      fileInput.addEventListener('change', async (e) => {
        const file = (e.target as HTMLInputElement).files?.[0];
        if (file && this.uploading) {
          await this.uploadDocument(this.uploading, file);
        }
        fileInput.value = '';
      });
    }
  }

  private initiateUpload(docType: string): void {
    this.uploading = docType;
    const fileInput = document.getElementById('kycFileInput') as HTMLInputElement;
    if (fileInput) {
      fileInput.click();
    }
  }

  private async uploadDocument(docType: string, file: File): Promise<void> {
    const btn = document.querySelector(`[data-doc="${docType}"]`);
    if (btn) {
      btn.textContent = 'Uploading...';
      (btn as HTMLButtonElement).disabled = true;
    }

    try {
      const formData = new FormData();
      formData.append('file', file);  // DC Protocol Feb 2026: Fix field name
      formData.append('document_type', docType);

      // DC Protocol Feb 2026: Fix endpoint path - use /profile/ not /users/
      const response = await apiService.uploadFile('/profile/upload-kyc-document', formData);
      
      if (response.success) {
        alert(`${docType.toUpperCase()} document uploaded successfully! It will be reviewed within 24-48 hours.`);
        await this.loadKYC();
      } else {
        alert(response.error || 'Failed to upload document. Please try again.');
      }
    } catch (error) {
      console.error('[MNRKYC] Upload failed:', error);
      alert('Failed to upload document. Please try again later.');
    } finally {
      this.uploading = null;
      if (btn) {
        btn.textContent = 'Upload';
        (btn as HTMLButtonElement).disabled = false;
      }
    }
  }

  private renderDocument(doc: KYCDocument | undefined): string {
    if (!doc) return '';
    const statusClass = doc.status.toLowerCase().replace(' ', '-');
    const isUploading = this.uploading === doc.key;
    const isPhoto = doc.key === 'profile_photo' || doc.key === 'passport_photo';
    const iconMap: Record<string, string> = {
      'profile_photo': '📷',
      'passport_photo': '🖼️',
      'aadhaar': '🪪',
      'pan': '📄',
      'bank': '🏦'
    };
    
    return `
      <div class="kyc-doc card ${statusClass}">
        <div class="doc-header">
          <div class="doc-icon">
            ${iconMap[doc.key] || '📄'}
          </div>
          <div class="doc-info">
            <h4>${doc.type}</h4>
            <p class="doc-number">${doc.number}</p>
          </div>
          <div class="doc-status ${statusClass}">
            ${doc.status}
          </div>
        </div>
        ${doc.url && isPhoto ? `
          <div class="photo-preview">
            <img src="${doc.url}" alt="${doc.type}" class="preview-img">
          </div>
        ` : ''}
        ${doc.canUpload || isPhoto ? `
          <div class="doc-actions">
            <button class="btn ${doc.url ? 'btn-secondary' : 'btn-primary'} upload-btn" data-doc="${doc.key}" ${isUploading ? 'disabled' : ''}>
              ${isUploading ? 'Uploading...' : doc.url ? 'Change Photo' : 'Upload'}
            </button>
            ${doc.url ? `<button class="btn btn-outline view-btn" data-url="${doc.url}">View</button>` : ''}
          </div>
        ` : `
          <div class="doc-verified">
            <span class="verified-badge">✓ Submitted</span>
          </div>
        `}
      </div>

      <style>
        .photo-preview { margin: 12px 0; text-align: center; }
        .preview-img { max-width: 120px; max-height: 120px; border-radius: 8px; border: 2px solid #64ffda; }
        .doc-actions { display: flex; gap: 8px; margin-top: 8px; }
        .doc-actions .btn { flex: 1; }
        .btn-outline { background: transparent; border: 1px solid #64ffda; color: #64ffda; }
        .photo-docs { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        @media (max-width: 400px) { .photo-docs { grid-template-columns: 1fr; } }
      </style>
    `;
  }

  private getStatusMessage(status: string): string {
    switch (status) {
      case 'Verified': return 'All documents verified successfully';
      case 'Rejected': return 'Some documents were rejected. Please re-upload.';
      case 'Pending': return 'Documents are under review';
      default: return 'Please complete your KYC';
    }
  }

  private maskNumber(num: string): string {
    if (num.length <= 4) return num;
    return 'XXXX' + num.slice(-4);
  }
}
