/**
 * Leaves Page - Full Workflow
 * DC Protocol: DC_MOBILE_LEAVES_001
 * View Balance + Apply Leave + Leave History
 * Matches web staff_my_leaves.html backend contract exactly
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface LeaveType {
  id: number;
  code: string;
  name: string;
  description: string;
  requires_document: boolean;
  allow_half_day: boolean;
  max_consecutive_days: number | null;
  min_advance_days: number;
}

interface LeaveBalanceItem {
  leave_type_id: number;
  leave_type_code: string;
  leave_type_name: string;
  balance: number;
  used: number;
  pending: number;
  available: number;
}

interface LeaveRequestDay {
  date: string;
  is_half_day: boolean;
  half_day_type: string | null;
  days_count: number;
}

interface LeaveRequest {
  id: number;
  leave_type_id: number;
  leave_type_name: string;
  reason: string;
  status: string;
  total_days: number;
  applied_at: string;
  can_cancel: boolean;
  days: LeaveRequestDay[];
}

interface SelectedDate {
  date: string;
  is_half_day: boolean;
  half_day_type: string | null;
}

const TYPE_STYLES: Record<string, { icon: string; color: string; cssClass: string }> = {
  'casual_leave': { icon: '🌴', color: '#10b981', cssClass: 'casual' },
  'sick_leave': { icon: '🏥', color: '#ef4444', cssClass: 'sick' },
  'approved_leave': { icon: '⭐', color: '#3b82f6', cssClass: 'privilege' },
  'unpaid_leave': { icon: '📋', color: '#6b7280', cssClass: 'unpaid' }
};

const DEFAULT_STYLE = { icon: '📅', color: '#8b5cf6', cssClass: 'casual' };

export class LeavesPage {
  private container: HTMLElement;
  private leaveTypes: LeaveType[] = [];
  private balances: LeaveBalanceItem[] = [];
  private balanceMap: Record<number, LeaveBalanceItem> = {};
  private requests: LeaveRequest[] = [];
  private selectedDates: SelectedDate[] = [];
  private loading: boolean = true;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await Promise.all([
      this.loadLeaveTypes(),
      this.loadBalances(),
      this.loadLeaveRequests()
    ]);
  }

  private async loadLeaveTypes(): Promise<void> {
    try {
      const response = await apiService.get<any>('/staff/leaves/leave-types');
      if (response.success && response.data) {
        this.leaveTypes = response.data.leave_types || response.data || [];
      }
    } catch (error) {
      console.error('[LeavesPage] Failed to load leave types:', error);
    }
  }

  private async loadBalances(): Promise<void> {
    try {
      const response = await apiService.get<any>('/staff/leaves/my-balance');

      if (response.success && response.data) {
        const rawBalances = response.data.balances || response.data || [];
        if (Array.isArray(rawBalances)) {
          this.balances = rawBalances;
          this.balanceMap = {};
          rawBalances.forEach((b: LeaveBalanceItem) => {
            this.balanceMap[b.leave_type_id] = b;
          });
        }
      }
    } catch (error) {
      console.error('[LeavesPage] Failed to load balances:', error);
    }
    this.updateBalanceCards();
  }

  private async loadLeaveRequests(): Promise<void> {
    this.loading = true;
    this.updateRequestsList();

    try {
      const year = new Date().getFullYear();
      const response = await apiService.get<any>(`/staff/leaves/my-requests?year=${year}`);

      if (response.success && response.data) {
        this.requests = response.data.requests || response.data || [];
      }
    } catch (error) {
      console.error('[LeavesPage] Failed to load requests:', error);
    }

    this.loading = false;
    this.updateRequestsList();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'My Leaves', showBack: true, rightAction: { icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>', onClick: () => {} } })}
        
        <div class="balance-cards" id="balanceCards">
          <div class="balance-card" style="border-left-color: #d1d5db">
            <div class="balance-header">
              <span class="balance-icon">⏳</span>
              <span class="balance-type">Loading balances...</span>
            </div>
            <div class="balance-value">--</div>
          </div>
        </div>

        <h4 class="section-title">Leave History</h4>
        <div class="list-container" id="requestsList">
          <div class="loading-state">Loading...</div>
        </div>
      </div>

      <!-- Apply Leave Modal -->
      <div class="modal-overlay" id="applyLeaveModal" style="display: none;">
        <div class="modal-content modal-lg">
          <div class="modal-header">
            <h4>Apply for Leave</h4>
            <button class="modal-close" id="closeApplyModal">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>Leave Type <span class="required">*</span></label>
              <select id="leaveType" class="form-select">
                <option value="">Select leave type</option>
              </select>
              <small class="form-hint" id="leaveTypeInfo"></small>
            </div>

            <div class="form-group" id="availableBalanceGroup" style="display:none;">
              <label>Available Balance</label>
              <div class="balance-indicator" id="availableBalanceDisplay"></div>
            </div>

            <div class="form-group">
              <label>Select Date(s) <span class="required">*</span></label>
              <input type="date" id="leaveDate" class="form-input">
              <div class="selected-dates-list" id="selectedDatesList"></div>
            </div>

            <div id="conflictWarning" class="conflict-banner" style="display:none;">
              <span class="conflict-icon">⚠️</span>
              <span id="conflictMessage"></span>
            </div>

            <div class="form-group">
              <label>Reason <span class="required">*</span></label>
              <textarea id="leaveReason" class="form-textarea" rows="3" placeholder="Please provide a detailed reason (min 10 characters)" minlength="10" maxlength="500"></textarea>
              <small class="form-hint"><span id="reasonCharCount">0</span>/500 characters</small>
            </div>

            <div class="leave-summary" id="leaveSummary">
              <span class="summary-label">Total Days:</span>
              <span class="summary-value" id="totalDays">0</span>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="cancelApplyBtn">Cancel</button>
            <button class="btn btn-primary" id="submitLeaveBtn">Submit Request</button>
          </div>
        </div>
      </div>

      <!-- Leave Detail Modal -->
      <div class="modal-overlay" id="leaveDetailModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Leave Details</h4>
            <button class="modal-close" id="closeDetailModal">&times;</button>
          </div>
          <div class="modal-body" id="leaveDetailContent"></div>
          <div class="modal-footer" id="leaveDetailActions"></div>
        </div>
      </div>
    `;

    this.attachListeners();
  }

  private attachListeners(): void {
    PageHeader.attachListeners({ 
      title: 'My Leaves', 
      showBack: true, 
      rightAction: { 
        icon: '+', 
        onClick: () => this.showApplyModal() 
      } 
    });

    document.getElementById('closeApplyModal')?.addEventListener('click', () => this.hideApplyModal());
    document.getElementById('cancelApplyBtn')?.addEventListener('click', () => this.hideApplyModal());
    document.getElementById('submitLeaveBtn')?.addEventListener('click', () => this.submitLeave());

    document.getElementById('leaveType')?.addEventListener('change', () => this.onLeaveTypeChange());
    document.getElementById('leaveDate')?.addEventListener('change', () => this.addLeaveDate());
    document.getElementById('leaveReason')?.addEventListener('input', () => this.updateCharCount());

    document.getElementById('closeDetailModal')?.addEventListener('click', () => this.hideDetailModal());
  }

  private updateBalanceCards(): void {
    const container = document.getElementById('balanceCards');
    if (!container) return;

    if (this.balances.length === 0) {
      container.innerHTML = `
        <div class="balance-card" style="border-left-color: #d1d5db">
          <div class="balance-header">
            <span class="balance-icon">📅</span>
            <span class="balance-type">No balance data</span>
          </div>
          <div class="balance-value">0</div>
        </div>
      `;
      return;
    }

    container.innerHTML = this.balances.map(b => {
      const style = TYPE_STYLES[b.leave_type_code] || DEFAULT_STYLE;
      return `
        <div class="balance-card" style="border-left-color: ${style.color}">
          <div class="balance-header">
            <span class="balance-icon">${style.icon}</span>
            <span class="balance-type">${b.leave_type_name}</span>
          </div>
          <div class="balance-value">${b.available}</div>
          <div class="balance-detail">
            <span>Used: ${b.used}</span>
            <span>Pending: ${b.pending}</span>
          </div>
        </div>
      `;
    }).join('');
  }

  private updateRequestsList(): void {
    const container = document.getElementById('requestsList');
    if (!container) return;

    if (this.loading) {
      container.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    if (this.requests.length === 0) {
      container.innerHTML = '<div class="empty-state">No leave requests found</div>';
      return;
    }

    container.innerHTML = this.requests.map(request => {
      const dateRange = this.getDateRange(request.days);
      return `
        <div class="list-item card leave-card" data-id="${request.id}">
          <div class="item-header">
            <span class="leave-type-badge ${this.getTypeClass(request.leave_type_name)}">${request.leave_type_name}</span>
            <span class="status-badge ${this.getStatusClass(request.status)}">${this.formatStatus(request.status)}</span>
          </div>
          <div class="leave-dates">
            <span class="date-range">${dateRange}</span>
            <span class="days-count">${request.total_days} day${request.total_days !== 1 ? 's' : ''}</span>
          </div>
          <div class="leave-reason">${request.reason || 'No reason provided'}</div>
          <div class="leave-meta">
            <span>Applied: ${this.formatDate(request.applied_at)}</span>
          </div>
          ${request.can_cancel ? `
            <div class="leave-actions">
              <button class="btn btn-sm btn-danger cancel-leave-btn" data-id="${request.id}">Cancel Request</button>
            </div>
          ` : ''}
        </div>
      `;
    }).join('');

    container.querySelectorAll('.cancel-leave-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const id = btn.getAttribute('data-id');
        await this.cancelLeave(parseInt(id!));
      });
    });

    container.querySelectorAll('.leave-card').forEach(card => {
      card.addEventListener('click', () => {
        const id = card.getAttribute('data-id');
        this.showLeaveDetail(parseInt(id!));
      });
    });
  }

  private getDateRange(days: LeaveRequestDay[]): string {
    if (!days || days.length === 0) return 'N/A';
    if (days.length === 1) return this.formatDate(days[0].date);
    const sorted = [...days].sort((a, b) => a.date.localeCompare(b.date));
    return `${this.formatDate(sorted[0].date)} - ${this.formatDate(sorted[sorted.length - 1].date)}`;
  }

  private showApplyModal(): void {
    this.selectedDates = [];

    const modal = document.getElementById('applyLeaveModal');
    if (modal) modal.style.display = 'flex';

    const select = document.getElementById('leaveType') as HTMLSelectElement;
    if (select) {
      select.innerHTML = '<option value="">Select leave type</option>' +
        this.leaveTypes.map(lt => `<option value="${lt.id}">${lt.name}</option>`).join('');
      select.value = '';
    }

    const dateInput = document.getElementById('leaveDate') as HTMLInputElement;
    if (dateInput) dateInput.value = '';

    const reasonInput = document.getElementById('leaveReason') as HTMLTextAreaElement;
    if (reasonInput) reasonInput.value = '';

    this.renderSelectedDates();
    this.updateTotalDays();
    this.updateCharCount();

    const balGroup = document.getElementById('availableBalanceGroup');
    if (balGroup) balGroup.style.display = 'none';
    const infoEl = document.getElementById('leaveTypeInfo');
    if (infoEl) infoEl.textContent = '';
    const conflictEl = document.getElementById('conflictWarning');
    if (conflictEl) conflictEl.style.display = 'none';
  }

  private hideApplyModal(): void {
    const modal = document.getElementById('applyLeaveModal');
    if (modal) modal.style.display = 'none';
  }

  private onLeaveTypeChange(): void {
    const typeId = parseInt((document.getElementById('leaveType') as HTMLSelectElement)?.value);
    const leaveType = this.leaveTypes.find(lt => lt.id === typeId);
    const balance = this.balanceMap[typeId];

    const infoEl = document.getElementById('leaveTypeInfo');
    if (infoEl && leaveType) {
      const info: string[] = [];
      if (leaveType.requires_document) info.push('Document required for >2 days');
      if (leaveType.min_advance_days > 0) info.push(`${leaveType.min_advance_days} day(s) advance notice`);
      if (leaveType.max_consecutive_days) info.push(`Max ${leaveType.max_consecutive_days} consecutive days`);
      if (leaveType.allow_half_day) info.push('Half-day allowed');
      infoEl.textContent = info.join(' · ');
    } else if (infoEl) {
      infoEl.textContent = '';
    }

    const balGroup = document.getElementById('availableBalanceGroup');
    const balDisplay = document.getElementById('availableBalanceDisplay');
    if (balGroup && balDisplay) {
      if (balance) {
        balGroup.style.display = 'block';
        if (balance.available <= 0) {
          balDisplay.innerHTML = `<span class="balance-warning">0 days available - LOP will be marked</span>`;
        } else {
          balDisplay.innerHTML = `<span class="balance-ok">${balance.available} days available</span>`;
        }
      } else {
        balGroup.style.display = 'none';
      }
    }

    this.renderSelectedDates();
  }

  private addLeaveDate(): void {
    const dateInput = document.getElementById('leaveDate') as HTMLInputElement;
    const dateValue = dateInput?.value;
    if (!dateValue) return;

    if (this.selectedDates.find(d => d.date === dateValue)) {
      alert('This date is already selected');
      dateInput.value = '';
      return;
    }

    this.selectedDates.push({ date: dateValue, is_half_day: false, half_day_type: null });
    dateInput.value = '';
    this.renderSelectedDates();
    this.updateTotalDays();
    this.checkConflicts();
  }

  private renderSelectedDates(): void {
    const container = document.getElementById('selectedDatesList');
    if (!container) return;

    if (this.selectedDates.length === 0) {
      container.innerHTML = '<div class="empty-dates-hint">Tap dates above to add leave days</div>';
      return;
    }

    const typeId = parseInt((document.getElementById('leaveType') as HTMLSelectElement)?.value);
    const leaveType = this.leaveTypes.find(lt => lt.id === typeId);
    const allowHalfDay = leaveType?.allow_half_day ?? true;

    container.innerHTML = this.selectedDates.map((d, idx) => {
      const dateObj = new Date(d.date + 'T00:00:00');
      const formatted = dateObj.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
      const dayType = d.is_half_day ? (d.half_day_type === 'first_half' ? '1st Half' : '2nd Half') : 'Full Day';

      return `
        <div class="date-chip-row">
          <span class="date-chip-label">${formatted}</span>
          ${allowHalfDay ? `
            <select class="date-type-select" data-idx="${idx}">
              <option value="full" ${!d.is_half_day ? 'selected' : ''}>Full Day</option>
              <option value="first_half" ${d.is_half_day && d.half_day_type === 'first_half' ? 'selected' : ''}>1st Half</option>
              <option value="second_half" ${d.is_half_day && d.half_day_type === 'second_half' ? 'selected' : ''}>2nd Half</option>
            </select>
          ` : `<span class="date-type-label">${dayType}</span>`}
          <button class="date-remove-btn" data-idx="${idx}">&times;</button>
        </div>
      `;
    }).join('');

    container.querySelectorAll('.date-type-select').forEach(sel => {
      sel.addEventListener('change', (e) => {
        const idx = parseInt((e.target as HTMLSelectElement).getAttribute('data-idx')!);
        const value = (e.target as HTMLSelectElement).value;
        if (value === 'full') {
          this.selectedDates[idx].is_half_day = false;
          this.selectedDates[idx].half_day_type = null;
        } else {
          this.selectedDates[idx].is_half_day = true;
          this.selectedDates[idx].half_day_type = value;
        }
        this.updateTotalDays();
      });
    });

    container.querySelectorAll('.date-remove-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const idx = parseInt((e.target as HTMLElement).getAttribute('data-idx')!);
        this.selectedDates.splice(idx, 1);
        this.renderSelectedDates();
        this.updateTotalDays();
        this.checkConflicts();
      });
    });
  }

  private updateTotalDays(): void {
    const el = document.getElementById('totalDays');
    if (!el) return;
    const total = this.selectedDates.reduce((sum, d) => sum + (d.is_half_day ? 0.5 : 1), 0);
    el.textContent = total.toString();
  }

  private updateCharCount(): void {
    const reason = (document.getElementById('leaveReason') as HTMLTextAreaElement)?.value || '';
    const el = document.getElementById('reasonCharCount');
    if (el) el.textContent = reason.length.toString();
  }

  private async checkConflicts(): Promise<void> {
    if (this.selectedDates.length === 0) {
      const el = document.getElementById('conflictWarning');
      if (el) el.style.display = 'none';
      return;
    }

    try {
      const dates = this.selectedDates.map(d => d.date).join(',');
      const response = await apiService.get<any>(`/staff/leaves/check-conflicts?dates=${dates}`);

      if (response.success && response.data) {
        const data = response.data;
        if (data.has_any_conflict) {
          const conflictDates = (data.conflicts || []).filter((c: any) => c.has_conflict).map((c: any) => c.date);
          const msgEl = document.getElementById('conflictMessage');
          const warnEl = document.getElementById('conflictWarning');
          if (msgEl) msgEl.textContent = `Attendance exists for: ${conflictDates.join(', ')}. These may be skipped or replaced.`;
          if (warnEl) warnEl.style.display = 'flex';
        } else {
          const warnEl = document.getElementById('conflictWarning');
          if (warnEl) warnEl.style.display = 'none';
        }
      }
    } catch (error) {
      console.error('[LeavesPage] Failed to check conflicts:', error);
    }
  }

  private async submitLeave(markAsLop: boolean = false): Promise<void> {
    const leaveTypeId = parseInt((document.getElementById('leaveType') as HTMLSelectElement)?.value);
    const reason = (document.getElementById('leaveReason') as HTMLTextAreaElement)?.value?.trim();

    if (!leaveTypeId) {
      alert('Please select a leave type');
      return;
    }

    if (this.selectedDates.length === 0) {
      alert('Please select at least one date');
      return;
    }

    if (!reason || reason.length < 10) {
      alert('Reason must be at least 10 characters');
      return;
    }

    const submitBtn = document.getElementById('submitLeaveBtn') as HTMLButtonElement;
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Submitting...';
    }

    try {
      const payload = {
        leave_type_id: leaveTypeId,
        reason: reason,
        days: this.selectedDates.map(d => ({
          leave_date: d.date,
          is_half_day: d.is_half_day,
          half_day_type: d.half_day_type
        })),
        conflict_resolution: 'skip',
        mark_as_lop: markAsLop
      };

      const response = await apiService.post<any>('/staff/leaves/apply', payload);

      if (response.success) {
        this.hideApplyModal();
        const lopMsg = markAsLop ? ' (Marked as Loss of Pay)' : '';
        const reqId = response.data?.leave_request_id || '';
        alert(`Leave request submitted successfully!${lopMsg}${reqId ? ` Request ID: #${reqId}` : ''}`);
        await Promise.all([
          this.loadBalances(),
          this.loadLeaveRequests()
        ]);
      } else if (response.data?.requires_lop_acknowledgment) {
        const confirmLop = confirm(
          `WARNING: Loss of Pay (LOP) will be marked!\n\n` +
          `Your available balance is ${response.data.available_balance} days, but you requested ${response.data.requested_days} days.\n\n` +
          `If you proceed, this leave will be marked as Loss of Pay and salary deduction will apply.\n\n` +
          `Do you want to continue?`
        );
        if (confirmLop) {
          await this.submitLeave(true);
          return;
        }
      } else if (response.data?.requires_conflict_resolution) {
        alert('Attendance conflicts found. Please resolve and try again.');
      } else {
        alert(response.error || response.data?.detail || 'Failed to submit leave request');
      }
    } catch (error: any) {
      const errMsg = error?.response?.data?.detail || error?.message || 'Failed to submit leave request';
      if (typeof errMsg === 'string' && errMsg.includes('requires_lop_acknowledgment')) {
        const confirmLop = confirm(
          'Your leave balance is insufficient. This will be marked as Loss of Pay (LOP). Continue?'
        );
        if (confirmLop) {
          await this.submitLeave(true);
          return;
        }
      } else {
        alert(errMsg);
      }
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit Request';
      }
    }
  }

  private showLeaveDetail(id: number): void {
    const request = this.requests.find(r => r.id === id);
    if (!request) return;

    const modal = document.getElementById('leaveDetailModal');
    const content = document.getElementById('leaveDetailContent');
    const actions = document.getElementById('leaveDetailActions');

    if (!modal || !content || !actions) return;

    const datesList = request.days.map(d => {
      const dateStr = this.formatDate(d.date);
      return d.is_half_day ? `${dateStr} (${d.half_day_type === 'first_half' ? '1st Half' : '2nd Half'})` : dateStr;
    }).join('<br>');

    content.innerHTML = `
      <div class="leave-detail">
        <div class="detail-row">
          <span class="detail-label">Request ID</span>
          <span class="detail-value">#${request.id}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Leave Type</span>
          <span class="leave-type-badge ${this.getTypeClass(request.leave_type_name)}">${request.leave_type_name}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Dates</span>
          <span class="detail-value">${datesList}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Total Days</span>
          <span class="detail-value">${request.total_days}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Status</span>
          <span class="status-badge ${this.getStatusClass(request.status)}">${this.formatStatus(request.status)}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Reason</span>
          <span class="detail-value">${request.reason || 'No reason provided'}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Applied On</span>
          <span class="detail-value">${this.formatDate(request.applied_at)}</span>
        </div>
      </div>
    `;

    actions.innerHTML = `
      <button class="btn btn-secondary" id="closeDetailBtn">Close</button>
      ${request.can_cancel ? `<button class="btn btn-danger" id="cancelLeaveDetailBtn">Cancel Request</button>` : ''}
    `;

    document.getElementById('closeDetailBtn')?.addEventListener('click', () => this.hideDetailModal());

    if (request.can_cancel) {
      document.getElementById('cancelLeaveDetailBtn')?.addEventListener('click', async () => {
        await this.cancelLeave(id);
        this.hideDetailModal();
      });
    }

    modal.style.display = 'flex';
  }

  private hideDetailModal(): void {
    const modal = document.getElementById('leaveDetailModal');
    if (modal) modal.style.display = 'none';
  }

  private async cancelLeave(id: number): Promise<void> {
    if (!confirm('Are you sure you want to cancel this leave request?')) return;

    try {
      const response = await apiService.post(`/staff/leaves/cancel/${id}`, {});

      if (response.success) {
        await Promise.all([
          this.loadBalances(),
          this.loadLeaveRequests()
        ]);
        alert('Leave request cancelled');
      } else {
        alert(response.error || 'Failed to cancel leave request');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to cancel leave request');
    }
  }

  private getTypeClass(typeName: string): string {
    const lower = typeName?.toLowerCase() || '';
    if (lower.includes('casual')) return 'casual';
    if (lower.includes('sick')) return 'sick';
    if (lower.includes('privilege') || lower.includes('approved')) return 'privilege';
    if (lower.includes('unpaid')) return 'unpaid';
    return 'casual';
  }

  private getStatusClass(status: string): string {
    const s = status?.toLowerCase().replace('_', '-') || 'pending';
    if (s.includes('pending')) return 'pending';
    if (s.includes('approved')) return 'approved';
    if (s.includes('rejected')) return 'rejected';
    if (s.includes('cancelled')) return 'cancelled';
    return s;
  }

  private formatStatus(status: string): string {
    if (!status) return 'Pending';
    return status
      .replace(/_/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase());
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
  }
}
