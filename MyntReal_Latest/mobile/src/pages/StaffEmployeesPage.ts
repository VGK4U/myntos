/**
 * Staff Employees Page
 * DC Protocol: DC_MOBILE_STAFF_EMPLOYEES_001
 * View and manage employee list
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface Employee {
  id: number;
  emp_code: string;
  name: string;
  email: string;
  phone: string;
  department: string;
  designation: string;
  status: string;
  joining_date: string;
  photo_url?: string;
}

export class StaffEmployeesPage {
  private container: HTMLElement;
  private employees: Employee[] = [];
  private loading: boolean = true;
  private searchQuery: string = '';
  private filterDepartment: string = '';
  private departments: string[] = [];

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadEmployees();
  }

  private async loadEmployees(): Promise<void> {
    this.loading = true;
    this.updateList();

    try {
      const response = await apiService.get<any>('/staff/employees');
      console.log('[StaffEmployeesPage] API response:', response);

      if (response.success && response.data) {
        this.employees = response.data.employees || response.data || [];
        this.departments = [...new Set(this.employees.map(e => e.department).filter(Boolean))];
      }
    } catch (error) {
      console.error('[StaffEmployeesPage] Failed to load:', error);
    }

    this.loading = false;
    this.updateList();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Employees', showBack: true })}
        
        <div class="search-filter-bar">
          <div class="search-box">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/>
              <path d="m21 21-4.35-4.35"/>
            </svg>
            <input type="text" id="searchInput" placeholder="Search employees..." class="search-input">
          </div>
          <select id="deptFilter" class="filter-select">
            <option value="">All Departments</option>
          </select>
        </div>

        <div class="stats-row">
          <div class="stat-card mini">
            <span class="stat-value" id="totalCount">0</span>
            <span class="stat-label">Total</span>
          </div>
          <div class="stat-card mini">
            <span class="stat-value" id="activeCount">0</span>
            <span class="stat-label">Active</span>
          </div>
        </div>

        <div class="list-container" id="employeesList">
          <div class="loading-state">Loading employees...</div>
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

    document.getElementById('deptFilter')?.addEventListener('change', (e) => {
      this.filterDepartment = (e.target as HTMLSelectElement).value;
      this.updateList();
    });
  }

  private updateList(): void {
    const listContainer = document.getElementById('employeesList');
    const deptFilter = document.getElementById('deptFilter') as HTMLSelectElement;
    
    if (deptFilter && this.departments.length > 0) {
      deptFilter.innerHTML = `
        <option value="">All Departments</option>
        ${this.departments.map(d => `<option value="${d}">${d}</option>`).join('')}
      `;
    }

    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state">Loading employees...</div>';
      return;
    }

    let filtered = this.employees;
    if (this.searchQuery) {
      filtered = filtered.filter(e => 
        e.name?.toLowerCase().includes(this.searchQuery) ||
        e.emp_code?.toLowerCase().includes(this.searchQuery) ||
        e.email?.toLowerCase().includes(this.searchQuery)
      );
    }
    if (this.filterDepartment) {
      filtered = filtered.filter(e => e.department === this.filterDepartment);
    }

    const totalEl = document.getElementById('totalCount');
    const activeEl = document.getElementById('activeCount');
    if (totalEl) totalEl.textContent = this.employees.length.toString();
    if (activeEl) activeEl.textContent = this.employees.filter(e => e.status === 'active').length.toString();

    if (filtered.length === 0) {
      listContainer.innerHTML = '<div class="empty-state">No employees found</div>';
      return;
    }

    listContainer.innerHTML = filtered.map(emp => `
      <div class="list-card employee-card">
        <div class="employee-avatar">
          ${emp.photo_url ? `<img src="${emp.photo_url}" alt="${emp.name}">` : this.getInitials(emp.name)}
        </div>
        <div class="employee-info">
          <div class="employee-name">${emp.name}</div>
          <div class="employee-code">${emp.emp_code}</div>
          <div class="employee-dept">${emp.department || 'N/A'} • ${emp.designation || 'N/A'}</div>
        </div>
        <div class="employee-status ${emp.status}">${emp.status || 'active'}</div>
      </div>
    `).join('');
  }

  private getInitials(name: string): string {
    return name?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || '??';
  }
}
