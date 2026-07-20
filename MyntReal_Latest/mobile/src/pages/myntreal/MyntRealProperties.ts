/**
 * MyntReal Properties Page
 * DC Protocol: DC_MOBILE_MYNTREAL_PROP_001
 * Browse and refer properties
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';

interface Property {
  id: number;
  title: string;
  location: string;
  price: number;
  type: string;
  bedrooms: number;
  area_sqft: number;
  status: string;
  image_url: string | null;
}

export class MyntRealProperties {
  private container: HTMLElement;
  private properties: Property[] = [];
  private loading: boolean = true;
  private filter: string = 'all';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadProperties();
  }

  private async loadProperties(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<any>('/real-dreams/public/listings');
      if (response.success && response.data) {
        this.properties = response.data.properties || response.data || [];
      }
    } catch (error) {
      console.error('[MyntRealProperties] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container myntreal-page">
        ${PageHeader.render({ title: 'Properties', showBack: true })}
        
        <div class="filter-tabs">
          <button class="tab ${this.filter === 'all' ? 'active' : ''}" data-filter="all">All</button>
          <button class="tab ${this.filter === 'residential' ? 'active' : ''}" data-filter="residential">Residential</button>
          <button class="tab ${this.filter === 'commercial' ? 'active' : ''}" data-filter="commercial">Commercial</button>
          <button class="tab ${this.filter === 'plots' ? 'active' : ''}" data-filter="plots">Plots</button>
        </div>

        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;

    this.attachListeners();
  }

  private attachListeners(): void {
    PageHeader.attachListeners({ title: 'Properties', showBack: true });

    this.container.querySelectorAll('.filter-tabs .tab').forEach(btn => {
      btn.addEventListener('click', () => {
        this.filter = btn.getAttribute('data-filter') || 'all';
        this.render();
        this.updateContent();
      });
    });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading properties...</div>';
      return;
    }

    const filtered = this.getFilteredProperties();

    if (filtered.length === 0) {
      content.innerHTML = `
        <div class="empty-state card">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
            <polyline points="9 22 9 12 15 12 15 22"/>
          </svg>
          <h3>No Properties Found</h3>
          <p>Check back later for new listings</p>
        </div>
      `;
      return;
    }

    content.innerHTML = `
      <div class="properties-grid">
        ${filtered.map(p => `
          <div class="property-card card" data-id="${p.id}">
            <div class="property-image">
              ${p.image_url ? `<img src="${p.image_url}" alt="${p.title}">` : '<div class="no-image">🏠</div>'}
              <span class="property-type-badge">${p.type}</span>
            </div>
            <div class="property-info">
              <h4 class="property-title">${p.title}</h4>
              <p class="property-location">📍 ${p.location}</p>
              <div class="property-meta">
                ${p.bedrooms ? `<span>🛏️ ${p.bedrooms} BHK</span>` : ''}
                ${p.area_sqft ? `<span>📐 ${p.area_sqft} sqft</span>` : ''}
              </div>
              <div class="property-price">₹${this.formatPrice(p.price)}</div>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  private getFilteredProperties(): Property[] {
    if (this.filter === 'all') return this.properties;
    return this.properties.filter(p => 
      p.type?.toLowerCase().includes(this.filter.toLowerCase())
    );
  }

  private formatPrice(price: number): string {
    if (price >= 10000000) return (price / 10000000).toFixed(2) + ' Cr';
    if (price >= 100000) return (price / 100000).toFixed(2) + ' L';
    return price.toLocaleString();
  }
}
