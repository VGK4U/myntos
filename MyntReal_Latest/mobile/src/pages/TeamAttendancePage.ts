/**
 * Staff Team Attendance Page
 * DC Protocol: DC_MOBILE_STAFF_TEAM_ATT_001
 * View team member attendance (for managers)
 * Enhanced with department and status filters
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import { APP_CONFIG } from '../config/app.config';

interface TeamMember {
  id: number;
  name: string;
  emp_code: string;
  employee_code?: string;
  department: string;
  status: 'present' | 'absent' | 'leave' | 'wfh' | 'half_day';
  clock_in: string | null;
  clock_out: string | null;
  hours_worked: number;
  break_minutes?: number;
  is_active_journey: boolean;
  late_by_minutes?: number;
  early_leaving_minutes?: number;
  clock_in_photo_url?: string | null;
  clock_out_photo_url?: string | null;
  clock_in_area_name?: string | null;
  clock_out_area_name?: string | null;
  is_away_clock_in?: boolean;
  is_away_clock_out?: boolean;
  has_photos?: boolean;
  battery_percentage?: number | null;
  current_status?: string;
  last_gps_lat?: number | null;
  last_gps_lng?: number | null;
  last_gps_update?: string | null;
}

interface Department {
  id: number;
  name: string;
}

export class TeamAttendancePage {
  private container: HTMLElement;
  private teamMembers: TeamMember[] = [];
  private filteredMembers: TeamMember[] = [];
  private loading: boolean = true;
  private selectedDate: string = '';
  private departments: Department[] = [];
  private selectedDepartment: string = '';
  private selectedStatus: string = '';

  constructor(container: HTMLElement) {
    this.container = container;
    this.selectedDate = new Date().toISOString().split('T')[0];
  }

  async init(): Promise<void> {
    this.render();
    await Promise.all([this.loadTeamAttendance(), this.loadDepartments()]);
  }

  private async loadDepartments(): Promise<void> {
    try {
      const response = await apiService.get<any>('/staff/departments');
      if (response.success && response.data) {
        this.departments = response.data.departments || response.data || [];
        this.updateDepartmentSelect();
      }
    } catch (error) {
      console.error('[TeamAttendance] Failed to load departments:', error);
    }
  }

  private updateDepartmentSelect(): void {
    const select = document.getElementById('deptFilter') as HTMLSelectElement;
    if (select) {
      select.innerHTML = `<option value="">All Departments</option>` +
        this.departments.map(d => `<option value="${d.name}">${d.name}</option>`).join('');
    }
  }

  private async loadTeamAttendance(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      let endpoint = `/staff/attendance/team?date=${this.selectedDate}`;
      if (this.selectedDepartment) endpoint += `&department=${encodeURIComponent(this.selectedDepartment)}`;
      
      const response = await apiService.get<any>(endpoint);
      if (response.success && response.data) {
        this.teamMembers = response.data.members || response.data || [];
        this.applyFilters();
      }
    } catch (error) {
      console.error('[TeamAttendance] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private applyFilters(): void {
    this.filteredMembers = this.teamMembers.filter(m => {
      if (this.selectedStatus && m.status !== this.selectedStatus) return false;
      return true;
    });
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Team Attendance', showBack: true })}
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: 'Team Attendance', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    const present = this.teamMembers.filter(m => m.status === 'present').length;
    const absent = this.teamMembers.filter(m => m.status === 'absent').length;
    const leave = this.teamMembers.filter(m => m.status === 'leave').length;
    const wfh = this.teamMembers.filter(m => m.status === 'wfh').length;
    const lateArrivals = this.teamMembers.filter(m => (m.late_by_minutes || 0) > 0).length;

    content.innerHTML = `
      <div class="filters-section card">
        <div class="filters-row">
          <input type="date" id="datePicker" value="${this.selectedDate}" class="form-input">
          <select id="deptFilter" class="form-select">
            <option value="">All Departments</option>
          </select>
        </div>
      </div>

      <div class="filter-tabs scrollable">
        <button class="filter-tab ${this.selectedStatus === '' ? 'active' : ''}" data-status="">All (${this.teamMembers.length})</button>
        <button class="filter-tab ${this.selectedStatus === 'present' ? 'active' : ''}" data-status="present">Present (${present})</button>
        <button class="filter-tab ${this.selectedStatus === 'absent' ? 'active' : ''}" data-status="absent">Absent (${absent})</button>
        <button class="filter-tab ${this.selectedStatus === 'leave' ? 'active' : ''}" data-status="leave">Leave (${leave})</button>
        <button class="filter-tab ${this.selectedStatus === 'wfh' ? 'active' : ''}" data-status="wfh">WFH (${wfh})</button>
      </div>

      <div class="attendance-summary card">
        <div class="summary-grid five-col">
          <div class="summary-item clickable" data-status="present">
            <span class="summary-value present">${present}</span>
            <span class="summary-label">Present</span>
          </div>
          <div class="summary-item clickable" data-status="absent">
            <span class="summary-value absent">${absent}</span>
            <span class="summary-label">Absent</span>
          </div>
          <div class="summary-item clickable" data-status="leave">
            <span class="summary-value leave">${leave}</span>
            <span class="summary-label">Leave</span>
          </div>
          <div class="summary-item clickable" data-status="wfh">
            <span class="summary-value wfh">${wfh}</span>
            <span class="summary-label">WFH</span>
          </div>
          <div class="summary-item">
            <span class="summary-value warning">${lateArrivals}</span>
            <span class="summary-label">Late</span>
          </div>
        </div>
      </div>

      <h4 class="section-title">Team Members (${this.filteredMembers.length})</h4>
      ${this.filteredMembers.length > 0 ? `
        <div class="team-list">
          ${this.filteredMembers.map(member => this.renderMember(member)).join('')}
        </div>
      ` : `
        <div class="empty-state card">
          <div class="empty-icon">👥</div>
          <p>No team members found</p>
        </div>
      `}
    `;

    this.attachContentListeners();
    this.updateDepartmentSelect();
    
    const deptSelect = document.getElementById('deptFilter') as HTMLSelectElement;
    if (deptSelect && this.selectedDepartment) {
      deptSelect.value = this.selectedDepartment;
    }
  }

  private attachContentListeners(): void {
    document.getElementById('datePicker')?.addEventListener('change', (e) => {
      this.selectedDate = (e.target as HTMLInputElement).value;
      this.loadTeamAttendance();
    });

    document.getElementById('deptFilter')?.addEventListener('change', (e) => {
      this.selectedDepartment = (e.target as HTMLSelectElement).value;
      this.loadTeamAttendance();
    });

    this.container.querySelectorAll('.filter-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        this.selectedStatus = (tab as HTMLElement).dataset.status || '';
        this.applyFilters();
        this.container.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        this.updateMemberList();
      });
    });

    this.container.querySelectorAll('.summary-item.clickable').forEach(item => {
      item.addEventListener('click', () => {
        this.selectedStatus = (item as HTMLElement).dataset.status || '';
        this.applyFilters();
        this.container.querySelectorAll('.filter-tab').forEach(t => {
          t.classList.toggle('active', (t as HTMLElement).dataset.status === this.selectedStatus);
        });
        this.updateMemberList();
      });
    });
    
    // Photo button handlers
    this.container.querySelectorAll('.photo-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const photoUrl = (btn as HTMLElement).dataset.photo;
        const photoType = (btn as HTMLElement).dataset.type;
        if (photoUrl) {
          this.showPhotoModal(photoUrl, photoType === 'in' ? 'Clock-In Photo' : 'Clock-Out Photo');
        }
      });
    });
  }
  
  private showPhotoModal(photoUrl: string, title: string): void {
    const existingModal = document.getElementById('photoViewerModal');
    if (existingModal) existingModal.remove();
    
    // DC Protocol: Use centralized configuration from APP_CONFIG
    const fullPhotoUrl = photoUrl.startsWith('http') ? photoUrl : `${APP_CONFIG.MEDIA_BASE_URL}${photoUrl.startsWith('/') ? '' : '/'}${photoUrl}`;
    
    const modal = document.createElement('div');
    modal.id = 'photoViewerModal';
    modal.className = 'photo-modal';
    modal.innerHTML = `
      <div class="photo-modal-content">
        <div class="photo-modal-header">
          <h3>${title}</h3>
          <button class="photo-modal-close">&times;</button>
        </div>
        <div class="photo-modal-body">
          <img src="${fullPhotoUrl}" alt="${title}" onerror="this.parentElement.innerHTML='<div style=\\'text-align:center;padding:20px;color:#888;\\'>Photo not available</div>'" />
        </div>
      </div>
    `;
    
    document.body.appendChild(modal);
    
    modal.querySelector('.photo-modal-close')?.addEventListener('click', () => modal.remove());
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.remove();
    });
  }

  private updateMemberList(): void {
    const title = this.container.querySelector('.section-title');
    if (title) title.textContent = `Team Members (${this.filteredMembers.length})`;

    const list = this.container.querySelector('.team-list');
    if (list) {
      if (this.filteredMembers.length > 0) {
        list.innerHTML = this.filteredMembers.map(member => this.renderMember(member)).join('');
        // Reattach photo button listeners
        list.querySelectorAll('.photo-btn').forEach(btn => {
          btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const photoUrl = (btn as HTMLElement).dataset.photo;
            const photoType = (btn as HTMLElement).dataset.type;
            if (photoUrl) {
              this.showPhotoModal(photoUrl, photoType === 'in' ? 'Clock-In Photo' : 'Clock-Out Photo');
            }
          });
        });
      } else {
        list.innerHTML = `<div class="empty-state card"><div class="empty-icon">👥</div><p>No team members found</p></div>`;
      }
    }
  }

  private renderMember(member: TeamMember): string {
    const statusClass = member.status;
    // DC Protocol: Handle undefined/null name gracefully with fallback
    const displayName = member.name || (member as any).full_name || (member as any).employee_name || member.emp_code || member.employee_code || 'Unknown';
    const empCode = member.emp_code || member.employee_code || 'N/A';
    const initials = displayName.split(' ').map((n: string) => n[0]).join('').toUpperCase().slice(0, 2) || '??';
    const isLate = (member.late_by_minutes || 0) > 0;
    
    // Calculate hours breakdown
    let loginMinutes = 0;
    if (member.clock_in) {
      const clockIn = new Date(member.clock_in);
      const clockOut = member.clock_out ? new Date(member.clock_out) : new Date();
      loginMinutes = Math.floor((clockOut.getTime() - clockIn.getTime()) / 60000);
    }
    const breakMinutes = member.break_minutes || 0;
    const workedMinutes = Math.max(0, loginMinutes - breakMinutes);
    
    const loginHrs = Math.floor(loginMinutes / 60);
    const loginMins = loginMinutes % 60;
    const breakHrs = Math.floor(breakMinutes / 60);
    const breakMins = breakMinutes % 60;
    const workedHrs = Math.floor(workedMinutes / 60);
    const workedMins = workedMinutes % 60;

    const hasPhotos = member.clock_in_photo_url || member.clock_out_photo_url;
    
    // Build location strings with Office/Out of Office designation
    let clockInLocation = '';
    if (member.clock_in_area_name) {
      const officeStatus = member.is_away_clock_in ? '🔴 Out of Office' : '🟢 Office';
      clockInLocation = `${officeStatus} • ${member.clock_in_area_name}`;
    }
    
    let clockOutLocation = '';
    if (member.clock_out_area_name) {
      const officeStatus = member.is_away_clock_out ? '🔴 Out of Office' : '🟢 Office';
      clockOutLocation = `${officeStatus} • ${member.clock_out_area_name}`;
    }

    return `
      <div class="team-member-card card ${statusClass}" data-member-id="${member.id}">
        <div class="member-header">
          <div class="member-avatar ${member.is_active_journey ? 'on-journey' : ''}">${initials}</div>
          <div class="member-info">
            <h4>${displayName}</h4>
            <p class="member-code">${empCode} • ${member.department || 'N/A'}</p>
          </div>
          <div class="member-status">
            <span class="status-badge ${statusClass}">${this.formatStatus(member.status)}</span>
            ${member.is_active_journey ? '<span class="journey-indicator">🚗</span>' : ''}
            ${member.battery_percentage != null ? `<div class="battery-info">🔋 ${member.battery_percentage}%</div>` : ''}
            ${member.current_status === 'active' && !member.last_gps_lat ? '<div class="gps-status no-gps">No GPS data</div>' : ''}
            ${member.last_gps_update ? `<div class="gps-status has-gps">${this.formatTimeAgo(member.last_gps_update)}</div>` : ''}
          </div>
        </div>
        
        ${member.status === 'present' || member.status === 'wfh' ? `
          <div class="member-details">
            <!-- Time Row -->
            <div class="time-row">
              <div class="time-item">
                <span class="time-label">In</span>
                <span class="time-value">${member.clock_in ? this.formatTime(member.clock_in) : '--:--'}</span>
                ${isLate ? `<span class="late-badge">+${member.late_by_minutes}m</span>` : ''}
              </div>
              <span class="time-arrow">→</span>
              <div class="time-item">
                <span class="time-label">Out</span>
                <span class="time-value ${!member.clock_out ? 'active' : ''}">${member.clock_out ? this.formatTime(member.clock_out) : 'Active'}</span>
              </div>
            </div>
            
            <!-- Hours Breakdown -->
            <div class="hours-breakdown">
              <div class="hours-item">
                <span class="hours-label">Login</span>
                <span class="hours-value">${loginHrs}:${loginMins.toString().padStart(2, '0')}</span>
              </div>
              <div class="hours-item break">
                <span class="hours-label">Breaks</span>
                <span class="hours-value">${breakHrs}:${breakMins.toString().padStart(2, '0')}</span>
              </div>
              <div class="hours-item worked">
                <span class="hours-label">Worked</span>
                <span class="hours-value">${workedHrs}:${workedMins.toString().padStart(2, '0')}</span>
              </div>
            </div>
            
            <!-- Locations -->
            ${clockInLocation || clockOutLocation ? `
              <div class="location-row">
                ${clockInLocation ? `<div class="location-item"><span class="loc-icon">📍</span><span class="loc-text">In: ${clockInLocation}</span></div>` : ''}
                ${clockOutLocation ? `<div class="location-item"><span class="loc-icon">📍</span><span class="loc-text">Out: ${clockOutLocation}</span></div>` : ''}
              </div>
            ` : ''}
            
            <!-- Photo Buttons -->
            ${hasPhotos ? `
              <div class="photo-buttons">
                ${member.clock_in_photo_url ? `<button class="photo-btn" data-photo="${member.clock_in_photo_url}" data-type="in">📷 Clock-In Photo</button>` : ''}
                ${member.clock_out_photo_url ? `<button class="photo-btn" data-photo="${member.clock_out_photo_url}" data-type="out">📷 Clock-Out Photo</button>` : ''}
              </div>
            ` : ''}
          </div>
        ` : ''}
      </div>
    `;
  }

  private formatStatus(status: string): string {
    const statusMap: Record<string, string> = {
      present: 'Present',
      absent: 'Absent',
      leave: 'Leave',
      wfh: 'WFH',
      half_day: 'Half Day'
    };
    return statusMap[status] || status.toUpperCase();
  }

  private formatTime(dateStr: string): string {
    return new Date(dateStr).toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit' });
  }

  private formatTimeAgo(dateStr: string): string {
    try {
      const date = new Date(dateStr);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      
      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours}h ago`;
      const diffDays = Math.floor(diffHours / 24);
      return `${diffDays}d ago`;
    } catch {
      return 'N/A';
    }
  }
}
