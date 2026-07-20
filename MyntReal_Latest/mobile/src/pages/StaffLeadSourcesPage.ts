/**
 * Staff Lead Sources Page
 * DC Protocol: DC_MOBILE_LEAD_SOURCES_001
 * View and manage lead sources
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface LeadSource {
  id: number;
  name: string;
  code: string;
  category: string;
  description: string;
  leads_count: number;
  conversion_rate: number;
  status: string;
  created_at: string;
}

export class StaffLeadSourcesPage {
  private container: HTMLElement;
  private sources: LeadSource[] = [];
  private loading: boolean = true;
  private filterCategory: string = '';
  private categories: string[] = [];

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadSources();
  }

  private async loadSources(): Promise<void> {
    this.loading = true;
    this.updateList();

    try {
      const response = await apiService.get<any>('/crm/sources');
      console.log('[StaffLeadSourcesPage] API response:', response);

      if (response.success && response.data) {
        this.sources = response.data.sources || response.data || [];
        this.categories = [...new Set(this.sources.map(s => s.category).filter(Boolean))];
      }
    } catch (error) {
      console.error('[StaffLeadSourcesPage] Failed to load:', error);
    }

    this.loading = false;
    this.updateList();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Lead Sources', showBack: true })}
        
        <div class="filter-row">
          <select id="categoryFilter" class="filter-select full-width">
            <option value="">All Categories</option>
          </select>
        </div>

        <div class="stats-row">
          <div class="stat-card mini">
            <span class="stat-value" id="totalSources">0</span>
            <span class="stat-label">Total Sources</span>
          </div>
          <div class="stat-card mini">
            <span class="stat-value" id="totalLeads">0</span>
            <span class="stat-label">Total Leads</span>
          </div>
        </div>

        <div class="list-container" id="sourcesList">
          <div class="loading-state">Loading sources...</div>
        </div>
      </div>
    `;

    PageHeader.attachBackHandler();
    this.attachEventListeners();
  }

  private attachEventListeners(): void {
    document.getElementById('categoryFilter')?.addEventListener('change', (e) => {
      this.filterCategory = (e.target as HTMLSelectElement).value;
      this.updateList();
    });
  }

  private updateList(): void {
    const listContainer = document.getElementById('sourcesList');
    const categoryFilter = document.getElementById('categoryFilter') as HTMLSelectElement;
    
    if (categoryFilter && this.categories.length > 0) {
      categoryFilter.innerHTML = `
        <option value="">All Categories</option>
        ${this.categories.map(c => `<option value="${c}">${c}</option>`).join('')}
      `;
    }

    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state">Loading sources...</div>';
      return;
    }

    let filtered = this.sources;
    if (this.filterCategory) {
      filtered = filtered.filter(s => s.category === this.filterCategory);
    }

    const totalSourcesEl = document.getElementById('totalSources');
    const totalLeadsEl = document.getElementById('totalLeads');
    if (totalSourcesEl) totalSourcesEl.textContent = filtered.length.toString();
    if (totalLeadsEl) totalLeadsEl.textContent = filtered.reduce((sum, s) => sum + (s.leads_count || 0), 0).toString();

    if (filtered.length === 0) {
      listContainer.innerHTML = '<div class="empty-state">No lead sources found</div>';
      return;
    }

    listContainer.innerHTML = filtered.map(source => `
      <div class="list-card source-card">
        <div class="source-header">
          <div class="source-info">
            <div class="source-name">${source.name}</div>
            <div class="source-code">${source.code}</div>
          </div>
          <span class="status-badge ${source.status}">${source.status}</span>
        </div>
        <div class="source-category">${source.category || 'Uncategorized'}</div>
        ${source.description ? `<div class="source-desc">${source.description}</div>` : ''}
        <div class="source-stats">
          <div class="stat-item">
            <span class="stat-val">${source.leads_count || 0}</span>
            <span class="stat-lbl">Leads</span>
          </div>
          <div class="stat-item">
            <span class="stat-val">${source.conversion_rate?.toFixed(1) || 0}%</span>
            <span class="stat-lbl">Conversion</span>
          </div>
        </div>
      </div>
    `).join('');
  }
}
