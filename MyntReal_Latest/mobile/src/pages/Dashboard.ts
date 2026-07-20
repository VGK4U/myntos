/**
 * Dashboard Page Component
 * DC Protocol: DC_MOBILE_DASHBOARD_001
 * Main screen after login - attendance, journey, stats
 */

import { authService } from '../services/auth.service';
import { gpsService } from '../services/gps.service';
import { cameraService } from '../services/camera.service';
import { apiService } from '../services/api.service';
import { getSideDrawer } from '../components/SideDrawer';

interface AttendanceState {
  status: 'not_clocked_in' | 'clocked_in' | 'on_break' | 'clocked_out';
  isClockedIn: boolean;
  isOnBreak: boolean;
  clockInTime: string | null;
  clockOutTime: string | null;
  hasActiveJourney: boolean;
  activeJourneyId: number | null;
  workMode: 'office' | 'wfh' | 'field';
  activeBreak: any | null;
  breakTypes: { id: number; name: string; code: string }[];
  workedMinutes: number | null;
  totalBreakMinutes: number;
}

export class DashboardPage {
  private container: HTMLElement;
  private state: AttendanceState = {
    status: 'not_clocked_in',
    isClockedIn: false,
    isOnBreak: false,
    clockInTime: null,
    clockOutTime: null,
    hasActiveJourney: false,
    activeJourneyId: null,
    workMode: 'office',
    activeBreak: null,
    breakTypes: [],
    workedMinutes: null,
    totalBreakMinutes: 0
  };
  private user: any = null;
  private gpsStatusInterval: any = null;
  private hoursWorkedInterval: any = null;
  private attendancePollInterval: any = null;
  private initialUpdateTimeout: any = null;
  private isDestroyed: boolean = false;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  cleanup(): void {
    this.isDestroyed = true;
    if (this.gpsStatusInterval) {
      clearInterval(this.gpsStatusInterval);
      this.gpsStatusInterval = null;
    }
    if (this.hoursWorkedInterval) {
      clearInterval(this.hoursWorkedInterval);
      this.hoursWorkedInterval = null;
    }
    if (this.attendancePollInterval) {
      clearInterval(this.attendancePollInterval);
      this.attendancePollInterval = null;
    }
    if (this.initialUpdateTimeout) {
      clearTimeout(this.initialUpdateTimeout);
      this.initialUpdateTimeout = null;
    }
  }

  async init(): Promise<void> {
    const authState = authService.getAuthState();
    this.user = authState.user;
    this.state.isClockedIn = authState.isClockedIn;
    this.state.hasActiveJourney = authState.hasActiveJourney;

    gpsService.setClockedIn(this.state.isClockedIn);

    this.render();
    this.attachEventListeners();
    
    // Load status and break types in parallel
    await Promise.all([
      this.refreshStatus(),
      this.loadBreakTypes()
    ]);
    
    // Initialize GPS status immediately (don't wait for interval)
    this.initGpsStatus();
  }

  private async loadBreakTypes(): Promise<void> {
    try {
      const response = await apiService.get<any>('/staff/attendance/break-types');
      const data = response.data as any;
      if (response.success !== false && data?.break_types) {
        this.state.breakTypes = data.break_types.map((bt: any) => ({
          id: bt.id,
          name: bt.name,
          code: bt.code
        }));
      }
    } catch (error) {
      console.error('[Dashboard] Failed to load break types:', error);
      // Default break types
      this.state.breakTypes = [
        { id: 1, name: 'Lunch Break', code: 'lunch' },
        { id: 2, name: 'Tea Break', code: 'tea' },
        { id: 3, name: 'Personal Break', code: 'personal' }
      ];
    }
  }
  
  private async initGpsStatus(): Promise<void> {
    if (!this.state.isClockedIn && !this.state.hasActiveJourney) {
      this.updateGpsStatus();
      return;
    }
    try {
      const position = await gpsService.getCurrentPosition();
      this.updateGpsStatus();
      if (!position) {
        console.warn('[Dashboard] GPS position unavailable');
      }
    } catch (error) {
      console.error('[Dashboard] GPS init error:', error);
      this.updateGpsStatus();
    }
  }

  private async refreshStatus(): Promise<void> {
    if (this.isDestroyed) return;
    try {
      // DC Protocol: Use /staff/attendance/today endpoint (web parity)
      const response = await apiService.get<any>('/staff/attendance/today');
      
      const data = response.data as any;
      if (response.success !== false && data) {
        const status = data.status || 'not_clocked_in';
        const attendance = data.attendance;
        
        this.state.status = status;
        this.state.isClockedIn = status === 'clocked_in' || status === 'on_break';
        this.state.isOnBreak = status === 'on_break';
        // DC_FIX_NAN_001: Use clock_in (full ISO datetime) instead of clock_in_time (HH:MM string)
        this.state.clockInTime = attendance?.clock_in || null;
        this.state.clockOutTime = attendance?.clock_out || null;
        this.state.activeBreak = data.active_break || null;
        this.state.workedMinutes = attendance?.worked_minutes ?? data.worked_minutes ?? null;
        this.state.totalBreakMinutes = attendance?.break_minutes ?? data.total_break_minutes ?? 0;
        
        
        gpsService.setClockedIn(this.state.isClockedIn);
        // DC Protocol (Jan 28, 2026): Sync break state with GPS service on every status refresh
        // This ensures GPS tracking is paused during breaks even after app restart or refresh
        gpsService.setOnBreak(this.state.isOnBreak);
        authService.setClockedIn(this.state.isClockedIn);
        if (this.isDestroyed) return;
        this.updateUI();
        this.updateDashboardStats();
      }
    } catch (error) {
      console.error('[Dashboard] Failed to refresh status:', error);
    }
  }

  private updateDashboardStats(): void {
    const todayHoursEl = document.getElementById('todayHours');
    if (todayHoursEl) {
      if (this.state.workedMinutes !== undefined && this.state.workedMinutes !== null) {
        const hours = Math.floor(this.state.workedMinutes / 60);
        const mins = this.state.workedMinutes % 60;
        todayHoursEl.textContent = `${hours}:${mins.toString().padStart(2, '0')}`;
      } else if (this.state.isClockedIn && this.state.clockInTime) {
        const clockIn = new Date(this.state.clockInTime);
        if (!isNaN(clockIn.getTime())) {
          const now = new Date();
          const diffMs = now.getTime() - clockIn.getTime();
          if (diffMs > 0) {
            const hours = Math.floor(diffMs / 3600000);
            const mins = Math.floor((diffMs % 3600000) / 60000);
            todayHoursEl.textContent = `${hours}:${mins.toString().padStart(2, '0')}`;
          } else {
            todayHoursEl.textContent = '0:00';
          }
        } else {
          todayHoursEl.textContent = '--:--';
        }
      } else {
        todayHoursEl.textContent = '--:--';
      }
    }
    this.fetchTodayJourneys();
  }

  private async fetchTodayJourneys(): Promise<void> {
    if (this.isDestroyed) return;
    try {
      const today = new Date().toISOString().split('T')[0];
      const response = await apiService.get<any>(`/staff/journeys/my?start_date=${today}&end_date=${today}`);
      if (this.isDestroyed) return;
      if (response.success && response.data) {
        const journeys = response.data.journeys || response.data || [];
        const todayJourneysEl = document.getElementById('todayJourneys');
        if (todayJourneysEl) {
          todayJourneysEl.textContent = journeys.length.toString();
        }
      }
    } catch (error) {
      console.error('[Dashboard] Failed to fetch today journeys:', error);
    }
  }

  private render(): void {
    if (this.isDestroyed) return;
    const username = this.user?.name || this.user?.emp_code || 'Staff';
    
    this.container.innerHTML = `
      <div class="dashboard-container">
        <header class="dashboard-header">
          <button id="hamburgerBtn" class="hamburger-btn">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="3" y1="6" x2="21" y2="6"/>
              <line x1="3" y1="12" x2="21" y2="12"/>
              <line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
          </button>
          <div class="user-info">
            <div class="user-avatar">${this.getInitials(username)}</div>
            <div class="user-details">
              <h2 class="user-name">${username}</h2>
              <p class="user-role">${this.user?.role_name || 'Employee'}</p>
            </div>
          </div>
          <button id="logoutBtn" class="header-btn">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
          </button>
        </header>

        <main class="dashboard-content">
          <!-- Status Card -->
          <div class="card status-card" id="statusCard">
            <div class="status-header">
              <div class="status-indicator ${this.getStatusClass()}">
                <span class="status-dot"></span>
                <span class="status-text">${this.getStatusText()}</span>
              </div>
              ${this.state.clockInTime ? `
                <p class="clock-time">Since ${this.formatTime(this.state.clockInTime)}</p>
              ` : ''}
            </div>
            
            <div class="tracking-status-row">
              <div class="gps-status" id="gpsStatus">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="10" r="3"/>
                  <path d="M12 21.7C17.3 17 20 13 20 10a8 8 0 1 0-16 0c0 3 2.7 7 8 11.7z"/>
                </svg>
                <span>Acquiring GPS...</span>
              </div>
              <div class="battery-status" id="batteryStatus">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="1" y="6" width="18" height="12" rx="2" ry="2"/>
                  <line x1="23" y1="10" x2="23" y2="14"/>
                </svg>
                <span>--%</span>
              </div>
            </div>
          </div>

          <!-- Work Mode Selector (shown only before clock-in) -->
          ${this.state.status === 'not_clocked_in' ? `
          <div class="work-mode-selector card">
            <p class="work-mode-label">Select Work Mode:</p>
            <div class="work-mode-options">
              <button class="work-mode-btn ${this.state.workMode === 'office' ? 'active' : ''}" data-mode="office">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="3" width="18" height="18" rx="2"/>
                  <path d="M9 3v18M15 3v18M3 9h18M3 15h18"/>
                </svg>
                Office
              </button>
              <button class="work-mode-btn ${this.state.workMode === 'wfh' ? 'active' : ''}" data-mode="wfh">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M3 12l9-9 9 9"/>
                  <path d="M5 10v10h14V10"/>
                </svg>
                WFH
              </button>
              <button class="work-mode-btn ${this.state.workMode === 'field' ? 'active' : ''}" data-mode="field">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 22s-8-4.5-8-11.8A8 8 0 0 1 12 2a8 8 0 0 1 8 8.2c0 7.3-8 11.8-8 11.8z"/>
                  <circle cx="12" cy="10" r="3"/>
                </svg>
                Field
              </button>
            </div>
          </div>
          ` : ''}

          <!-- Action Buttons -->
          <div class="action-buttons">
            ${this.state.status === 'not_clocked_in' ? `
              <button id="clockInBtn" class="btn btn-primary btn-lg btn-full action-btn">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/>
                  <polyline points="12 6 12 12 16 14"/>
                </svg>
                Clock In
              </button>
            ` : ''}

            ${this.state.status === 'clocked_in' ? `
              <button id="startBreakBtn" class="btn btn-warning btn-lg btn-full action-btn">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="10" y1="8" x2="10" y2="16"/>
                  <line x1="14" y1="8" x2="14" y2="16"/>
                </svg>
                Start Break
              </button>
              <button id="clockOutBtn" class="btn btn-danger btn-lg btn-full action-btn">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="15" y1="9" x2="9" y2="15"/>
                  <line x1="9" y1="9" x2="15" y2="15"/>
                </svg>
                Clock Out
              </button>
            ` : ''}

            ${this.state.status === 'on_break' ? `
              <button id="endBreakBtn" class="btn btn-success btn-lg btn-full action-btn">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/>
                  <polygon points="10 8 16 12 10 16 10 8"/>
                </svg>
                End Break
              </button>
            ` : ''}

            ${this.state.status === 'clocked_out' ? `
              <div class="day-completed-notice">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/>
                  <polyline points="16 10 11 15 8 12"/>
                </svg>
                <p>Day Completed</p>
                <span class="clock-out-time">Clocked out at ${this.state.clockOutTime ? this.formatTime(this.state.clockOutTime) : '--:--'}</span>
              </div>
            ` : ''}

            ${this.state.isClockedIn && !this.state.isOnBreak && !this.state.hasActiveJourney ? `
              <button id="startJourneyBtn" class="btn btn-secondary btn-lg btn-full action-btn">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M12 8v8M8 12h8"/>
                </svg>
                Start Journey
              </button>
            ` : ''}

            ${this.state.hasActiveJourney ? `
              <button id="endJourneyBtn" class="btn btn-warning btn-lg btn-full action-btn">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="6" y="6" width="12" height="12" rx="2"/>
                </svg>
                End Journey
              </button>
            ` : ''}
          </div>

          <!-- Time Breakdown Stats -->
          <div class="time-breakdown card">
            <div class="breakdown-row">
              <div class="breakdown-item">
                <span class="breakdown-label">Login Time</span>
                <span class="breakdown-value" id="totalLoginTime">--:--</span>
              </div>
              <div class="breakdown-item">
                <span class="breakdown-label">Breaks</span>
                <span class="breakdown-value break-time" id="totalBreakTime">0:00</span>
              </div>
              <div class="breakdown-item highlight">
                <span class="breakdown-label">Worked</span>
                <span class="breakdown-value" id="netWorkedTime">--:--</span>
              </div>
            </div>
          </div>

          <!-- Quick Stats -->
          <div class="stats-grid">
            <div class="card stat-card">
              <p class="stat-label">Journeys Today</p>
              <p class="stat-value" id="todayJourneys">0</p>
            </div>
          </div>
        </main>

        <!-- Selfie Modal -->
        <div id="selfieModal" class="modal" style="display: none;">
          <div class="modal-content">
            <h3 class="modal-title" id="selfieTitle">Take Selfie for Clock In</h3>
            <p class="modal-desc">A photo is required for attendance verification</p>
            
            <div id="selfiePreview" class="selfie-preview" style="display: none;">
              <img id="selfieImage" src="" alt="Selfie preview" />
            </div>
            
            <div class="modal-actions">
              <button id="takeSelfieBtn" class="btn btn-primary btn-lg btn-full">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                  <circle cx="12" cy="13" r="4"/>
                </svg>
                Take Photo
              </button>
              <button id="confirmSelfieBtn" class="btn btn-primary btn-lg btn-full" style="display: none;">
                Confirm & Submit
              </button>
              <button id="retakeSelfieBtn" class="btn btn-outline btn-full" style="display: none;">
                Retake Photo
              </button>
              <button id="cancelSelfieBtn" class="btn btn-outline btn-full">
                Cancel
              </button>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  private attachEventListeners(): void {
    document.getElementById('hamburgerBtn')?.addEventListener('click', () => getSideDrawer().open());
    document.getElementById('logoutBtn')?.addEventListener('click', () => this.handleLogout());
    document.getElementById('clockInBtn')?.addEventListener('click', () => this.showSelfieModal('clockIn'));
    document.getElementById('clockOutBtn')?.addEventListener('click', () => this.showSelfieModal('clockOut'));
    document.getElementById('startBreakBtn')?.addEventListener('click', () => this.showBreakModal());
    document.getElementById('endBreakBtn')?.addEventListener('click', () => this.handleEndBreak());
    document.getElementById('startJourneyBtn')?.addEventListener('click', () => this.handleStartJourney());
    document.getElementById('endJourneyBtn')?.addEventListener('click', () => this.handleEndJourney());
    document.getElementById('takeSelfieBtn')?.addEventListener('click', () => this.handleTakeSelfie());
    document.getElementById('cancelSelfieBtn')?.addEventListener('click', () => this.hideSelfieModal());
    document.getElementById('retakeSelfieBtn')?.addEventListener('click', () => this.handleRetakeSelfie());
    document.getElementById('confirmSelfieBtn')?.addEventListener('click', () => this.handleConfirmSelfie());

    // Work mode selector buttons
    document.querySelectorAll('.work-mode-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const mode = (e.currentTarget as HTMLElement).dataset.mode as 'office' | 'wfh' | 'field';
        this.state.workMode = mode;
        document.querySelectorAll('.work-mode-btn').forEach(b => b.classList.remove('active'));
        (e.currentTarget as HTMLElement).classList.add('active');
      });
    });

    this.gpsStatusInterval = setInterval(() => {
      if (this.state.isClockedIn) {
        this.updateGpsStatus();
      }
    }, 5000);
    
    this.hoursWorkedInterval = setInterval(() => {
      if (this.state.isClockedIn) {
        this.updateLiveHoursWorked();
      }
    }, 60000);
    
    this.attendancePollInterval = setInterval(() => {
      this.refreshStatus();
    }, 30000);
    
    this.initialUpdateTimeout = setTimeout(() => this.updateLiveHoursWorked(), 2000);
  }
  
  private updateLiveHoursWorked(): void {
    const loginTimeEl = document.getElementById('totalLoginTime');
    const breakTimeEl = document.getElementById('totalBreakTime');
    const workedTimeEl = document.getElementById('netWorkedTime');
    
    if (!this.state.isClockedIn) {
      if (loginTimeEl) loginTimeEl.textContent = '--:--';
      if (breakTimeEl) breakTimeEl.textContent = '0:00';
      if (workedTimeEl) workedTimeEl.textContent = '--:--';
      return;
    }
    
    // Calculate live hours from clock-in time
    if (this.state.clockInTime) {
      const clockIn = new Date(this.state.clockInTime);
      if (!isNaN(clockIn.getTime())) {
        const now = new Date();
        const diffMs = now.getTime() - clockIn.getTime();
        
        if (diffMs > 0) {
          // Total login time (clock-in to now)
          const totalLoginMinutes = Math.floor(diffMs / 60000);
          const loginHours = Math.floor(totalLoginMinutes / 60);
          const loginMins = totalLoginMinutes % 60;
          
          // Break time from backend
          const breakMinutes = this.state.totalBreakMinutes || 0;
          const breakHours = Math.floor(breakMinutes / 60);
          const breakMins = breakMinutes % 60;
          
          // Net worked time (login - breaks)
          const netMinutes = Math.max(0, totalLoginMinutes - breakMinutes);
          const netHours = Math.floor(netMinutes / 60);
          const netMins = netMinutes % 60;
          
          if (loginTimeEl) loginTimeEl.textContent = `${loginHours}:${loginMins.toString().padStart(2, '0')}`;
          if (breakTimeEl) breakTimeEl.textContent = `${breakHours}:${breakMins.toString().padStart(2, '0')}`;
          if (workedTimeEl) workedTimeEl.textContent = `${netHours}:${netMins.toString().padStart(2, '0')}`;
        } else {
          if (loginTimeEl) loginTimeEl.textContent = '0:00';
          if (breakTimeEl) breakTimeEl.textContent = '0:00';
          if (workedTimeEl) workedTimeEl.textContent = '0:00';
        }
        return;
      }
    }
    
    if (loginTimeEl) loginTimeEl.textContent = '0:00';
    if (breakTimeEl) breakTimeEl.textContent = '0:00';
    if (workedTimeEl) workedTimeEl.textContent = '0:00';
  }

  private getStatusClass(): string {
    switch (this.state.status) {
      case 'clocked_in': return 'active';
      case 'on_break': return 'on-break';
      case 'clocked_out': return 'completed';
      default: return 'inactive';
    }
  }

  private getStatusText(): string {
    switch (this.state.status) {
      case 'clocked_in': return 'Clocked In';
      case 'on_break': return 'On Break';
      case 'clocked_out': return 'Day Completed';
      default: return 'Not Clocked In';
    }
  }

  private showBreakModal(): void {
    const breakOptions = this.state.breakTypes.map(bt => 
      `<button class="break-type-btn btn btn-outline" data-break-type="${bt.code}" data-break-id="${bt.id}">${bt.name}</button>`
    ).join('');

    const modal = document.createElement('div');
    modal.id = 'breakModal';
    modal.className = 'modal';
    modal.style.display = 'flex';
    modal.innerHTML = `
      <div class="modal-content">
        <h3 class="modal-title">Select Break Type</h3>
        <div class="break-type-options">
          ${breakOptions}
        </div>
        <button id="cancelBreakBtn" class="btn btn-outline btn-full" style="margin-top: 1rem;">Cancel</button>
      </div>
    `;
    document.body.appendChild(modal);

    modal.querySelectorAll('.break-type-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const target = e.currentTarget as HTMLElement;
        const breakType = target.dataset.breakType || 'personal';
        const breakTypeId = parseInt(target.dataset.breakId || '0');
        this.handleStartBreak(breakType, breakTypeId);
        modal.remove();
      });
    });

    modal.querySelector('#cancelBreakBtn')?.addEventListener('click', () => modal.remove());
  }

  private async handleStartBreak(breakType: string, breakTypeId: number): Promise<void> {
    try {
      const normalizedBreakType = breakType.toLowerCase().replace(/[^a-z_]/g, '');
      const validBreakTypes = ['lunch', 'tea', 'personal', 'meeting', 'client_visit', 'travel', 'emergency', 'other'];
      const finalBreakType = validBreakTypes.includes(normalizedBreakType) ? normalizedBreakType : 'personal';
      
      const response = await apiService.post<any>('/staff/attendance/break/start', {
        break_type: finalBreakType,
        break_type_id: breakTypeId || null
      });
      
      if (response.success !== false) {
        // DC Protocol (Jan 28, 2026): Pause GPS tracking during break
        gpsService.setOnBreak(true);
        await this.refreshStatus();
        this.render();
        this.attachEventListeners();
      } else {
        alert((response as any).error || 'Failed to start break');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to start break');
    }
  }

  private async handleEndBreak(): Promise<void> {
    try {
      const response = await apiService.post<any>('/staff/attendance/break/end', {});
      
      if (response.success !== false) {
        // DC Protocol (Jan 28, 2026): Resume GPS tracking after break
        gpsService.setOnBreak(false);
        await this.refreshStatus();
        this.render();
        this.attachEventListeners();
      } else {
        alert((response as any).error || 'Failed to end break');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to end break');
    }
  }

  private pendingSelfieAction: 'clockIn' | 'clockOut' | null = null;
  private capturedSelfie: string | null = null;

  private showSelfieModal(action: 'clockIn' | 'clockOut'): void {
    this.pendingSelfieAction = action;
    this.capturedSelfie = null;
    
    const modal = document.getElementById('selfieModal');
    const title = document.getElementById('selfieTitle');
    
    if (title) {
      title.textContent = action === 'clockIn' ? 'Take Selfie for Clock In' : 'Take Selfie for Clock Out';
    }
    
    // Reset modal state
    document.getElementById('selfiePreview')!.style.display = 'none';
    document.getElementById('takeSelfieBtn')!.style.display = 'block';
    document.getElementById('confirmSelfieBtn')!.style.display = 'none';
    document.getElementById('retakeSelfieBtn')!.style.display = 'none';
    
    if (modal) modal.style.display = 'flex';
  }

  private hideSelfieModal(): void {
    const modal = document.getElementById('selfieModal');
    if (modal) modal.style.display = 'none';
    this.pendingSelfieAction = null;
    this.capturedSelfie = null;
  }

  private async handleTakeSelfie(): Promise<void> {
    const result = await cameraService.takeSelfie();
    
    if (result.success && result.base64) {
      this.capturedSelfie = result.base64;
      
      // Show preview
      const preview = document.getElementById('selfiePreview');
      const image = document.getElementById('selfieImage') as HTMLImageElement;
      
      if (preview && image) {
        image.src = `data:image/jpeg;base64,${result.base64}`;
        preview.style.display = 'block';
      }
      
      // Update buttons
      document.getElementById('takeSelfieBtn')!.style.display = 'none';
      document.getElementById('confirmSelfieBtn')!.style.display = 'block';
      document.getElementById('retakeSelfieBtn')!.style.display = 'block';
    } else {
      alert(result.error || 'Failed to capture photo');
    }
  }

  private handleRetakeSelfie(): void {
    this.capturedSelfie = null;
    document.getElementById('selfiePreview')!.style.display = 'none';
    document.getElementById('takeSelfieBtn')!.style.display = 'block';
    document.getElementById('confirmSelfieBtn')!.style.display = 'none';
    document.getElementById('retakeSelfieBtn')!.style.display = 'none';
  }

  private async handleConfirmSelfie(): Promise<void> {
    if (!this.capturedSelfie || !this.pendingSelfieAction) return;
    
    const confirmBtn = document.getElementById('confirmSelfieBtn') as HTMLButtonElement;
    confirmBtn.disabled = true;
    confirmBtn.textContent = 'Getting GPS...';
    
    // Use getCurrentPosition() to actively fetch GPS (not cached value)
    const location = await gpsService.getCurrentPosition();
    
    if (!location) {
      alert('Unable to get GPS location. Please ensure location services are enabled and try again.');
      confirmBtn.disabled = false;
      confirmBtn.textContent = 'Confirm & Submit';
      return;
    }
    
    confirmBtn.textContent = 'Processing...';
    
    try {
      let response;
      
      if (this.pendingSelfieAction === 'clockIn') {
        response = await apiService.clockIn(
          location.latitude,
          location.longitude,
          location.accuracy_m,
          this.capturedSelfie,
          this.state.workMode
        );
        
        if (response.success !== false) {
          this.state.status = 'clocked_in';
          this.state.isClockedIn = true;
          this.state.isOnBreak = false;
          authService.setClockedIn(true);
          gpsService.setClockedIn(true);
        }
      } else {
        response = await apiService.clockOut(
          location.latitude,
          location.longitude,
          location.accuracy_m,
          this.capturedSelfie
        );
        
        if (response.success !== false) {
          this.state.status = 'clocked_out';
          this.state.isClockedIn = false;
          this.state.isOnBreak = false;
          authService.setClockedIn(false);
          gpsService.setClockedIn(false);
        }
      }
      
      if (response.success !== false) {
        this.hideSelfieModal();
        await this.refreshStatus();
        this.render();
        this.attachEventListeners();
      } else {
        alert(response.error || 'Operation failed');
        confirmBtn.disabled = false;
        confirmBtn.textContent = 'Confirm & Submit';
      }
    } catch (error: any) {
      alert(error.message || 'Operation failed');
      confirmBtn.disabled = false;
      confirmBtn.textContent = 'Confirm & Submit';
    }
  }

  private async handleStartJourney(): Promise<void> {
    const { routerService } = await import('../services/router.service');
    routerService.navigate('journeys');
  }

  private async handleEndJourney(): Promise<void> {
    const { routerService } = await import('../services/router.service');
    routerService.navigate('journeys');
  }

  private async handleLogout(): Promise<void> {
    if (this.state.isClockedIn) {
      const confirm = window.confirm('You are still clocked in. Are you sure you want to logout?');
      if (!confirm) return;
    }
    
    await gpsService.cleanup();
    await authService.logout();
    window.dispatchEvent(new CustomEvent('logout'));
  }

  private updateUI(): void {
    if (this.isDestroyed) return;
    this.render();
    this.attachEventListeners();
  }

  private updateGpsStatus(): void {
    const location = gpsService.getCurrentLocation();
    const trackingStatus = gpsService.getTrackingStatus();
    const gpsStatus = document.getElementById('gpsStatus');
    const batteryStatus = document.getElementById('batteryStatus');
    
    // DC_SESSION_EXPIRY_001: Handle session expiration banner
    this.updateSessionExpirationBanner(trackingStatus.isSessionExpired);
    
    if (gpsStatus) {
      if (location) {
        const quality = gpsService.getAccuracyQuality(location.accuracy_m);
        gpsStatus.innerHTML = `
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${quality.color}" stroke-width="2">
            <circle cx="12" cy="10" r="3"/>
            <path d="M12 21.7C17.3 17 20 13 20 10a8 8 0 1 0-16 0c0 3 2.7 7 8 11.7z"/>
          </svg>
          <span style="color: ${quality.color}">${quality.label} (${Math.round(location.accuracy_m)}m)</span>
        `;
      } else {
        const statusText = trackingStatus.isTracking ? 'Acquiring...' : 'GPS Off';
        const statusColor = trackingStatus.isTracking ? 'var(--warning)' : 'var(--text-muted)';
        gpsStatus.innerHTML = `
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${statusColor}" stroke-width="2">
            <circle cx="12" cy="10" r="3"/>
            <path d="M12 21.7C17.3 17 20 13 20 10a8 8 0 1 0-16 0c0 3 2.7 7 8 11.7z"/>
          </svg>
          <span style="color: ${statusColor}">${statusText}</span>
        `;
      }
    }
    
    if (batteryStatus) {
      const level = trackingStatus.batteryLevel;
      const charging = trackingStatus.isCharging;
      
      if (level !== null) {
        const color = level >= 50 ? '#10b981' : (level >= 25 ? '#f59e0b' : '#ef4444');
        const icon = charging ? 'M13 2L3 14h9l-1 8 10-12h-9l1-8z' : '';
        batteryStatus.innerHTML = `
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2">
            <rect x="1" y="6" width="18" height="12" rx="2" ry="2"/>
            <line x1="23" y1="10" x2="23" y2="14"/>
            ${charging ? `<path d="${icon}" fill="${color}" stroke="none" transform="scale(0.5) translate(6, 6)"/>` : ''}
          </svg>
          <span style="color: ${color}">${level}%${charging ? ' ⚡' : ''}</span>
        `;
      } else {
        batteryStatus.innerHTML = `
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="2">
            <rect x="1" y="6" width="18" height="12" rx="2" ry="2"/>
            <line x1="23" y1="10" x2="23" y2="14"/>
          </svg>
          <span style="color: var(--text-muted)">--%</span>
        `;
      }
    }
  }

  private getInitials(name: string): string {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  }

  private formatTime(isoString: string | null | undefined): string {
    if (!isoString) return '--:--';
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return '--:--';
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  // DC_SESSION_EXPIRY_001: Session expiration banner management
  private updateSessionExpirationBanner(isExpired: boolean): void {
    const existingBanner = document.getElementById('sessionExpiredBanner');
    
    if (isExpired && !existingBanner) {
      // Show session expired banner
      const banner = document.createElement('div');
      banner.id = 'sessionExpiredBanner';
      banner.className = 'session-expired-banner';
      banner.innerHTML = `
        <div class="session-banner-content">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <div class="session-banner-text">
            <strong>Session Expired</strong>
            <span>Data is being saved locally. Tap to re-login.</span>
          </div>
        </div>
        <button id="reAuthBtn" class="re-auth-btn">Login</button>
      `;
      
      // Insert at top of page
      const mainContent = this.container.querySelector('.dashboard-container');
      if (mainContent) {
        mainContent.insertBefore(banner, mainContent.firstChild);
      } else {
        this.container.insertBefore(banner, this.container.firstChild);
      }
      
      // Attach re-auth handler
      const reAuthBtn = document.getElementById('reAuthBtn');
      reAuthBtn?.addEventListener('click', () => this.handleReAuthenticate());
      
      banner.addEventListener('click', (e) => {
        if ((e.target as HTMLElement).id !== 'reAuthBtn') {
          this.handleReAuthenticate();
        }
      });
    } else if (!isExpired && existingBanner) {
      // Remove banner when session is restored
      existingBanner.remove();
    }
  }

  private async handleReAuthenticate(): Promise<void> {
    // DC_SESSION_EXPIRY_001: Show re-authentication modal
    this.showReAuthModal();
  }

  private showReAuthModal(): void {
    // Check if modal already exists
    if (document.getElementById('reAuthModal')) return;

    const modal = document.createElement('div');
    modal.id = 'reAuthModal';
    modal.className = 'modal';
    modal.style.display = 'flex';
    modal.innerHTML = `
      <div class="modal-content" style="max-width: 320px;">
        <div class="modal-header">
          <h3>Session Expired</h3>
          <button class="modal-close" id="closeReAuthModal">&times;</button>
        </div>
        <div class="modal-body">
          <p style="margin-bottom: 16px; color: var(--text-secondary);">
            Your session has expired. Please enter your password to continue.
          </p>
          <div class="form-group">
            <label>Password</label>
            <input type="password" id="reAuthPassword" class="form-control" placeholder="Enter your password" autocomplete="current-password">
          </div>
          <p id="reAuthError" class="form-error" style="display: none; color: var(--danger); margin-top: 8px;"></p>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" id="cancelReAuth">Cancel</button>
          <button class="btn btn-primary" id="submitReAuth">Login</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    // Focus password field
    setTimeout(() => {
      const passwordInput = document.getElementById('reAuthPassword') as HTMLInputElement;
      passwordInput?.focus();
    }, 100);

    // Event listeners
    document.getElementById('closeReAuthModal')?.addEventListener('click', () => modal.remove());
    document.getElementById('cancelReAuth')?.addEventListener('click', () => modal.remove());
    document.getElementById('submitReAuth')?.addEventListener('click', () => this.submitReAuth());
    
    // Enter key to submit
    document.getElementById('reAuthPassword')?.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.submitReAuth();
    });
  }

  private async submitReAuth(): Promise<void> {
    const passwordInput = document.getElementById('reAuthPassword') as HTMLInputElement;
    const errorEl = document.getElementById('reAuthError');
    const submitBtn = document.getElementById('submitReAuth') as HTMLButtonElement;
    
    if (!passwordInput || !this.user) return;

    const password = passwordInput.value;
    if (!password) {
      if (errorEl) {
        errorEl.textContent = 'Please enter your password';
        errorEl.style.display = 'block';
      }
      return;
    }

    // Disable button during request
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Logging in...';
    }

    try {
      // Re-authenticate with stored user ID
      const userId = this.user.employee_id || this.user.id || this.user.mnr_id;
      const portal = this.user.portal || 'staff';
      
      const result = await authService.loginWithPassword(userId, password, portal);
      
      if (result.success) {
        // Success - remove modal and banner
        document.getElementById('reAuthModal')?.remove();
        gpsService.resetSessionExpiredState();
        
        // Sync any queued data
        const { offlineQueueService } = await import('../services/offline-queue.service');
        const status = offlineQueueService.getStatus();
        if (status.pendingCount > 0) {
          console.log('[Dashboard] Re-auth successful, syncing queued data...');
        }
        
        // Refresh status
        await this.refreshStatus();
      } else {
        if (errorEl) {
          errorEl.textContent = result.error || 'Login failed. Please try again.';
          errorEl.style.display = 'block';
        }
      }
    } catch (error: any) {
      if (errorEl) {
        errorEl.textContent = error.message || 'An error occurred';
        errorEl.style.display = 'block';
      }
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Login';
      }
    }
  }
}
