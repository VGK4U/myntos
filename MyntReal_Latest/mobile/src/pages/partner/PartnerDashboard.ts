/**
 * Partner Dashboard Page
 * DC Protocol: DC_MOBILE_PARTNER_DASHBOARD_002
 * Main dashboard for Partners with sidebar menu and professional header
 */

import { apiService } from '../../services/api.service';
import { authService } from '../../services/auth.service';
import { routerService } from '../../services/router.service';
import { partnerSideDrawer } from '../../components/PartnerSideDrawer';

interface PartnerDashboardData {
  total_orders: number;
  pending_orders: number;
  completed_orders: number;
  total_revenue: number;
  pending_payments: number;
  total_leads: number;
  open_tickets: number;
}

export class PartnerDashboard {
  private container: HTMLElement;
  private user: any = null;
  private data: PartnerDashboardData | null = null;
  private loading: boolean = true;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    const authState = authService.getAuthState();
    this.user = authState.user;
    partnerSideDrawer.setUser(this.user);
    this.render();
    await this.loadDashboard();
  }

  private async loadDashboard(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<PartnerDashboardData>('/partner/dashboard/stats');
      if (response.success && response.data) {
        this.data = response.data;
      }
    } catch (error) {
      console.error('[PartnerDashboard] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    const username = this.user?.name || this.user?.partner_name || 'Partner';
    const partnerCode = this.user?.partner_code || this.user?.partner_id || 'PARTNER';
    const partnerType = this.user?.partner_type || this.user?.type || 'Official Partner';
    const initials = username.split(' ').map((n: string) => n[0]).join('').toUpperCase().slice(0, 2);

    this.container.innerHTML = `
      <style>
        .partner-page { background: linear-gradient(135deg, #0a1929 0%, #0d2137 100%); min-height: 100vh; }
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
        .partner-hamburger:active { background: rgba(255, 255, 255, 0.25); }
        .partner-header-info { flex: 1; display: flex; align-items: center; gap: 12px; }
        .partner-header-avatar {
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
          border: 2px solid rgba(255, 255, 255, 0.3);
        }
        .partner-header-text { display: flex; flex-direction: column; }
        .partner-header-name { font-size: 16px; font-weight: 600; color: white; }
        .partner-header-code {
          font-size: 11px;
          color: rgba(255, 255, 255, 0.9);
          background: rgba(255, 255, 255, 0.15);
          padding: 2px 8px;
          border-radius: 4px;
          margin-top: 2px;
          display: inline-block;
        }
        .partner-header-type { font-size: 10px; color: rgba(255, 255, 255, 0.7); margin-top: 2px; }
        .partner-logout-btn {
          background: rgba(255, 255, 255, 0.15);
          border: none;
          border-radius: 8px;
          padding: 10px;
          color: white;
          cursor: pointer;
        }
        .partner-content { padding: 16px; }
        .partner-service-banner {
          background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
          color: white;
          display: flex;
          align-items: center;
          gap: 12px;
          cursor: pointer;
        }
        .partner-service-banner:active { opacity: 0.9; }
        .partner-service-icon {
          width: 48px;
          height: 48px;
          border-radius: 12px;
          background: rgba(255, 255, 255, 0.2);
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .partner-service-text { flex: 1; }
        .partner-service-text h3 { margin: 0 0 4px; font-size: 16px; }
        .partner-service-text p { margin: 0; font-size: 12px; opacity: 0.9; }
        .partner-revenue-card {
          background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
          border-radius: 12px;
          padding: 20px;
          margin-bottom: 16px;
          border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .partner-revenue-row { display: flex; justify-content: space-between; align-items: center; }
        .partner-revenue-label { font-size: 12px; color: #9ca3af; margin-bottom: 4px; }
        .partner-revenue-amount { font-size: 28px; font-weight: 700; color: #10b981; }
        .partner-revenue-pending { font-size: 13px; color: #fbbf24; }
        .partner-stats-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 12px;
          margin-bottom: 16px;
        }
        .partner-stat-card {
          background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
          border-radius: 12px;
          padding: 16px;
          text-align: center;
          border: 1px solid rgba(255, 255, 255, 0.1);
          cursor: pointer;
        }
        .partner-stat-card:active { opacity: 0.9; }
        .partner-stat-value { font-size: 32px; font-weight: 700; color: #10b981; }
        .partner-stat-label { font-size: 12px; color: #9ca3af; margin-top: 4px; }
        .partner-quick-title { font-size: 14px; font-weight: 600; color: #e0e0e0; margin: 0 0 12px; }
        .partner-quick-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 10px;
          margin-bottom: 16px;
        }
        .partner-quick-btn {
          background: #1f2937;
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 10px;
          padding: 14px;
          display: flex;
          align-items: center;
          gap: 10px;
          color: #e0e0e0;
          font-size: 13px;
          cursor: pointer;
        }
        .partner-quick-btn:active { background: #374151; }
        .partner-quick-btn svg { color: #64b5f6; }
        .partner-menu-list { display: flex; flex-direction: column; gap: 8px; }
        .partner-menu-item {
          background: #1f2937;
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 10px;
          padding: 14px 16px;
          display: flex;
          align-items: center;
          gap: 12px;
          color: #e0e0e0;
          font-size: 14px;
          cursor: pointer;
        }
        .partner-menu-item:active { background: #374151; }
        .partner-menu-item svg { color: #64b5f6; }
        .partner-menu-item .chevron { margin-left: auto; color: #6b7280; }
        .loading-state { text-align: center; padding: 40px; color: #8892b0; }
      </style>

      <div class="partner-page">
        <header class="partner-header">
          <button class="partner-hamburger" id="partnerHamburgerBtn">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
          </button>
          <div class="partner-header-info">
            <div class="partner-header-avatar">${initials}</div>
            <div class="partner-header-text">
              <span class="partner-header-name">${username}</span>
              <span class="partner-header-code">${partnerCode}</span>
              <span class="partner-header-type">${partnerType}</span>
            </div>
          </div>
          <button class="partner-logout-btn" id="partnerLogoutBtn">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
          </button>
        </header>

        <div class="partner-content" id="dashboardContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;

    this.attachListeners();
  }

  private attachListeners(): void {
    document.getElementById('partnerHamburgerBtn')?.addEventListener('click', () => {
      partnerSideDrawer.open();
    });

    document.getElementById('partnerLogoutBtn')?.addEventListener('click', async () => {
      if (confirm('Are you sure you want to logout?')) {
        await authService.logout();
        window.dispatchEvent(new CustomEvent('logout'));
      }
    });
  }

  private updateContent(): void {
    const content = document.getElementById('dashboardContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    const d = this.data || { total_orders: 0, pending_orders: 0, completed_orders: 0, total_revenue: 0, pending_payments: 0, total_leads: 0, open_tickets: 0 };

    content.innerHTML = `
      <div class="partner-service-banner" data-page="partner-service">
        <div class="partner-service-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
            <path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"/>
          </svg>
        </div>
        <div class="partner-service-text">
          <h3>Service Request</h3>
          <p>Raise a new ticket or view existing requests</p>
        </div>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      </div>

      <div class="partner-revenue-card">
        <div class="partner-revenue-row">
          <div>
            <div class="partner-revenue-label">Total Revenue</div>
            <div class="partner-revenue-amount">₹${d.total_revenue.toLocaleString()}</div>
          </div>
          <div style="text-align: right;">
            <div class="partner-revenue-pending">Pending: ₹${d.pending_payments.toLocaleString()}</div>
          </div>
        </div>
      </div>

      <div class="partner-stats-grid">
        <div class="partner-stat-card" data-page="partner-orders">
          <div class="partner-stat-value">${d.total_orders}</div>
          <div class="partner-stat-label">Total Orders</div>
        </div>
        <div class="partner-stat-card" data-page="partner-orders">
          <div class="partner-stat-value">${d.pending_orders}</div>
          <div class="partner-stat-label">Pending</div>
        </div>
        <div class="partner-stat-card" data-page="partner-orders">
          <div class="partner-stat-value">${d.completed_orders}</div>
          <div class="partner-stat-label">Completed</div>
        </div>
        <div class="partner-stat-card" data-page="partner-leads">
          <div class="partner-stat-value">${d.total_leads}</div>
          <div class="partner-stat-label">Leads</div>
        </div>
      </div>

      <h4 class="partner-quick-title">Quick Actions</h4>
      <div class="partner-quick-grid">
        <button class="partner-quick-btn" data-page="partner-orders">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
          </svg>
          Orders
        </button>
        <button class="partner-quick-btn" data-page="partner-invoices">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
          </svg>
          Invoices
        </button>
        <button class="partner-quick-btn" data-page="partner-payments">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
          </svg>
          Payments
        </button>
        <button class="partner-quick-btn" data-page="partner-leads">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
          </svg>
          Leads
        </button>
      </div>

      <div class="partner-menu-list">
        <button class="partner-menu-item" data-page="partner-raise-ticket">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>
          </svg>
          <span>Raise New Ticket</span>
          <svg class="chevron" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"/>
          </svg>
        </button>
        <button class="partner-menu-item" data-page="partner-revenue">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>
          </svg>
          <span>Revenue Dashboard</span>
          <svg class="chevron" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"/>
          </svg>
        </button>
        <button class="partner-menu-item" data-page="partner-kyc-documents">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
          </svg>
          <span>KYC &amp; Documents</span>
          <svg class="chevron" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"/>
          </svg>
        </button>
        <button class="partner-menu-item" data-page="partner-profile">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
          </svg>
          <span>My Profile</span>
          <svg class="chevron" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"/>
          </svg>
        </button>
      </div>
    `;

    content.querySelectorAll('[data-page]').forEach(btn => {
      btn.addEventListener('click', () => {
        const page = btn.getAttribute('data-page');
        if (page) routerService.navigate(page as any);
      });
    });
  }
}
