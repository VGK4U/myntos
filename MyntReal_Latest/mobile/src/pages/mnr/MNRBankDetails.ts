/**
 * MNR Bank Details Page
 * DC Protocol: DC_MOBILE_MNR_BANK_001
 * View and manage bank account details
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';

interface BankDetails {
  bank_name: string;
  account_holder_name: string;
  account_number: string;
  ifsc_code: string;
  branch: string;
  is_verified: boolean;
}

export class MNRBankDetails {
  private container: HTMLElement;
  private bankDetails: BankDetails | null = null;
  private loading: boolean = true;
  private editMode: boolean = false;
  private saving: boolean = false;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadBankDetails();
  }

  private async loadBankDetails(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<any>('/users/profile/banking');
      if (response.success && response.data) {
        this.bankDetails = response.data;
      }
    } catch (error) {
      console.error('[MNRBankDetails] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: '🏦 Bank Details', showBack: true })}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: '🏦 Bank Details', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    const bank = this.bankDetails;

    if (this.editMode || !bank || !bank.bank_name) {
      content.innerHTML = this.renderEditForm(bank);
      this.attachEditListeners();
      return;
    }

    content.innerHTML = `
      <div class="bank-card card">
        <div class="bank-header">
          <div class="bank-logo">🏦</div>
          <div class="bank-name-section">
            <h3>${bank.bank_name}</h3>
            <span class="verify-badge ${bank.is_verified ? 'verified' : 'pending'}">
              ${bank.is_verified ? '✓ Verified' : '⏳ Pending'}
            </span>
          </div>
        </div>
        
        <div class="bank-details-grid">
          <div class="detail-row">
            <span class="detail-label">Account Holder</span>
            <span class="detail-value">${bank.account_holder_name || 'N/A'}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Account Number</span>
            <span class="detail-value">${this.maskAccount(bank.account_number)}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">IFSC Code</span>
            <span class="detail-value">${bank.ifsc_code || 'N/A'}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Branch</span>
            <span class="detail-value">${bank.branch || 'N/A'}</span>
          </div>
        </div>
        
        <button class="btn btn-primary btn-full" id="editBankBtn">
          ✏️ Edit Bank Details
        </button>
      </div>

      <div class="bank-info card">
        <h4>Important Notes</h4>
        <ul class="info-list">
          <li>Bank verification takes 24-48 hours</li>
          <li>Withdrawals will be credited to this account</li>
          <li>Contact support to update bank details</li>
          <li>Account name must match your registered name</li>
        </ul>
      </div>
    `;

    document.getElementById('editBankBtn')?.addEventListener('click', () => {
      this.editMode = true;
      this.updateContent();
    });
  }

  private renderEditForm(bank: BankDetails | null): string {
    return `
      <div class="edit-form card">
        <h3 class="form-title">💳 ${bank?.bank_name ? 'Edit' : 'Add'} Bank Details</h3>
        
        <div class="form-group">
          <label>Bank Name *</label>
          <input type="text" id="bankName" class="form-input" 
            value="${bank?.bank_name || ''}" placeholder="Enter bank name" required>
        </div>
        
        <div class="form-group">
          <label>Account Holder Name *</label>
          <input type="text" id="accountHolder" class="form-input" 
            value="${bank?.account_holder_name || ''}" placeholder="Name as per bank account" required>
        </div>
        
        <div class="form-group">
          <label>Account Number *</label>
          <input type="text" id="accountNumber" class="form-input" 
            value="${bank?.account_number || ''}" placeholder="Enter account number" required>
        </div>
        
        <div class="form-group">
          <label>IFSC Code *</label>
          <input type="text" id="ifscCode" class="form-input" 
            value="${bank?.ifsc_code || ''}" placeholder="e.g., SBIN0001234" required>
        </div>
        
        <div class="form-group">
          <label>Branch</label>
          <input type="text" id="branchName" class="form-input" 
            value="${bank?.branch || ''}" placeholder="Branch name">
        </div>
        
        <div class="form-actions">
          <button class="btn btn-secondary" id="cancelEditBtn" ${this.saving ? 'disabled' : ''}>
            Cancel
          </button>
          <button class="btn btn-primary" id="saveBankBtn" ${this.saving ? 'disabled' : ''}>
            ${this.saving ? 'Saving...' : 'Save Details'}
          </button>
        </div>
      </div>
    `;
  }

  private attachEditListeners(): void {
    document.getElementById('cancelEditBtn')?.addEventListener('click', () => {
      if (this.bankDetails?.bank_name) {
        this.editMode = false;
        this.updateContent();
      }
    });

    document.getElementById('saveBankBtn')?.addEventListener('click', () => {
      this.saveBankDetails();
    });
  }

  private async saveBankDetails(): Promise<void> {
    const bankName = (document.getElementById('bankName') as HTMLInputElement)?.value?.trim();
    const accountHolder = (document.getElementById('accountHolder') as HTMLInputElement)?.value?.trim();
    const accountNumber = (document.getElementById('accountNumber') as HTMLInputElement)?.value?.trim();
    const ifscCode = (document.getElementById('ifscCode') as HTMLInputElement)?.value?.trim();
    const branch = (document.getElementById('branchName') as HTMLInputElement)?.value?.trim();

    if (!bankName || !accountHolder || !accountNumber || !ifscCode) {
      alert('Please fill in all required fields');
      return;
    }

    this.saving = true;
    this.updateContent();

    try {
      const response = await apiService.put<any>('/users/profile/banking', {
        bank_name: bankName,
        account_holder_name: accountHolder,
        account_number: accountNumber,
        ifsc_code: ifscCode,
        branch: branch || null
      });

      if (response.success) {
        alert('Bank details saved successfully!');
        this.editMode = false;
        await this.loadBankDetails();
      } else {
        alert(response.error || 'Failed to save bank details');
      }
    } catch (error) {
      console.error('[MNRBankDetails] Save failed:', error);
      alert('Failed to save bank details. Please try again.');
    } finally {
      this.saving = false;
    }
  }

  private maskAccount(num: string): string {
    if (!num || num.length <= 4) return num || 'N/A';
    return 'XXXXXXXX' + num.slice(-4);
  }
}
