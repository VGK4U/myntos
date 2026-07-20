/**
 * Attendance History Page
 * DC Protocol: DC_MOBILE_ATTENDANCE_001
 * View attendance records with clock in/out history
 * Enhanced with exception requests and detail view
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import { routerService } from '../services/router.service';
import { APP_CONFIG } from '../config/app.config';

interface AttendanceRecord {
  id: number;
  date: string;
  clock_in_time: string | null;
  clock_out_time: string | null;
  total_hours: number | null;
  worked_hours?: number | null;
  status: string;
  clock_in_location: string | null;
  clock_out_location: string | null;
  clock_in_photo_url?: string | null;
  clock_out_photo_url?: string | null;
  clock_in_photo_time?: string | null;
  clock_out_photo_time?: string | null;
  has_photos?: boolean;
  has_exception?: boolean;
  exception_status?: string;
  is_regularized?: boolean;
  remarks?: string;
  total_gps_off_minutes?: number;
}

interface GpsGap {
  id: number;
  timestamp: string;
  reason: string;
  description: string;
  duration_seconds: number | null;
  source: string;
}

export class AttendancePage {
  private container: HTMLElement;
  private records: AttendanceRecord[] = [];
  private loading: boolean = true;
  private currentMonth: Date = new Date();
  private selectedRecord: AttendanceRecord | null = null;
  // DC Protocol: Use centralized configuration from APP_CONFIG
  private readonly baseUrl: string = APP_CONFIG.MEDIA_BASE_URL;

  constructor(container: HTMLElement) {
    this.container = container;
  }
  
  // DC Protocol (Jan 28, 2026): Construct absolute URL for photos in mobile app
  private getAbsolutePhotoUrl(photoUrl: string | null | undefined): string {
    if (!photoUrl) return '';
    return photoUrl.startsWith('http') ? photoUrl : `${this.baseUrl}${photoUrl.startsWith('/') ? '' : '/'}${photoUrl}`;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadAttendance();
  }

  private async loadAttendance(): Promise<void> {
    this.loading = true;
    this.updateList();

    try {
      const year = this.currentMonth.getFullYear();
      const month = this.currentMonth.getMonth() + 1;
      const fromDate = `${year}-${String(month).padStart(2, '0')}-01`;
      const lastDay = new Date(year, month, 0).getDate();
      const toDate = `${year}-${String(month).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`;
      
      const response = await apiService.get<any>(
        `/staff/attendance/my-history?from_date=${fromDate}&to_date=${toDate}&limit=100`
      );

      if (response.success && response.data) {
        this.records = response.data.records || response.data || [];
      } else {
        this.records = [];
      }
    } catch (error) {
      console.error('[AttendancePage] Failed to load:', error);
      this.records = [];
    }

    this.loading = false;
    this.updateList();
  }

  private render(): void {
    const monthName = this.currentMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'My Attendance', showBack: false })}
        
        <div class="month-selector">
          <button class="month-nav" id="prevMonth">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
          </button>
          <span class="month-label">${monthName}</span>
          <button class="month-nav" id="nextMonth">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
        </div>

        <div class="attendance-summary card" id="summary">
          <div class="summary-item">
            <span class="summary-value" id="totalDays">--</span>
            <span class="summary-label">Days Present</span>
          </div>
          <div class="summary-item">
            <span class="summary-value" id="totalHours">--</span>
            <span class="summary-label">Total Hours</span>
          </div>
          <div class="summary-item">
            <span class="summary-value" id="avgHours">--</span>
            <span class="summary-label">Avg Hours/Day</span>
          </div>
        </div>

        <div class="list-container" id="attendanceList">
          <div class="loading-state">Loading...</div>
        </div>
      </div>

      <!-- Detail Modal -->
      <div class="modal-overlay" id="detailModal" style="display: none;">
        <div class="modal-content modal-lg">
          <div class="modal-header">
            <h4>Attendance Details</h4>
            <button class="modal-close" id="closeDetailModal">&times;</button>
          </div>
          <div class="modal-body" id="detailBody"></div>
          <div class="modal-footer" id="detailFooter"></div>
        </div>
      </div>

      <!-- Exception Request Modal -->
      <div class="modal-overlay" id="exceptionModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Request Regularization</h4>
            <button class="modal-close" id="closeExceptionModal">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>Exception Type <span class="required">*</span></label>
              <select id="exceptionType" class="form-select">
                <option value="">Select type...</option>
                <option value="missed_clock_in">Missed Clock In</option>
                <option value="missed_clock_out">Missed Clock Out</option>
                <option value="wrong_time">Incorrect Time Recorded</option>
                <option value="work_from_home">Work From Home</option>
                <option value="on_duty">On Duty (Outdoor)</option>
              </select>
            </div>
            <div class="form-group" id="requestedInGroup" style="display: none;">
              <label>Requested Clock In Time</label>
              <input type="time" id="requestedClockIn" class="form-input">
            </div>
            <div class="form-group" id="requestedOutGroup" style="display: none;">
              <label>Requested Clock Out Time</label>
              <input type="time" id="requestedClockOut" class="form-input">
            </div>
            <div class="form-group">
              <label>Reason <span class="required">*</span></label>
              <textarea id="exceptionReason" class="form-textarea" rows="3" placeholder="Explain the reason for this request..."></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="cancelExceptionBtn">Cancel</button>
            <button class="btn btn-primary" id="submitExceptionBtn">Submit Request</button>
          </div>
        </div>
      </div>
    `;

    this.attachListeners();
  }

  private attachListeners(): void {
    PageHeader.attachListeners({ title: 'My Attendance', showBack: false });

    document.getElementById('prevMonth')?.addEventListener('click', () => {
      this.currentMonth.setMonth(this.currentMonth.getMonth() - 1);
      this.render();
      this.loadAttendance();
    });

    document.getElementById('nextMonth')?.addEventListener('click', () => {
      this.currentMonth.setMonth(this.currentMonth.getMonth() + 1);
      this.render();
      this.loadAttendance();
    });

    document.getElementById('closeDetailModal')?.addEventListener('click', () => this.hideModal('detailModal'));
    document.getElementById('closeExceptionModal')?.addEventListener('click', () => this.hideModal('exceptionModal'));
    document.getElementById('cancelExceptionBtn')?.addEventListener('click', () => this.hideModal('exceptionModal'));
    document.getElementById('submitExceptionBtn')?.addEventListener('click', () => this.submitException());

    document.getElementById('exceptionType')?.addEventListener('change', (e) => {
      const type = (e.target as HTMLSelectElement).value;
      const inGroup = document.getElementById('requestedInGroup');
      const outGroup = document.getElementById('requestedOutGroup');
      
      if (inGroup && outGroup) {
        inGroup.style.display = ['missed_clock_in', 'wrong_time', 'work_from_home', 'on_duty'].includes(type) ? 'block' : 'none';
        outGroup.style.display = ['missed_clock_out', 'wrong_time', 'work_from_home', 'on_duty'].includes(type) ? 'block' : 'none';
      }
    });
  }

  private showModal(modalId: string): void {
    const modal = document.getElementById(modalId);
    if (modal) modal.style.display = 'flex';
  }

  private hideModal(modalId: string): void {
    const modal = document.getElementById(modalId);
    if (modal) modal.style.display = 'none';
  }

  private updateList(): void {
    const listContainer = document.getElementById('attendanceList');
    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    if (this.records.length === 0) {
      listContainer.innerHTML = '<div class="empty-state">No attendance records found</div>';
      return;
    }

    const totalDays = this.records.filter(r => r.clock_in_time).length;
    const totalHours = this.records.reduce((sum, r) => sum + (r.total_hours || 0), 0);
    const avgHours = totalDays > 0 ? (totalHours / totalDays).toFixed(1) : '0';

    document.getElementById('totalDays')!.textContent = totalDays.toString();
    document.getElementById('totalHours')!.textContent = totalHours.toFixed(1);
    document.getElementById('avgHours')!.textContent = avgHours;

    listContainer.innerHTML = this.records.map(record => `
      <div class="list-item card attendance-record" data-id="${record.id}" data-date="${record.date}">
        <div class="item-header">
          <span class="item-date">${this.formatDate(record.date)}</span>
          <div class="status-badges">
            ${record.has_exception ? `<span class="status-badge exception ${record.exception_status || 'pending'}">${record.exception_status || 'Exception'}</span>` : ''}
            <span class="status-badge ${record.status?.toLowerCase() || 'present'}">${record.status || 'Present'}</span>
          </div>
        </div>
        <div class="item-details">
          <div class="time-row">
            <span class="time-label">In:</span>
            <span class="time-value">${record.clock_in_time ? this.formatTime(record.clock_in_time) : '--:--'}</span>
            ${record.clock_in_location ? `<span class="location-hint" title="${record.clock_in_location}">📍</span>` : ''}
          </div>
          <div class="time-row">
            <span class="time-label">Out:</span>
            <span class="time-value">${record.clock_out_time ? this.formatTime(record.clock_out_time) : '--:--'}</span>
            ${record.clock_out_location ? `<span class="location-hint" title="${record.clock_out_location}">📍</span>` : ''}
          </div>
          <div class="time-row">
            <span class="time-label">Hours:</span>
            <span class="time-value ${(record.total_hours || record.worked_hours || 0) < 8 ? 'warning' : ''}">${(record.total_hours || record.worked_hours) ? (record.total_hours || record.worked_hours)!.toFixed(1) : '--'}</span>
            ${record.has_photos ? '<span class="photo-indicator" title="Has photos">📷</span>' : ''}
          </div>
        </div>
        <div class="record-actions">
          <button class="btn btn-sm btn-outline view-detail-btn" data-id="${record.id}">Details</button>
          ${!record.has_exception && this.canRequestException(record) ? `
            <button class="btn btn-sm btn-outline request-exception-btn" data-id="${record.id}">Regularize</button>
          ` : ''}
        </div>
      </div>
    `).join('');

    this.attachRecordListeners();
  }

  private canRequestException(record: AttendanceRecord): boolean {
    const recordDate = new Date(record.date);
    const today = new Date();
    const daysDiff = Math.floor((today.getTime() - recordDate.getTime()) / (1000 * 60 * 60 * 24));
    return daysDiff <= 7 && (!record.clock_in_time || !record.clock_out_time || (record.total_hours || 0) < 4);
  }

  private attachRecordListeners(): void {
    this.container.querySelectorAll('.view-detail-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const id = parseInt((btn as HTMLElement).dataset.id || '0');
        this.showDetailModal(id);
      });
    });

    this.container.querySelectorAll('.request-exception-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const id = parseInt((btn as HTMLElement).dataset.id || '0');
        this.showExceptionModal(id);
      });
    });
  }

  private async showDetailModal(id: number): Promise<void> {
    const record = this.records.find(r => r.id === id);
    if (!record) return;

    this.selectedRecord = record;
    const body = document.getElementById('detailBody');
    const footer = document.getElementById('detailFooter');

    let gpsGaps: GpsGap[] = [];
    try {
      const gapsResponse = await apiService.get<{gaps: GpsGap[], total_offline_minutes: number}>(`/staff/attendance/gps-gaps/${id}`);
      if (gapsResponse.success && gapsResponse.data?.gaps) {
        gpsGaps = gapsResponse.data.gaps;
      }
    } catch (error) {
      console.error('[AttendancePage] Failed to load GPS gaps:', error);
    }

    if (body) {
      body.innerHTML = `
        <div class="detail-section">
          <h5>${this.formatDate(record.date)}</h5>
          <div class="detail-grid">
            <div class="detail-item">
              <span class="label">Status</span>
              <span class="value"><span class="status-badge ${record.status?.toLowerCase()}">${record.status || 'Present'}</span></span>
            </div>
            <div class="detail-item">
              <span class="label">Total Hours</span>
              <span class="value">${record.total_hours ? record.total_hours.toFixed(2) : '--'} hrs</span>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <h5>Clock In</h5>
          <div class="detail-grid">
            <div class="detail-item">
              <span class="label">Time</span>
              <span class="value">${record.clock_in_time ? this.formatTime(record.clock_in_time) : 'Not recorded'}</span>
            </div>
            ${record.clock_in_location ? `
              <div class="detail-item full-width">
                <span class="label">Location</span>
                <span class="value location-text">${record.clock_in_location}</span>
              </div>
            ` : ''}
            ${record.clock_in_photo_url ? `
              <div class="detail-item full-width photo-item">
                <span class="label">Photo</span>
                <div class="photo-preview">
                  <img src="${this.getAbsolutePhotoUrl(record.clock_in_photo_url)}" alt="Clock-In Photo" class="attendance-photo" data-url="${this.getAbsolutePhotoUrl(record.clock_in_photo_url)}" onerror="this.style.display='none';this.nextElementSibling?.classList.add('photo-error')">
                  <span class="photo-time">${record.clock_in_photo_time ? new Date(record.clock_in_photo_time).toLocaleTimeString('en-IN', {hour: '2-digit', minute: '2-digit'}) : ''}</span>
                </div>
              </div>
            ` : ''}
          </div>
        </div>

        <div class="detail-section">
          <h5>Clock Out</h5>
          <div class="detail-grid">
            <div class="detail-item">
              <span class="label">Time</span>
              <span class="value">${record.clock_out_time ? this.formatTime(record.clock_out_time) : 'Not recorded'}</span>
            </div>
            ${record.clock_out_location ? `
              <div class="detail-item full-width">
                <span class="label">Location</span>
                <span class="value location-text">${record.clock_out_location}</span>
              </div>
            ` : ''}
            ${record.clock_out_photo_url ? `
              <div class="detail-item full-width photo-item">
                <span class="label">Photo</span>
                <div class="photo-preview">
                  <img src="${this.getAbsolutePhotoUrl(record.clock_out_photo_url)}" alt="Clock-Out Photo" class="attendance-photo" data-url="${this.getAbsolutePhotoUrl(record.clock_out_photo_url)}" onerror="this.style.display='none';this.nextElementSibling?.classList.add('photo-error')">
                  <span class="photo-time">${record.clock_out_photo_time ? new Date(record.clock_out_photo_time).toLocaleTimeString('en-IN', {hour: '2-digit', minute: '2-digit'}) : ''}</span>
                </div>
              </div>
            ` : ''}
          </div>
        </div>

        ${record.has_exception ? `
          <div class="detail-section exception-info">
            <h5>Exception Request</h5>
            <div class="detail-item">
              <span class="label">Status</span>
              <span class="status-badge ${record.exception_status}">${record.exception_status}</span>
            </div>
          </div>
        ` : ''}

        ${gpsGaps.length > 0 || (record.total_gps_off_minutes && record.total_gps_off_minutes > 0) ? `
          <div class="detail-section gps-gaps-info">
            <h5>GPS Tracking Gaps</h5>
            ${record.total_gps_off_minutes ? `
              <div class="detail-item">
                <span class="label">Total Offline Time</span>
                <span class="value warning">${this.formatMinutes(record.total_gps_off_minutes)}</span>
              </div>
            ` : ''}
            ${gpsGaps.length > 0 ? `
              <div class="gaps-list">
                ${gpsGaps.map(gap => `
                  <div class="gap-item">
                    <span class="gap-time">${gap.timestamp ? new Date(gap.timestamp).toLocaleTimeString('en-IN', {hour: '2-digit', minute: '2-digit'}) : '--:--'}</span>
                    <span class="gap-reason">${this.formatGapReason(gap.reason)}</span>
                    ${gap.duration_seconds ? `<span class="gap-duration">(${Math.round(gap.duration_seconds / 60)} min)</span>` : ''}
                  </div>
                `).join('')}
              </div>
            ` : ''}
          </div>
        ` : ''}

        ${record.remarks ? `
          <div class="detail-section">
            <h5>Remarks</h5>
            <p>${record.remarks}</p>
          </div>
        ` : ''}
      `;
    }

    if (footer) {
      footer.innerHTML = `
        <button class="btn btn-secondary" id="closeDetailBtn">Close</button>
        ${!record.has_exception && this.canRequestException(record) ? `
          <button class="btn btn-primary" id="requestFromDetailBtn">Request Regularization</button>
        ` : ''}
      `;

      document.getElementById('closeDetailBtn')?.addEventListener('click', () => this.hideModal('detailModal'));
      document.getElementById('requestFromDetailBtn')?.addEventListener('click', () => {
        this.hideModal('detailModal');
        this.showExceptionModal(id);
      });
    }

    this.showModal('detailModal');
  }

  private showExceptionModal(id: number): void {
    const record = this.records.find(r => r.id === id);
    if (!record) return;

    this.selectedRecord = record;

    (document.getElementById('exceptionType') as HTMLSelectElement).value = '';
    (document.getElementById('requestedClockIn') as HTMLInputElement).value = '';
    (document.getElementById('requestedClockOut') as HTMLInputElement).value = '';
    (document.getElementById('exceptionReason') as HTMLTextAreaElement).value = '';
    document.getElementById('requestedInGroup')!.style.display = 'none';
    document.getElementById('requestedOutGroup')!.style.display = 'none';

    this.showModal('exceptionModal');
  }

  private async submitException(): Promise<void> {
    if (!this.selectedRecord) return;

    const exceptionType = (document.getElementById('exceptionType') as HTMLSelectElement).value;
    const requestedClockIn = (document.getElementById('requestedClockIn') as HTMLInputElement).value;
    const requestedClockOut = (document.getElementById('requestedClockOut') as HTMLInputElement).value;
    const reason = (document.getElementById('exceptionReason') as HTMLTextAreaElement).value.trim();

    if (!exceptionType) {
      alert('Please select exception type');
      return;
    }
    if (!reason) {
      alert('Please provide a reason');
      return;
    }

    const btn = document.getElementById('submitExceptionBtn') as HTMLButtonElement;
    if (btn) { btn.disabled = true; btn.textContent = 'Submitting...'; }

    try {
      const payload: any = {
        date: this.selectedRecord.date,
        exception_type: exceptionType,
        reason
      };

      if (requestedClockIn) payload.requested_clock_in = requestedClockIn;
      if (requestedClockOut) payload.requested_clock_out = requestedClockOut;

      const response = await apiService.post('/staff/attendance/regularization-request', payload);

      if (response.success) {
        alert('Regularization request submitted successfully!');
        this.hideModal('exceptionModal');
        await this.loadAttendance();
      } else {
        alert(response.error || 'Failed to submit request');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to submit request');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'Submit Request'; }
    }
  }

  private formatDate(dateStr: string): string {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { weekday: 'short', day: 'numeric', month: 'short' });
  }

  private formatTime(timeStr: string): string {
    const date = new Date(timeStr);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  }

  private formatMinutes(minutes: number): string {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours > 0) {
      return `${hours}h ${mins}m`;
    }
    return `${mins} min`;
  }

  private formatGapReason(reason: string): string {
    const reasonMap: Record<string, string> = {
      'device_reboot': 'Device Restart',
      'app_background': 'App in Background',
      'app_killed': 'App Closed',
      'gps_disabled': 'GPS Disabled',
      'permission_denied': 'Permission Denied',
      'network_error': 'Network Error',
      'location_timeout': 'Location Timeout',
      'tab_hidden': 'Browser Tab Hidden',
      'page_unload': 'Page Closed',
      'unknown': 'Unknown'
    };
    return reasonMap[reason] || reason.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }
}
