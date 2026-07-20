/**
 * Staff Zynova Dashboard Page
 * DC Protocol: DC_MOBILE_STAFF_ZYNOVA_001
 * Zynova Real Estate & Insurance management
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import { routerService } from '../services/router.service';

interface ZynovaStats {
  real_estate: {
    active_listings: number;
    total_leads: number;
    conversions: number;
    commission_pending: number;
  };
  insurance: {
    policies_sold: number;
    renewals_due: number;
    total_premium: number;
    commission_earned: number;
  };
}

export class StaffZynovaPage {
  private container: HTMLElement;
  private stats: ZynovaStats | null = null;
  private loading: boolean = true;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadStats();
  }

  private async loadStats(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const [membershipRes, incentivesRes] = await Promise.all([
        apiService.get<any>('/myntreal/zynova/my-membership'),
        apiService.get<any>('/myntreal/my-zynova-incentives')
      ]);

      const membership = membershipRes.success ? membershipRes.data : {};
      const incentives = incentivesRes.success ? incentivesRes.data : {};

      this.stats = {
        real_estate: {
          active_listings: membership.real_estate_listings || 0,
          total_leads: incentives.real_estate_leads || 0,
          conversions: incentives.real_estate_conversions || 0,
          commission_pending: incentives.real_estate_commission_pending || 0
        },
        insurance: {
          policies_sold: incentives.insurance_policies_sold || 0,
          renewals_due: membership.insurance_renewals_due || 0,
          total_premium: incentives.insurance_total_premium || 0,
          commission_earned: incentives.insurance_commission_earned || 0
        }
      };
    } catch (error) {
      console.error('[StaffZynova] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'VGK4U', showBack: true })}
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: 'VGK4U', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    content.innerHTML = `
      <div class="zynova-hero card">
        <div class="hero-icon">🏢</div>
        <h3>VGK4U Business Suite</h3>
        <p>Real Estate & Insurance Management</p>
      </div>

      <h4 class="section-title">Real Estate</h4>
      <div class="zynova-section card" id="realEstateSection">
        <div class="section-header">
          <span class="section-icon">🏠</span>
          <h4>Real Dreams</h4>
        </div>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-value">${this.stats?.real_estate?.active_listings || 0}</span>
            <span class="stat-label">Active Listings</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">${this.stats?.real_estate?.total_leads || 0}</span>
            <span class="stat-label">Leads</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">${this.stats?.real_estate?.conversions || 0}</span>
            <span class="stat-label">Conversions</span>
          </div>
        </div>
        <button class="btn btn-secondary btn-block" data-page="staff-zynova-real-estate">
          Manage Real Estate →
        </button>
      </div>

      <h4 class="section-title">Insurance</h4>
      <div class="zynova-section card" id="insuranceSection">
        <div class="section-header">
          <span class="section-icon">🛡️</span>
          <h4>Insurance Services</h4>
        </div>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-value">${this.stats?.insurance?.policies_sold || 0}</span>
            <span class="stat-label">Policies Sold</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">${this.stats?.insurance?.renewals_due || 0}</span>
            <span class="stat-label">Renewals Due</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">₹${((this.stats?.insurance?.commission_earned || 0) / 1000).toFixed(1)}K</span>
            <span class="stat-label">Commission</span>
          </div>
        </div>
        <button class="btn btn-secondary btn-block" data-page="staff-zynova-insurance">
          Manage Insurance →
        </button>
      </div>

      <h4 class="section-title">Quick Actions</h4>
      <div class="quick-actions">
        <button class="action-card card" data-page="staff-zynova-incentives">
          <span class="action-icon">💰</span>
          <span>Incentives</span>
        </button>
        <button class="action-card card" data-page="staff-crm-dashboard">
          <span class="action-icon">👥</span>
          <span>CRM</span>
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
