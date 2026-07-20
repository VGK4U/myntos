/**
 * Staff Timesheet Approval Page
 * DC Protocol: DC_MOBILE_TIMESHEET_APPROVAL_001
 * Approve/reject timesheet submissions
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface TimesheetEntry {
  id: number;
  employee_id: number;
  employee_name: string;
  employee_code?: string; // Backend returns employee_code, not emp_code
  emp_code?: string; // Keep for backwards compatibility
  department?: string;
  date: string;
  duration_minutes?: number;
  hours?: number;
  comments?: string; // Backend uses 'comments' not 'work_description'
  work_description?: string;
  project_name?: string;
  task_title?: string; // Backend returns task_title
  task_name?: string;
  kra_title?: string; // Backend returns kra_title
  kra_name?: string;
  lead_name?: string;
  status: string;
  entry_type?: string;
  created_at?: string;
}

export class StaffTimesheetApprovalPage {
  private container: HTMLElement;
  private entries: TimesheetEntry[] = [];
  private filteredEntries: TimesheetEntry[] = [];
  private loading: boolean = true;
  private filterStatus: string = 'submitted'; // DC Protocol: Backend uses 'submitted' not 'pending'
  private searchQuery: string = '';
  private selectedEntry: TimesheetEntry | null = null;
  private dateFrom: string = '';
  private dateTo: string = '';

  constructor(container: HTMLElement) {
    this.container = container;
    // Default: last 30 days
    const now = new Date();
    this.dateTo = now.toISOString().split('T')[0];
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    this.dateFrom = thirtyDaysAgo.toISOString().split('T')[0];
  }

  async init(): Promise<void> {
    this.render();
    await this.loadEntries();
  }

  private async loadEntries(): Promise<void> {
    this.loading = true;
    this.updateList();

    try {
      // DC Protocol: Use server-side filtering for better performance
      const params = new URLSearchParams();
      if (this.dateFrom) params.append('from_date', this.dateFrom);
      if (this.dateTo) params.append('to_date', this.dateTo);
      params.append('limit', '100');
      
      const endpoint = `/staff/timesheet/team-entries?${params.toString()}`;
      console.log('[StaffTimesheetApprovalPage] Fetching:', endpoint);
      const response = await apiService.get<any>(endpoint);
      console.log('[StaffTimesheetApprovalPage] API response:', response);

      if (response.success !== false && response.data) {
        this.entries = response.data.entries || response.data || [];
      }
    } catch (error) {
      console.error('[StaffTimesheetApprovalPage] Failed to load:', error);
    }

    this.loading = false;
    this.applyFilters();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Timesheet Approval', showBack: true })}
        
        <!-- Employee Search -->
        <div class="search-bar">
          <input type="text" id="searchInput" class="search-input" placeholder="Search by name or employee code..." value="${this.searchQuery}">
        </div>
        
        <!-- Date Range Filter -->
        <div class="date-filter-row">
          <div class="date-input-group">
            <label>From</label>
            <input type="date" id="dateFrom" class="form-input" value="${this.dateFrom}">
          </div>
          <div class="date-input-group">
            <label>To</label>
            <input type="date" id="dateTo" class="form-input" value="${this.dateTo}">
          </div>
          <button class="btn btn-sm btn-primary" id="applyDateFilter">Apply</button>
        </div>

        <!-- Status Filter Tabs -->
        <div class="filter-tabs">
          <button class="filter-tab ${this.filterStatus === 'all' ? 'active' : ''}" data-status="all">All</button>
          <button class="filter-tab ${this.filterStatus === 'submitted' ? 'active' : ''}" data-status="submitted">Pending</button>
          <button class="filter-tab ${this.filterStatus === 'approved' ? 'active' : ''}" data-status="approved">Approved</button>
          <button class="filter-tab ${this.filterStatus === 'rejected' ? 'active' : ''}" data-status="rejected">Rejected</button>
        </div>

        <div class="stats-row">
          <div class="stat-card mini pending">
            <span class="stat-value" id="pendingCount">0</span>
            <span class="stat-label">Pending</span>
          </div>
          <div class="stat-card mini">
            <span class="stat-value" id="approvedCount">0</span>
            <span class="stat-label">Approved</span>
          </div>
          <div class="stat-card mini">
            <span class="stat-value" id="totalHours">0</span>
            <span class="stat-label">Hours</span>
          </div>
        </div>

        <div class="list-container" id="submissionsList">
          <div class="loading-state">Loading submissions...</div>
        </div>
      </div>

      <div class="modal-overlay" id="approvalModal" style="display: none;">
        <div class="modal-content modal-lg">
          <div class="modal-header">
            <h4 id="modalTitle">Timesheet Details</h4>
            <button class="modal-close" id="closeModal">&times;</button>
          </div>
          <div class="modal-body" id="modalBody"></div>
          <div class="modal-footer" id="modalFooter"></div>
        </div>
      </div>
    `;

    PageHeader.attachBackHandler();
    this.attachEventListeners();
  }

  private attachEventListeners(): void {
    // Status filter tabs
    this.container.querySelectorAll('.filter-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        this.filterStatus = (tab as HTMLElement).dataset.status || 'submitted';
        this.container.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        this.applyFilters();
      });
    });

    // Employee search
    const searchInput = document.getElementById('searchInput') as HTMLInputElement;
    if (searchInput) {
      searchInput.addEventListener('input', () => {
        this.searchQuery = searchInput.value.toLowerCase();
        this.applyFilters();
      });
    }
    
    // Date range filter
    document.getElementById('applyDateFilter')?.addEventListener('click', () => {
      const fromInput = document.getElementById('dateFrom') as HTMLInputElement;
      const toInput = document.getElementById('dateTo') as HTMLInputElement;
      if (fromInput) this.dateFrom = fromInput.value;
      if (toInput) this.dateTo = toInput.value;
      this.loadEntries(); // Reload with new date range
    });

    document.getElementById('closeModal')?.addEventListener('click', () => this.hideModal());
  }

  private applyFilters(): void {
    this.filteredEntries = this.entries.filter(entry => {
      const matchesStatus = this.filterStatus === 'all' || entry.status === this.filterStatus;
      const empCode = entry.employee_code || entry.emp_code || '';
      const matchesSearch = !this.searchQuery || 
        entry.employee_name?.toLowerCase().includes(this.searchQuery) ||
        empCode.toLowerCase().includes(this.searchQuery) ||
        entry.department?.toLowerCase().includes(this.searchQuery);
      return matchesStatus && matchesSearch;
    });
    this.updateList();
  }

  private updateList(): void {
    const listContainer = document.getElementById('submissionsList');
    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state">Loading entries...</div>';
      return;
    }

    const pendingEl = document.getElementById('pendingCount');
    const approvedEl = document.getElementById('approvedCount');
    const totalHoursEl = document.getElementById('totalHours');
    // DC Protocol: Backend uses 'submitted' for pending entries
    if (pendingEl) pendingEl.textContent = this.entries.filter(e => e.status === 'submitted').length.toString();
    if (approvedEl) approvedEl.textContent = this.entries.filter(e => e.status === 'approved').length.toString();
    // Calculate hours from duration_minutes if hours not available
    const totalHours = this.filteredEntries.reduce((sum, e) => {
      const hours = e.hours ?? (e.duration_minutes ? e.duration_minutes / 60 : 0);
      return sum + hours;
    }, 0);
    if (totalHoursEl) totalHoursEl.textContent = totalHours.toFixed(1);

    if (this.filteredEntries.length === 0) {
      const message = this.searchQuery ? 'No matching entries' : `No ${this.filterStatus} entries`;
      listContainer.innerHTML = `<div class="empty-state">${message}</div>`;
      return;
    }

    listContainer.innerHTML = this.filteredEntries.map(entry => {
      const empCode = entry.employee_code || entry.emp_code || 'N/A';
      const description = entry.comments || entry.work_description || 'No description';
      const hours = entry.hours ?? (entry.duration_minutes ? entry.duration_minutes / 60 : 0);
      const taskName = entry.task_title || entry.task_name;
      const kraName = entry.kra_title || entry.kra_name;
      const statusLabel = entry.status === 'submitted' ? 'PENDING' : entry.status?.toUpperCase();
      
      return `
        <div class="list-card timesheet-entry-card">
          <div class="timesheet-header">
            <div class="employee-info-row">
              <div class="employee-avatar-sm">${this.getInitials(entry.employee_name)}</div>
              <div class="employee-details">
                <div class="employee-name">${entry.employee_name || 'Unknown'}</div>
                <div class="employee-meta">${empCode} • ${entry.entry_type || 'Others'}</div>
              </div>
            </div>
            <span class="status-badge ${entry.status}">${statusLabel}</span>
          </div>

          <div class="timesheet-date">
            ${this.formatDate(entry.date)}
          </div>

          <div class="timesheet-description">
            ${description}
          </div>

          ${taskName || kraName || entry.lead_name || entry.project_name ? `
            <div class="timesheet-tags">
              ${entry.project_name ? `<span class="entry-tag project">${entry.project_name}</span>` : ''}
              ${taskName ? `<span class="entry-tag task">${taskName}</span>` : ''}
              ${kraName ? `<span class="entry-tag kra">${kraName}</span>` : ''}
              ${entry.lead_name ? `<span class="entry-tag lead">${entry.lead_name}</span>` : ''}
            </div>
          ` : ''}

          <div class="timesheet-hours-single">
            <span class="hours-value">${hours.toFixed(1)}h</span>
          </div>

          <div class="timesheet-actions">
            ${entry.status === 'submitted' ? `
              <button class="btn btn-success btn-sm approve-btn" data-id="${entry.id}">Approve</button>
              <button class="btn btn-danger btn-sm reject-btn" data-id="${entry.id}">Reject</button>
            ` : ''}
          </div>
        </div>
      `;
    }).join('');

    this.attachCardListeners();
  }

  private attachCardListeners(): void {
    this.container.querySelectorAll('.approve-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = parseInt((btn as HTMLElement).dataset.id || '0');
        this.showApproveModal(id);
      });
    });

    this.container.querySelectorAll('.reject-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = parseInt((btn as HTMLElement).dataset.id || '0');
        this.showRejectModal(id);
      });
    });
  }

  private showApproveModal(id: number): void {
    const entry = this.entries.find(e => e.id === id);
    if (!entry) return;

    this.selectedEntry = entry;
    const empCode = entry.employee_code || entry.emp_code || 'N/A';
    const hours = entry.hours ?? (entry.duration_minutes ? entry.duration_minutes / 60 : 0);
    const description = entry.comments || entry.work_description || 'No description';

    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    const modalFooter = document.getElementById('modalFooter');
    const modal = document.getElementById('approvalModal');

    if (modalTitle) modalTitle.textContent = 'Approve Entry';

    if (modalBody) {
      modalBody.innerHTML = `
        <div class="approval-summary">
          <p><strong>${entry.employee_name}</strong> (${empCode})</p>
          <p>${this.formatDate(entry.date)}</p>
          <p class="hours-highlight">${hours.toFixed(1)}h</p>
          <p class="entry-desc-preview">${description}</p>
        </div>
        <div class="form-group">
          <label>Remarks (Optional)</label>
          <textarea id="approveRemarks" class="form-textarea" rows="2" placeholder="Add any remarks..."></textarea>
        </div>
      `;
    }

    if (modalFooter) {
      modalFooter.innerHTML = `
        <button class="btn btn-secondary" id="cancelApprove">Cancel</button>
        <button class="btn btn-success" id="confirmApprove">Approve</button>
      `;

      document.getElementById('cancelApprove')?.addEventListener('click', () => this.hideModal());
      document.getElementById('confirmApprove')?.addEventListener('click', () => this.submitApprove());
    }

    if (modal) modal.style.display = 'flex';
  }

  private async submitApprove(): Promise<void> {
    if (!this.selectedEntry) return;

    const remarks = (document.getElementById('approveRemarks') as HTMLTextAreaElement)?.value || '';
    await this.processAction(this.selectedEntry.id, 'approve', remarks || undefined);
  }

  private showRejectModal(id: number): void {
    const entry = this.entries.find(e => e.id === id);
    if (!entry) return;

    this.selectedEntry = entry;
    const empCode = entry.employee_code || entry.emp_code || 'N/A';
    const hours = entry.hours ?? (entry.duration_minutes ? entry.duration_minutes / 60 : 0);

    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    const modalFooter = document.getElementById('modalFooter');
    const modal = document.getElementById('approvalModal');

    if (modalTitle) modalTitle.textContent = 'Reject Entry';

    if (modalBody) {
      modalBody.innerHTML = `
        <div class="rejection-summary">
          <p><strong>${entry.employee_name}</strong> (${empCode})</p>
          <p>${this.formatDate(entry.date)} - ${hours.toFixed(1)}h</p>
        </div>
        <div class="form-group">
          <label>Rejection Reason <span class="required">*</span></label>
          <textarea id="rejectReason" class="form-textarea" rows="3" placeholder="Enter reason for rejection..."></textarea>
        </div>
      `;
    }

    if (modalFooter) {
      modalFooter.innerHTML = `
        <button class="btn btn-secondary" id="cancelReject">Cancel</button>
        <button class="btn btn-danger" id="confirmReject">Reject</button>
      `;

      document.getElementById('cancelReject')?.addEventListener('click', () => this.hideModal());
      document.getElementById('confirmReject')?.addEventListener('click', () => this.submitReject());
    }

    if (modal) modal.style.display = 'flex';
  }

  private async submitReject(): Promise<void> {
    if (!this.selectedEntry) return;

    const reason = (document.getElementById('rejectReason') as HTMLTextAreaElement)?.value || '';
    if (!reason.trim()) {
      alert('Rejection reason is required');
      return;
    }

    await this.processAction(this.selectedEntry.id, 'reject', reason);
  }

  private async processAction(id: number, action: 'approve' | 'reject', remarks?: string): Promise<void> {
    try {
      const response = await apiService.post(`/staff/timesheet/${id}/approve`, { 
        action, 
        remarks: remarks || null 
      });

      if (response.success !== false) {
        alert(`Entry ${action}d successfully`);
        this.hideModal();
        await this.loadEntries();
      } else {
        alert((response as any).error || `Failed to ${action} entry`);
      }
    } catch (error: any) {
      alert(error.message || `Failed to ${action} entry`);
    }
  }

  private hideModal(): void {
    const modal = document.getElementById('approvalModal');
    if (modal) modal.style.display = 'none';
    this.selectedEntry = null;
  }

  private getInitials(name: string): string {
    return name?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || '??';
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  }
}
