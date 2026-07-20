/**
 * Staff My KYC Page
 * DC Protocol: DC_MOBILE_STAFF_KYC_001
 * View and upload staff KYC documents including Previous Experience section
 * Enhanced Jan 2026: Experience documents support for experienced employees
 */

import { apiService } from '../services/api.service';
import { authService } from '../services/auth.service';
import { PageHeader } from '../components/PageHeader';

interface KYCData {
  id?: number;
  documents?: Record<string, any>;
  status?: string;
  profile_photo?: string;
  bank_statement_1_url?: string;
  bank_statement_2_url?: string;
  bank_statement_3_url?: string;
  offer_letter_url?: string;
  pay_slip_1_url?: string;
  pay_slip_2_url?: string;
  pay_slip_3_url?: string;
  experience_docs_status?: string;
}

interface EmployeeData {
  id?: number;
  emp_code?: string;
  full_name?: string;
  is_experienced?: boolean;
}

export class StaffKYCPage {
  private container: HTMLElement;
  private kycData: KYCData = {};
  private employeeData: EmployeeData = {};
  private isExperienced: boolean = false;
  private loading: boolean = true;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadDocuments();
  }

  private async loadDocuments(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<any>('/staff/kyc/my');
      if (response.success) {
        this.kycData = response.data?.kyc || {};
        this.employeeData = response.data?.employee || {};
        
        // Check if user is experienced employee from auth state or API response
        const authState = await authService.getAuthState();
        this.isExperienced = authState?.user?.is_experienced || this.employeeData.is_experienced || false;
      }
    } catch (error) {
      console.error('[StaffKYC] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'My KYC Documents', showBack: true })}
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: 'My KYC Documents', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    const docs = this.kycData.documents || {};
    const docCount = Object.keys(docs).length;
    const kycStatus = this.kycData.status || 'pending';

    content.innerHTML = `
      <div class="kyc-summary card">
        <div class="summary-grid">
          <div class="summary-item">
            <span class="summary-value">${docCount}</span>
            <span class="summary-label">Documents</span>
          </div>
          <div class="summary-item">
            <span class="summary-value ${kycStatus}">${kycStatus.toUpperCase()}</span>
            <span class="summary-label">Status</span>
          </div>
        </div>
      </div>

      <div class="upload-section card">
        <h4>Upload Document</h4>
        <select id="docType" class="form-input">
          <option value="">Select Document Type</option>
          <option value="profile_photo">Profile Photo</option>
          <option value="aadhaar_front">Aadhaar Front</option>
          <option value="aadhaar_back">Aadhaar Back</option>
          <option value="pan_card">PAN Card</option>
          <option value="passport_photo">Passport Photo</option>
          <option value="driving_license">Driving License</option>
          <option value="voter_id">Voter ID</option>
          <option value="bank_passbook">Bank Passbook</option>
          <option value="cancelled_cheque">Cancelled Cheque</option>
        </select>
        <input type="file" id="fileInput" accept="image/*,.pdf" style="display: none;">
        <button class="btn btn-primary" id="uploadBtn">Select & Upload Document</button>
      </div>

      ${this.isExperienced ? this.renderExperienceSection() : ''}

      <h4 class="section-title">Uploaded Documents</h4>
      ${docCount > 0 ? `
        <div class="documents-list">
          ${Object.entries(docs).map(([type, info]) => this.renderDocument(type, info)).join('')}
        </div>
      ` : `
        <div class="empty-state card">
          <div class="empty-icon">📄</div>
          <p>No KYC documents uploaded yet</p>
        </div>
      `}
    `;

    this.attachListeners();
  }

  private renderExperienceSection(): string {
    const kyc = this.kycData;
    const expStatus = kyc.experience_docs_status || 'pending';
    const statusBadge = expStatus === 'verified' ? 'status-approved' : 
                        expStatus === 'submitted' ? 'status-submitted' : 'status-pending';

    const docSlots = [
      { key: 'bank_statement_1', label: 'Bank Statement 1', url: kyc.bank_statement_1_url },
      { key: 'bank_statement_2', label: 'Bank Statement 2', url: kyc.bank_statement_2_url },
      { key: 'bank_statement_3', label: 'Bank Statement 3', url: kyc.bank_statement_3_url },
      { key: 'offer_letter', label: 'Offer Letter (Previous Employer)', url: kyc.offer_letter_url },
      { key: 'pay_slip_1', label: 'Pay Slip 1', url: kyc.pay_slip_1_url },
      { key: 'pay_slip_2', label: 'Pay Slip 2', url: kyc.pay_slip_2_url },
      { key: 'pay_slip_3', label: 'Pay Slip 3', url: kyc.pay_slip_3_url },
    ];

    const uploadedCount = docSlots.filter(d => d.url).length;

    return `
      <div class="experience-section card">
        <div class="section-header">
          <h4>Previous Experience Documents</h4>
          <span class="status-badge ${statusBadge}">${expStatus.toUpperCase()}</span>
        </div>
        <p class="section-description">
          As an experienced employee, please upload all 7 required documents from your previous employment.
        </p>
        <div class="progress-bar">
          <div class="progress-fill" style="width: ${(uploadedCount/7)*100}%"></div>
        </div>
        <p class="progress-text">${uploadedCount}/7 documents uploaded</p>

        <div class="experience-docs-grid">
          ${docSlots.map(slot => `
            <div class="exp-doc-slot ${slot.url ? 'uploaded' : 'pending'}">
              <div class="slot-header">
                <span class="slot-label">${slot.label}</span>
                ${slot.url ? '<span class="check-icon">✓</span>' : '<span class="pending-icon">○</span>'}
              </div>
              ${slot.url ? `
                <button class="btn btn-sm btn-secondary view-exp-doc" data-url="${slot.url}">View</button>
              ` : `
                <button class="btn btn-sm btn-primary upload-exp-doc" data-type="${slot.key}">Upload</button>
              `}
            </div>
          `).join('')}
        </div>

        <input type="file" id="expFileInput" accept="image/*,.pdf" style="display: none;">
      </div>

      <style>
        .experience-section { margin: 16px 0; padding: 16px; }
        .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .section-description { color: #666; font-size: 14px; margin-bottom: 12px; }
        .progress-bar { height: 8px; background: #e0e0e0; border-radius: 4px; overflow: hidden; }
        .progress-fill { height: 100%; background: #4CAF50; transition: width 0.3s; }
        .progress-text { font-size: 12px; color: #666; margin-top: 4px; text-align: right; }
        .experience-docs-grid { display: grid; gap: 12px; margin-top: 16px; }
        .exp-doc-slot { display: flex; justify-content: space-between; align-items: center; padding: 12px; background: #f5f5f5; border-radius: 8px; }
        .exp-doc-slot.uploaded { background: #e8f5e9; border: 1px solid #4CAF50; }
        .slot-header { display: flex; align-items: center; gap: 8px; }
        .slot-label { font-size: 14px; font-weight: 500; }
        .check-icon { color: #4CAF50; font-weight: bold; }
        .pending-icon { color: #999; }
        .btn-sm { padding: 6px 12px; font-size: 12px; }
        .status-badge { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
        .status-approved { background: #e8f5e9; color: #2e7d32; }
        .status-submitted { background: #fff3e0; color: #f57c00; }
        .status-pending { background: #f5f5f5; color: #666; }
      </style>
    `;
  }

  private renderDocument(type: string, info: any): string {
    const uploadedAt = info?.uploaded_at ? new Date(info.uploaded_at).toLocaleDateString('en', { 
      day: 'numeric', month: 'short', year: 'numeric' 
    }) : '';

    return `
      <div class="document-card card">
        <div class="doc-header">
          <h4>${this.formatDocType(type)}</h4>
        </div>
        <div class="doc-meta">
          ${uploadedAt ? `<span>Uploaded: ${uploadedAt}</span>` : ''}
        </div>
      </div>
    `;
  }

  private formatDocType(type: string): string {
    const types: Record<string, string> = {
      'profile_photo': 'Profile Photo',
      'aadhaar_front': 'Aadhaar Front',
      'aadhaar_back': 'Aadhaar Back',
      'pan_card': 'PAN Card',
      'passport_photo': 'Passport Photo',
      'driving_license': 'Driving License',
      'voter_id': 'Voter ID',
      'bank_passbook': 'Bank Passbook',
      'cancelled_cheque': 'Cancelled Cheque',
      'bank_statement_1': 'Bank Statement 1',
      'bank_statement_2': 'Bank Statement 2',
      'bank_statement_3': 'Bank Statement 3',
      'offer_letter': 'Offer Letter',
      'pay_slip_1': 'Pay Slip 1',
      'pay_slip_2': 'Pay Slip 2',
      'pay_slip_3': 'Pay Slip 3'
    };
    return types[type] || type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }

  private attachListeners(): void {
    const fileInput = document.getElementById('fileInput') as HTMLInputElement;
    const uploadBtn = document.getElementById('uploadBtn');

    uploadBtn?.addEventListener('click', () => fileInput?.click());
    fileInput?.addEventListener('change', () => this.handleUpload());

    // Experience document upload handlers
    const expFileInput = document.getElementById('expFileInput') as HTMLInputElement;
    let currentExpDocType = '';

    document.querySelectorAll('.upload-exp-doc').forEach(btn => {
      btn.addEventListener('click', (e) => {
        currentExpDocType = (e.target as HTMLElement).dataset.type || '';
        expFileInput?.click();
      });
    });

    expFileInput?.addEventListener('change', async () => {
      if (!currentExpDocType || !expFileInput.files?.[0]) return;
      await this.handleExpDocUpload(currentExpDocType, expFileInput.files[0]);
      expFileInput.value = '';
      currentExpDocType = '';
    });

    document.querySelectorAll('.view-exp-doc').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const url = (e.target as HTMLElement).dataset.url;
        if (url) window.open(url, '_blank');
      });
    });
  }

  private async handleUpload(): Promise<void> {
    const fileInput = document.getElementById('fileInput') as HTMLInputElement;
    const docType = (document.getElementById('docType') as HTMLSelectElement)?.value;

    if (!docType) {
      alert('Please select a document type');
      return;
    }

    const file = fileInput?.files?.[0];
    if (!file) return;

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('document_type', docType);

      const response = await apiService.uploadFile('/staff/kyc/upload-document', formData);
      if (response.success) {
        alert('Document uploaded successfully!');
        await this.loadDocuments();
      } else {
        alert(response.error || 'Upload failed');
      }
    } catch (error) {
      console.error('[StaffKYC] Upload error:', error);
      alert('Failed to upload document');
    }

    fileInput.value = '';
  }

  private async handleExpDocUpload(docType: string, file: File): Promise<void> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('document_type', docType);

      const response = await apiService.uploadFile('/staff/kyc/upload-document', formData);
      if (response.success) {
        alert(`${this.formatDocType(docType)} uploaded successfully!`);
        await this.loadDocuments();
      } else {
        alert(response.error || 'Upload failed');
      }
    } catch (error) {
      console.error('[StaffKYC] Experience doc upload error:', error);
      alert('Failed to upload document');
    }
  }
}
