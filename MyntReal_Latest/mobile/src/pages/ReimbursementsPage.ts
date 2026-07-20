/**
 * Reimbursements Page
 * DC Protocol: DC_MOBILE_REIMBURSEMENTS_001
 * Submit and track expense reimbursement claims
 */

import { apiService } from '../services/api.service';
import { cameraService } from '../services/camera.service';
import { PageHeader } from '../components/PageHeader';

interface ReimbursementClaim {
  id: number;
  claim_number: string;
  category: string;
  amount: number;
  description: string;
  status: string;
  submitted_on: string;
  approved_amount: number | null;
  receipt_url: string | null;
}

export class ReimbursementsPage {
  private container: HTMLElement;
  private claims: ReimbursementClaim[] = [];
  private loading: boolean = true;
  private receiptBase64: string | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadClaims();
  }

  private async loadClaims(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<any>(
        '/staff/reimbursements/my-claims'
      );

      if (response.success && response.data) {
        this.claims = response.data.claims || response.data || [];
      }
    } catch (error) {
      console.error('[ReimbursementsPage] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ 
          title: 'Reimbursements', 
          showBack: true,
          rightAction: {
            icon: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
            </svg>`,
            onClick: () => this.showClaimForm()
          }
        })}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>

        <div id="claimModal" class="modal" style="display: none;">
          <div class="modal-content">
            <h3 class="modal-title">New Reimbursement Claim</h3>
            <form id="claimForm">
              <div class="input-group">
                <label class="input-label">Category</label>
                <select id="category" class="input" required>
                  <option value="">Select Category</option>
                  <option value="Travel">Travel</option>
                  <option value="Food">Food & Meals</option>
                  <option value="Communication">Communication</option>
                  <option value="Office Supplies">Office Supplies</option>
                  <option value="Other">Other</option>
                </select>
              </div>
              <div class="input-group">
                <label class="input-label">Amount (₹)</label>
                <input type="number" id="amount" class="input" placeholder="0.00" required />
              </div>
              <div class="input-group">
                <label class="input-label">Description</label>
                <textarea id="description" class="input" rows="3" required></textarea>
              </div>
              <div class="input-group">
                <label class="input-label">Receipt Photo</label>
                <div id="receiptPreview" class="receipt-preview" style="display: none;">
                  <img id="receiptImage" src="" alt="Receipt" />
                </div>
                <button type="button" class="btn btn-outline btn-full" id="captureReceipt">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                    <circle cx="12" cy="13" r="4"/>
                  </svg>
                  Capture Receipt
                </button>
              </div>
              <div class="modal-actions">
                <button type="submit" class="btn btn-primary btn-full">Submit Claim</button>
                <button type="button" class="btn btn-outline btn-full" id="cancelClaim">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      </div>
    `;

    this.attachListeners();
  }

  private attachListeners(): void {
    PageHeader.attachListeners({ 
      title: 'Reimbursements', 
      showBack: true,
      rightAction: { icon: '', onClick: () => this.showClaimForm() }
    });

    document.getElementById('cancelClaim')?.addEventListener('click', () => this.hideClaimForm());
    document.getElementById('claimForm')?.addEventListener('submit', (e) => this.handleSubmit(e));
    document.getElementById('captureReceipt')?.addEventListener('click', () => this.captureReceipt());
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    const totalPending = this.claims.filter(c => c.status === 'Pending').reduce((s, c) => s + c.amount, 0);
    const totalApproved = this.claims.filter(c => c.status === 'Approved').reduce((s, c) => s + (c.approved_amount || c.amount), 0);

    content.innerHTML = `
      <div class="reimbursement-summary card">
        <div class="summary-row">
          <div class="summary-item">
            <span class="summary-value">₹${totalPending.toFixed(0)}</span>
            <span class="summary-label">Pending</span>
          </div>
          <div class="summary-item">
            <span class="summary-value">₹${totalApproved.toFixed(0)}</span>
            <span class="summary-label">Approved</span>
          </div>
        </div>
      </div>

      <h3 class="section-title">Claims History</h3>
      <div class="list-container">
        ${this.claims.length === 0 ? '<div class="empty-state">No claims submitted</div>' :
          this.claims.map(claim => `
            <div class="list-item card">
              <div class="item-header">
                <span class="claim-number">${claim.claim_number || '#' + claim.id}</span>
                <span class="status-badge ${claim.status?.toLowerCase()}">${claim.status}</span>
              </div>
              <div class="claim-details">
                <span class="claim-category">${claim.category}</span>
                <span class="claim-amount">₹${claim.amount.toFixed(0)}</span>
              </div>
              <p class="claim-description">${claim.description}</p>
              <div class="claim-meta">Submitted: ${this.formatDate(claim.submitted_on)}</div>
              ${claim.approved_amount ? `<div class="approved-amount">Approved: ₹${claim.approved_amount}</div>` : ''}
            </div>
          `).join('')
        }
      </div>
    `;
  }

  private showClaimForm(): void {
    this.receiptBase64 = null;
    document.getElementById('receiptPreview')!.style.display = 'none';
    const modal = document.getElementById('claimModal');
    if (modal) modal.style.display = 'flex';
  }

  private hideClaimForm(): void {
    const modal = document.getElementById('claimModal');
    if (modal) modal.style.display = 'none';
  }

  private async captureReceipt(): Promise<void> {
    const result = await cameraService.takeDocumentPhoto();
    if (result.success && result.base64) {
      this.receiptBase64 = result.base64;
      const preview = document.getElementById('receiptPreview');
      const image = document.getElementById('receiptImage') as HTMLImageElement;
      if (preview && image) {
        image.src = `data:image/jpeg;base64,${result.base64}`;
        preview.style.display = 'block';
      }
    } else {
      alert(result.error || 'Failed to capture photo');
    }
  }

  private async handleSubmit(e: Event): Promise<void> {
    e.preventDefault();
    
    const category = (document.getElementById('category') as HTMLSelectElement).value;
    const amount = parseFloat((document.getElementById('amount') as HTMLInputElement).value);
    const description = (document.getElementById('description') as HTMLTextAreaElement).value;

    try {
      const response = await apiService.fetch('/staff/reimbursements/claims', {
        method: 'POST',
        body: JSON.stringify({ 
          category, 
          amount, 
          description,
          receipt_base64: this.receiptBase64
        })
      });

      if (response.success) {
        alert('Claim submitted successfully');
        this.hideClaimForm();
        await this.loadClaims();
      } else {
        alert(response.error || 'Failed to submit');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to submit');
    }
  }

  private formatDate(dateStr: string): string {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
  }
}
