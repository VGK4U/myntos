/**
 * Staff Directory Page
 * DC Protocol: DC_MOBILE_STAFF_DIRECTORY_001
 * Employee directory with contact info
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface DirectoryEntry {
  id: number;
  emp_code: string;
  name: string;
  email: string;
  phone: string;
  department: string;
  designation: string;
  photo_url?: string;
  extension?: string;
}

export class StaffDirectoryPage {
  private container: HTMLElement;
  private entries: DirectoryEntry[] = [];
  private loading: boolean = true;
  private searchQuery: string = '';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadDirectory();
  }

  private async loadDirectory(): Promise<void> {
    this.loading = true;
    this.updateList();

    try {
      const response = await apiService.get<any>('/staff/employees/directory');
      console.log('[StaffDirectoryPage] API response:', response);

      if (response.success && response.data) {
        this.entries = response.data.employees || response.data || [];
      }
    } catch (error) {
      console.error('[StaffDirectoryPage] Failed to load:', error);
    }

    this.loading = false;
    this.updateList();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Employee Directory', showBack: true })}
        
        <div class="search-box">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/>
            <path d="m21 21-4.35-4.35"/>
          </svg>
          <input type="text" id="searchInput" placeholder="Search by name, email, phone..." class="search-input">
        </div>

        <div class="list-container" id="directoryList">
          <div class="loading-state">Loading directory...</div>
        </div>
      </div>
    `;

    PageHeader.attachBackHandler();
    this.attachEventListeners();
  }

  private attachEventListeners(): void {
    document.getElementById('searchInput')?.addEventListener('input', (e) => {
      this.searchQuery = (e.target as HTMLInputElement).value.toLowerCase();
      this.updateList();
    });
  }

  private updateList(): void {
    const listContainer = document.getElementById('directoryList');
    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state">Loading directory...</div>';
      return;
    }

    let filtered = this.entries;
    if (this.searchQuery) {
      filtered = filtered.filter(e => 
        e.name?.toLowerCase().includes(this.searchQuery) ||
        e.email?.toLowerCase().includes(this.searchQuery) ||
        e.phone?.includes(this.searchQuery) ||
        e.department?.toLowerCase().includes(this.searchQuery)
      );
    }

    if (filtered.length === 0) {
      listContainer.innerHTML = '<div class="empty-state">No contacts found</div>';
      return;
    }

    listContainer.innerHTML = filtered.map(entry => `
      <div class="list-card contact-card">
        <div class="contact-avatar">
          ${entry.photo_url ? `<img src="${entry.photo_url}" alt="${entry.name}">` : this.getInitials(entry.name)}
        </div>
        <div class="contact-info">
          <div class="contact-name">${entry.name}</div>
          <div class="contact-role">${entry.designation || 'Employee'} • ${entry.department || 'N/A'}</div>
          <div class="contact-actions">
            ${entry.phone ? `<a href="tel:${entry.phone}" class="action-btn"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72"/></svg></a>` : ''}
            ${entry.email ? `<a href="mailto:${entry.email}" class="action-btn"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg></a>` : ''}
          </div>
        </div>
      </div>
    `).join('');
  }

  private getInitials(name: string): string {
    return name?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || '??';
  }
}
