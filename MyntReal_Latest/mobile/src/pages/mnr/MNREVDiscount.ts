/**
 * MNR Business Access - EV Discount Page
 * DC Protocol: DC_MOBILE_MNR_EV_001
 * View available EV models and purchase discounts
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';

interface EVModel {
  id: number;
  name: string;
  model: string;
  price: number;
  discount: number;
  image_url: string | null;
  features: string[];
  available: boolean;
}

interface EVStats {
  available_discount: number;
  used_discount: number;
  pending_redemptions: number;
}

export class MNREVDiscount {
  private container: HTMLElement;
  private evModels: EVModel[] = [];
  private stats: EVStats | null = null;
  private loading: boolean = true;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadData();
  }

  private async loadData(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const [modelsRes, statsRes] = await Promise.all([
        apiService.get<any>('/ev-discount/ev-models'),
        apiService.get<any>('/ev-discount/my-stats')
      ]);

      if (modelsRes.success && modelsRes.data) {
        this.evModels = modelsRes.data || [];
      }

      if (statsRes.success && statsRes.data) {
        this.stats = {
          available_discount: statsRes.data.available_discount || 0,
          used_discount: statsRes.data.used_discount || 0,
          pending_redemptions: statsRes.data.pending_redemptions || 0
        };
      }
    } catch (error) {
      console.error('[MNREVDiscount] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'EV Purchase Discount', showBack: true })}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: 'EV Purchase Discount', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    content.innerHTML = `
      <div class="ev-hero card">
        <div class="hero-icon">🛵</div>
        <h3>MNR Business Access Program</h3>
        <p>Get up to ₹13,100 discount on EV purchases</p>
      </div>

      <div class="stats-grid">
        <div class="stat-card card">
          <div class="stat-value">₹${(this.stats?.available_discount || 0).toLocaleString()}</div>
          <div class="stat-label">Available Discount</div>
        </div>
        <div class="stat-card card">
          <div class="stat-value">${this.stats?.pending_redemptions || 0}</div>
          <div class="stat-label">Pending</div>
        </div>
      </div>

      <h4 class="section-title">Available EV Models</h4>
      ${this.evModels.length > 0 ? `
        <div class="ev-models-list">
          ${this.evModels.map(model => this.renderEVModel(model)).join('')}
        </div>
      ` : `
        <div class="empty-state card">
          <div class="empty-icon">🛵</div>
          <p>No EV models available currently</p>
        </div>
      `}

      <div class="notice-card card info">
        <h4>📋 How to Avail</h4>
        <ul>
          <li>Select your preferred EV model</li>
          <li>Visit authorized dealer with MNR ID</li>
          <li>Submit purchase request for approval</li>
          <li>Discount applied at delivery</li>
        </ul>
      </div>

      <div class="notice-card card warning">
        <h4>⚠️ Terms & Conditions</h4>
        <ul>
          <li>Discount valid for activated members only</li>
          <li>One discount per member per category</li>
          <li>Subject to availability and eligibility</li>
          <li>Dealer verification required</li>
        </ul>
      </div>
    `;
  }

  private renderEVModel(model: EVModel): string {
    return `
      <div class="ev-model-card card ${!model.available ? 'unavailable' : ''}">
        <div class="model-image">
          ${model.image_url ? `<img src="${model.image_url}" alt="${model.name}">` : '🛵'}
        </div>
        <div class="model-info">
          <h4>${model.name}</h4>
          <p class="model-name">${model.model || ''}</p>
          <div class="model-pricing">
            <span class="original-price">₹${model.price.toLocaleString()}</span>
            <span class="discount-badge">-₹${model.discount.toLocaleString()}</span>
          </div>
          <div class="final-price">₹${(model.price - model.discount).toLocaleString()}</div>
        </div>
        ${model.available ? `
          <button class="btn btn-primary" onclick="alert('Please visit web portal or contact support to initiate purchase')">
            Enquire
          </button>
        ` : `
          <span class="unavailable-badge">Not Available</span>
        `}
      </div>
    `;
  }
}
