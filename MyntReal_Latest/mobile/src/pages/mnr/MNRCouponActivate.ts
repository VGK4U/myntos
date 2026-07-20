/**
 * MNR Coupon Activate Page
 * DC Protocol: DC_MOBILE_MNR_COUPON_ACTIVATE_001
 * Activate PINs for self or other members
 * Fixed: Jan 2026 - Correct endpoint /users/pins and /users/pins/activate
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';

interface Pin {
  id: string;
  coupon_code: string;
  coupon_type: string;
  status: string;
  amount: number;
  created_at: string;
}

export class MNRCouponActivate {
  private container: HTMLElement;
  private activePins: Pin[] = [];
  private loading: boolean = true;
  private selectedPin: string | null = null;
  private targetUserId: string = '';
  private targetUserName: string = '';
  private searchResults: any[] = [];
  private isSearching: boolean = false;
  private searchQuery: string = '';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadActivePins();
  }

  private async loadActivePins(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<any>('/users/pins');
      if (response.success && response.data) {
        const allPins = response.data.pins || [];
        this.activePins = allPins.filter((p: Pin) => p.status === 'Active');
      }
    } catch (error) {
      console.error('[MNRCouponActivate] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <style>
        .search-input-container { position: relative; }
        .search-spinner {
          position: absolute; right: 12px; top: 50%; transform: translateY(-50%);
          width: 16px; height: 16px; border: 2px solid #8892b0;
          border-top-color: #64ffda; border-radius: 50%; animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: translateY(-50%) rotate(360deg); } }
        .selected-user {
          display: flex; align-items: center; justify-content: space-between;
          background: rgba(100, 255, 218, 0.1); border: 1px solid rgba(100, 255, 218, 0.3);
          border-radius: 8px; padding: 12px 16px; margin-top: 12px;
        }
        .selected-user-info { display: flex; flex-direction: column; gap: 4px; }
        .selected-user-id { color: #64ffda; font-weight: 600; font-size: 14px; }
        .selected-user-name { color: #e6f1ff; font-size: 15px; font-weight: 500; }
        .clear-selection {
          background: rgba(255,100,100,0.2); border: none; color: #ff6b6b;
          width: 28px; height: 28px; border-radius: 50%; cursor: pointer;
          font-size: 14px; display: flex; align-items: center; justify-content: center;
        }
        .search-results {
          background: #1a2744; border: 1px solid #2d3b4f; border-radius: 8px;
          margin-top: 8px; max-height: 200px; overflow-y: auto;
        }
        .search-result-item {
          display: flex; flex-direction: column; gap: 2px;
          padding: 12px 16px; border-bottom: 1px solid #2d3b4f; cursor: pointer;
        }
        .search-result-item:last-child { border-bottom: none; }
        .search-result-item:active { background: rgba(100, 255, 218, 0.1); }
        .search-result-item .user-id { color: #64ffda; font-size: 13px; font-weight: 600; }
        .search-result-item .user-name { color: #e6f1ff; font-size: 14px; }
      </style>
      <div class="page-container">
        ${PageHeader.render({ title: '✅ Activate Coupon', showBack: true })}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: '✅ Activate Coupon', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    if (this.activePins.length === 0) {
      content.innerHTML = `
        <div class="empty-state card">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
          </svg>
          <h3>No Coupons to Activate</h3>
          <p>Purchase a coupon first to activate it</p>
        </div>
      `;
      return;
    }

    content.innerHTML = `
      <div class="activate-card card">
        <div class="card-header">Activate PIN/Coupon</div>
        
        <div class="info-box">
          <h4>How to Activate:</h4>
          <ul>
            <li>Select an available PIN from your inventory</li>
            <li>Search and select the user/member who will use this PIN</li>
            <li>Activation will upgrade the member's package</li>
          </ul>
        </div>

        <div class="form-group">
          <label>Select PIN Code</label>
          <select id="pinSelect" class="form-select">
            <option value="">-- Select a PIN --</option>
            ${this.activePins.map(pin => `
              <option value="${pin.id}" ${this.selectedPin === pin.id ? 'selected' : ''}>
                ${pin.coupon_code} - ${pin.coupon_type} Package
              </option>
            `).join('')}
          </select>
          <small>Select from your available/unused PINs</small>
        </div>

        <div class="form-group">
          <label>Activate For (User ID)</label>
          <div class="search-input-container">
            <input type="text" id="userIdInput" class="form-input" 
              placeholder="Search by MNR ID or Name..."
              value="${this.searchQuery}" />
            ${this.isSearching ? '<div class="search-spinner"></div>' : ''}
          </div>
          <small>Leave blank to activate for yourself. Type to search inactive users.</small>
          
          ${this.targetUserId && this.targetUserName ? `
            <div class="selected-user">
              <div class="selected-user-info">
                <span class="selected-user-id">${this.targetUserId}</span>
                <span class="selected-user-name">${this.targetUserName}</span>
              </div>
              <button class="clear-selection" id="clearUserBtn">✕</button>
            </div>
          ` : ''}
          
          ${this.searchResults.length > 0 && !this.targetUserId ? `
            <div class="search-results">
              ${this.searchResults.map(user => `
                <div class="search-result-item" data-user-id="${user.id}" data-user-name="${user.name || user.full_name || 'Unknown'}">
                  <span class="user-id">${user.id}</span>
                  <span class="user-name">${user.name || user.full_name || 'Unknown'}</span>
                </div>
              `).join('')}
            </div>
          ` : ''}
        </div>

        <button class="btn-primary activate-btn" id="activateBtn" ${!this.selectedPin ? 'disabled' : ''}>
          Activate PIN
        </button>
      </div>
    `;

    this.attachListeners();
  }

  private attachListeners(): void {
    document.getElementById('pinSelect')?.addEventListener('change', (e) => {
      const select = e.target as HTMLSelectElement;
      this.selectedPin = select.value || null;
      this.updateContent();
    });

    const userInput = document.getElementById('userIdInput') as HTMLInputElement;
    let searchTimeout: any;
    userInput?.addEventListener('input', (e) => {
      const input = e.target as HTMLInputElement;
      this.searchQuery = input.value;
      
      if (!this.targetUserId) {
        clearTimeout(searchTimeout);
        if (input.value.length >= 2) {
          searchTimeout = setTimeout(() => this.searchUsers(input.value), 400);
        } else {
          this.searchResults = [];
          this.updateContent();
        }
      }
    });

    document.getElementById('clearUserBtn')?.addEventListener('click', () => {
      this.targetUserId = '';
      this.targetUserName = '';
      this.searchQuery = '';
      this.searchResults = [];
      this.updateContent();
    });

    document.querySelectorAll('.search-result-item').forEach(item => {
      item.addEventListener('click', () => {
        const userId = item.getAttribute('data-user-id');
        const userName = item.getAttribute('data-user-name');
        if (userId) {
          this.targetUserId = userId;
          this.targetUserName = userName || 'Unknown';
          this.searchQuery = '';
          this.searchResults = [];
          this.updateContent();
        }
      });
    });

    document.getElementById('activateBtn')?.addEventListener('click', () => {
      this.handleActivate();
    });
  }

  private async searchUsers(query: string): Promise<void> {
    if (this.isSearching) return;
    this.isSearching = true;

    try {
      const response = await apiService.get<any>(`/team/search-inactive?q=${encodeURIComponent(query)}`);
      if (response.success && response.data) {
        this.searchResults = response.data.users || response.data || [];
        this.updateContent();
      }
    } catch (error) {
      console.error('[MNRCouponActivate] Search failed:', error);
    }

    this.isSearching = false;
  }

  private async handleActivate(): Promise<void> {
    if (!this.selectedPin) {
      alert('Please select a PIN to activate');
      return;
    }

    const confirmMsg = this.targetUserId 
      ? `Activate PIN for ${this.targetUserName} (${this.targetUserId})?`
      : 'Activate PIN for yourself?';
    
    if (!confirm(confirmMsg)) return;

    try {
      const response = await apiService.post<any>('/users/pins/activate', {
        pin_code: this.selectedPin,
        user_id: this.targetUserId || null
      });

      if (response.success) {
        alert('PIN activated successfully!');
        this.selectedPin = null;
        this.targetUserId = '';
        await this.loadActivePins();
      } else {
        alert(response.error || 'Failed to activate PIN');
      }
    } catch (error) {
      console.error('[MNRCouponActivate] Activation failed:', error);
      alert('Failed to activate PIN. Please try again.');
    }
  }
}
