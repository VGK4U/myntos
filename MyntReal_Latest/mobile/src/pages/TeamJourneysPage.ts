/**
 * Staff Team Journeys Page
 * DC Protocol: DC_MOBILE_STAFF_TEAM_JOURNEY_001
 * View team member journeys (for managers)
 * DC Protocol (Jan 28, 2026): Added journey detail modal with map and playback
 * DC Protocol (Feb 02, 2026): Enhanced with stops, battery, offline periods, playback, Open in Maps
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import { LeafletJourneyMap } from '../components/LeafletJourneyMap';
import { routerService } from '../services/router.service';

interface TeamJourneyAPI {
  id: number;
  employee_name: string;
  employee_id_code?: string;
  employee_code?: string;
  purpose: string;
  purpose_description: string;
  start_address?: string;
  start_location?: string;
  end_address?: string | null;
  end_location?: string | null;
  start_time: string;
  end_time: string | null;
  total_distance_km?: number;
  distance_km?: number;
  status: string;
  transport_mode: string;
  reimbursement_amount?: number;
}

interface TeamJourney {
  id: number;
  employee_name: string;
  emp_code: string;
  purpose: string;
  start_location: string;
  end_location: string | null;
  start_time: string;
  end_time: string | null;
  distance_km: number;
  status: string;
  transport_mode: string;
  reimbursement_amount?: number;
}

interface OfflinePeriod {
  startTime: Date;
  endTime: Date;
  durationMinutes: number;
  reason: string;
  startIndex: number;
  endIndex: number;
}

function mapApiToJourney(api: TeamJourneyAPI): TeamJourney {
  return {
    id: api.id,
    employee_name: api.employee_name || 'Staff Member',
    emp_code: api.employee_id_code || api.employee_code || '',
    purpose: api.purpose_description || api.purpose || 'General Field Visit',
    start_location: api.start_address || api.start_location || 'Start Location',
    end_location: api.end_address || api.end_location || null,
    start_time: api.start_time,
    end_time: api.end_time,
    distance_km: api.total_distance_km ?? api.distance_km ?? 0,
    status: (api.status || 'unknown').toLowerCase(),
    transport_mode: api.transport_mode || 'bike',
    reimbursement_amount: api.reimbursement_amount ?? 0
  };
}

export class TeamJourneysPage {
  private container: HTMLElement;
  private activeJourneys: TeamJourney[] = [];
  private dateJourneys: TeamJourney[] = [];
  private loading: boolean = true;
  private activeLoading: boolean = false;
  private dateLoading: boolean = false;
  private selectedDate: string = '';
  private expandedJourneyId: number | null = null;
  private leafletMap: LeafletJourneyMap | null = null;
  private addressCache: Map<string, string> = new Map();
  
  private playbackState: { playing: boolean; index: number; interval: any; speed: number } = {
    playing: false,
    index: 0,
    interval: null,
    speed: 2
  };
  private currentTrackPoints: any[] = [];
  private pendingTimers: ReturnType<typeof setTimeout>[] = [];

  constructor(container: HTMLElement) {
    this.container = container;
    this.selectedDate = new Date().toISOString().split('T')[0];
  }

  async init(): Promise<void> {
    this.render();
    await this.loadTeamJourneys();
  }

  private async loadTeamJourneys(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      // DC Protocol: Parallel fetch - Active journeys irrespective of date + Date-filtered journeys
      const [activeRes, dateRes] = await Promise.all([
        apiService.get<any>('/staff/journeys/team?status=in_progress'),
        apiService.get<any>(`/staff/journeys/team?start_date=${this.selectedDate}&end_date=${this.selectedDate}`)
      ]);

      if (activeRes && activeRes.success && activeRes.data) {
        const activeApis: TeamJourneyAPI[] = activeRes.data.journeys || activeRes.data || [];
        this.activeJourneys = activeApis.map(mapApiToJourney);
      } else {
        this.activeJourneys = [];
      }

      if (dateRes && dateRes.success && dateRes.data) {
        const dateApis: TeamJourneyAPI[] = dateRes.data.journeys || dateRes.data || [];
        this.dateJourneys = dateApis.map(mapApiToJourney);
      } else {
        this.dateJourneys = [];
      }
    } catch (error) {
      console.error('[TeamJourneys] Failed to load journeys:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private async loadActiveJourneysOnly(): Promise<void> {
    this.activeLoading = true;
    try {
      const activeRes = await apiService.get<any>('/staff/journeys/team?status=in_progress');
      if (activeRes && activeRes.success && activeRes.data) {
        const activeApis: TeamJourneyAPI[] = activeRes.data.journeys || activeRes.data || [];
        this.activeJourneys = activeApis.map(mapApiToJourney);
      } else {
        this.activeJourneys = [];
      }
    } catch (err) {
      console.error('[TeamJourneys] Failed to refresh active journeys:', err);
    }
    this.activeLoading = false;
    this.updateContent();
  }

  private async loadDateJourneysOnly(): Promise<void> {
    this.dateLoading = true;
    try {
      const dateRes = await apiService.get<any>(`/staff/journeys/team?start_date=${this.selectedDate}&end_date=${this.selectedDate}`);
      if (dateRes && dateRes.success && dateRes.data) {
        const dateApis: TeamJourneyAPI[] = dateRes.data.journeys || dateRes.data || [];
        this.dateJourneys = dateApis.map(mapApiToJourney);
      } else {
        this.dateJourneys = [];
      }
    } catch (err) {
      console.error('[TeamJourneys] Failed to load date journeys:', err);
    }
    this.dateLoading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Team Journeys', showBack: true })}
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>

      <!-- DC Protocol (Jan 28, 2026): Journey Detail Modal -->
      <div id="journeyDetailModal" class="modal" style="display: none;">
        <div class="modal-content journey-detail-modal">
          <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <h3 style="margin: 0; font-size: 18px;">Journey Details</h3>
            <button class="close-btn" id="closeJourneyModal" style="background: none; border: none; font-size: 24px; color: var(--text-primary); cursor: pointer;">&times;</button>
          </div>
          <div class="modal-body" id="journeyDetailBody" style="max-height: 70vh; overflow-y: auto;">
            <div class="loading-state">Loading...</div>
          </div>
        </div>
      </div>

      <!-- DC Protocol (Apr 2026): Force Stop Journey Modal -->
      <div id="forceStopModal" style="
        display: none; position: fixed; inset: 0; z-index: 1000;
        background: rgba(0,0,0,0.6); align-items: center; justify-content: center;
      ">
        <div style="
          background: #1e1e2e; border: 1px solid rgba(220,38,38,0.4);
          border-radius: 16px; padding: 24px; margin: 20px; max-width: 380px; width: 100%;
        ">
          <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 16px;">
            <span style="font-size: 22px;">🛑</span>
            <h3 style="margin: 0; color: #fca5a5; font-size: 17px;">Force Stop Journey</h3>
          </div>
          <p id="forceStopEmployeeName" style="color: rgba(255,255,255,0.7); font-size: 13px; margin: 0 0 16px 0;"></p>
          <label style="color: rgba(255,255,255,0.6); font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; display: block; margin-bottom: 6px;">
            Reason (required)
          </label>
          <textarea id="forceStopReason" rows="3" placeholder="Enter reason for force stopping this journey..." style="
            width: 100%; background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.15);
            border-radius: 8px; padding: 10px; color: #fff; font-size: 14px;
            resize: none; box-sizing: border-box; font-family: inherit;
          "></textarea>
          <div style="display: flex; gap: 10px; margin-top: 16px;">
            <button id="forceStopCancelBtn" style="
              flex: 1; padding: 12px; border: 1px solid rgba(255,255,255,0.2);
              border-radius: 10px; background: transparent; color: rgba(255,255,255,0.7);
              font-size: 14px; cursor: pointer;
            ">Cancel</button>
            <button id="forceStopConfirmBtn" style="
              flex: 1; padding: 12px; border: none;
              border-radius: 10px; background: #dc2626; color: #fff;
              font-size: 14px; font-weight: 600; cursor: pointer;
            ">Force Stop</button>
          </div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: 'Team Journeys', showBack: true });
    this.attachModalCloseHandler();
    this.attachForceStopModalHandlers();
  }

  private currentForceStopJourneyId: number | null = null;

  private attachForceStopModalHandlers(): void {
    document.getElementById('forceStopCancelBtn')?.addEventListener('click', () => {
      this.closeForceStopModal();
    });

    document.getElementById('forceStopConfirmBtn')?.addEventListener('click', async () => {
      await this.submitForceStop();
    });

    document.getElementById('forceStopModal')?.addEventListener('click', (e) => {
      if ((e.target as HTMLElement).id === 'forceStopModal') {
        this.closeForceStopModal();
      }
    });
  }

  private openForceStopModal(journeyId: number, employeeName: string): void {
    this.currentForceStopJourneyId = journeyId;
    const modal = document.getElementById('forceStopModal');
    const nameEl = document.getElementById('forceStopEmployeeName');
    const reasonEl = document.getElementById('forceStopReason') as HTMLTextAreaElement;
    if (nameEl) nameEl.textContent = `Force stopping journey for: ${employeeName}`;
    if (reasonEl) reasonEl.value = '';
    if (modal) modal.style.display = 'flex';
  }

  private closeForceStopModal(): void {
    const modal = document.getElementById('forceStopModal');
    if (modal) modal.style.display = 'none';
    this.currentForceStopJourneyId = null;
  }

  private async submitForceStop(): Promise<void> {
    const journeyId = this.currentForceStopJourneyId;
    if (!journeyId) return;

    const reasonEl = document.getElementById('forceStopReason') as HTMLTextAreaElement;
    const reason = reasonEl?.value?.trim() || '';
    if (!reason) {
      alert('Please enter a reason for force stopping this journey.');
      return;
    }

    const confirmBtn = document.getElementById('forceStopConfirmBtn') as HTMLButtonElement;
    if (confirmBtn) { confirmBtn.disabled = true; confirmBtn.textContent = 'Stopping...'; }

    try {
      const response = await apiService.post<any>(`/staff/journeys/${journeyId}/force-stop`, { reason });
      if (response.success) {
        this.closeForceStopModal();
        alert('Journey force stopped successfully.');
        await this.loadTeamJourneys();
      } else {
        alert(response.error || 'Failed to force stop journey. You may not have permission.');
      }
    } catch (err: any) {
      alert('Network error. Please try again.');
    } finally {
      if (confirmBtn) { confirmBtn.disabled = false; confirmBtn.textContent = 'Force Stop'; }
    }
  }

  private attachModalCloseHandler(): void {
    document.getElementById('closeJourneyModal')?.addEventListener('click', () => {
      this.closeModal();
    });

    document.getElementById('journeyDetailModal')?.addEventListener('click', (e) => {
      if ((e.target as HTMLElement).classList.contains('modal')) {
        this.closeModal();
      }
    });
  }

  private closeModal(): void {
    const modal = document.getElementById('journeyDetailModal');
    if (modal) modal.style.display = 'none';
    this.stopPlaybackInterval();
    if (this.leafletMap) {
      this.leafletMap.destroy();
      this.leafletMap = null;
    }
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = `
        <div style="text-align: center; padding: 48px 16px; color: rgba(255,255,255,0.6);">
          <i class="fas fa-circle-notch fa-spin" style="font-size: 28px; color: #6366f1; margin-bottom: 12px;"></i>
          <div style="font-size: 14px; font-weight: 500;">Loading Team Journeys...</div>
        </div>
      `;
      return;
    }

    const todayStr = new Date().toISOString().split('T')[0];
    const yestDate = new Date();
    yestDate.setDate(yestDate.getDate() - 1);
    const yestStr = yestDate.toISOString().split('T')[0];

    const isToday = this.selectedDate === todayStr;
    const isYesterday = this.selectedDate === yestStr;

    const totalKm = this.dateJourneys.reduce((sum, j) => sum + (j.distance_km || 0), 0);
    const totalAmount = this.dateJourneys.reduce((sum, j) => sum + (j.reimbursement_amount || 0), 0);
    const activeCount = this.activeJourneys.length;

    content.innerHTML = `
      <!-- Segmented Navigation Pill -->
      <div style="display: flex; background: rgba(30,41,59,0.7); padding: 4px; border-radius: 12px; margin-bottom: 16px; border: 1px solid rgba(255,255,255,0.08);">
        <button id="switchMyJourneysBtn" style="flex: 1; padding: 8px 12px; border: none; border-radius: 8px; background: transparent; color: #94a3b8; font-size: 13px; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px;">
          <i class="fas fa-user"></i> My Journeys
        </button>
        <button id="switchTeamJourneysBtn" style="flex: 1; padding: 8px 12px; border: none; border-radius: 8px; background: #4f46e5; color: #fff; font-size: 13px; font-weight: 600; cursor: default; display: flex; align-items: center; justify-content: center; gap: 6px; box-shadow: 0 2px 6px rgba(79,70,229,0.4);">
          <i class="fas fa-users"></i> Team Journeys
          ${activeCount > 0 ? `<span style="background: #22c55e; color: #fff; font-size: 10px; padding: 1px 6px; border-radius: 10px; font-weight: 700;">${activeCount}</span>` : ''}
        </button>
      </div>

      <!-- Modern 4-Card KPI Strip -->
      <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 20px;">
        <div style="background: rgba(30,41,59,0.85); border: 1px solid ${activeCount > 0 ? 'rgba(34,197,94,0.4)' : 'rgba(255,255,255,0.08)'}; border-radius: 12px; padding: 12px 6px; text-align: center;">
          <div style="display: flex; align-items: center; justify-content: center; gap: 5px;">
            ${activeCount > 0 ? `<span style="width: 7px; height: 7px; border-radius: 50%; background: #22c55e; box-shadow: 0 0 6px #22c55e;"></span>` : ''}
            <span style="font-size: 18px; font-weight: 800; color: ${activeCount > 0 ? '#4ade80' : '#94a3b8'};">${activeCount}</span>
          </div>
          <div style="font-size: 10px; color: #94a3b8; font-weight: 600; text-transform: uppercase; margin-top: 2px;">Active Now</div>
        </div>

        <div style="background: rgba(30,41,59,0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 12px 6px; text-align: center;">
          <span style="font-size: 18px; font-weight: 800; color: #60a5fa;">${this.dateJourneys.length}</span>
          <div style="font-size: 10px; color: #94a3b8; font-weight: 600; text-transform: uppercase; margin-top: 2px;">Trips</div>
        </div>

        <div style="background: rgba(30,41,59,0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 12px 6px; text-align: center;">
          <span style="font-size: 18px; font-weight: 800; color: #a78bfa;">${totalKm.toFixed(1)}</span>
          <div style="font-size: 10px; color: #94a3b8; font-weight: 600; text-transform: uppercase; margin-top: 2px;">KM Total</div>
        </div>

        <div style="background: rgba(30,41,59,0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 12px 6px; text-align: center;">
          <span style="font-size: 18px; font-weight: 800; color: #34d399;">₹${totalAmount.toFixed(0)}</span>
          <div style="font-size: 10px; color: #94a3b8; font-weight: 600; text-transform: uppercase; margin-top: 2px;">Claims</div>
        </div>
      </div>

      <!-- SECTION 1: 🟢 LIVE ACTIVE JOURNEYS (Always Visible Irrespective of Date) -->
      <div style="margin-bottom: 24px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <h4 style="margin: 0; font-size: 14.5px; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 8px;">
            <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #22c55e; box-shadow: 0 0 8px #22c55e;"></span>
            Live Active Journeys
            <span style="font-size: 11px; background: rgba(34,197,94,0.15); color: #4ade80; border: 1px solid rgba(34,197,94,0.3); padding: 1px 7px; border-radius: 10px; font-weight: 600;">
              ${activeCount} Active
            </span>
          </h4>
          <button id="refreshActiveBtn" style="background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12); color: #94a3b8; border-radius: 8px; padding: 4px 10px; font-size: 11px; cursor: pointer; display: flex; align-items: center; gap: 5px;">
            <i class="fas fa-sync-alt ${this.activeLoading ? 'fa-spin' : ''}"></i> Refresh
          </button>
        </div>

        ${activeCount > 0 ? `
          <div class="active-journeys-list" style="display: flex; flex-direction: column; gap: 12px;">
            ${this.activeJourneys.map(j => this.renderJourneyCard(j, true)).join('')}
          </div>
        ` : `
          <div style="padding: 16px 20px; background: rgba(30,41,59,0.5); border: 1px dashed rgba(255,255,255,0.12); border-radius: 12px; text-align: center;">
            <div style="font-size: 20px; margin-bottom: 4px;">✨</div>
            <div style="font-size: 13px; font-weight: 600; color: #e2e8f0;">No team members currently on journey</div>
            <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">All team members are off-field or trips have completed.</div>
          </div>
        `}
      </div>

      <!-- SECTION 2: 📅 DATE-WISE JOURNEY HISTORY & CLAIMS -->
      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
          <h4 style="margin: 0; font-size: 14.5px; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 7px;">
            <i class="fas fa-calendar-alt" style="color: #6366f1; font-size: 13px;"></i>
            Date-Wise Journeys
          </h4>
          <div style="display: flex; gap: 6px;">
            <button id="quickTodayBtn" style="padding: 4px 10px; border-radius: 6px; font-size: 11.5px; font-weight: 600; cursor: pointer; border: 1px solid ${isToday ? '#4f46e5' : 'rgba(255,255,255,0.15)'}; background: ${isToday ? '#4f46e5' : 'rgba(255,255,255,0.06)'}; color: ${isToday ? '#fff' : '#94a3b8'};">
              Today
            </button>
            <button id="quickYesterdayBtn" style="padding: 4px 10px; border-radius: 6px; font-size: 11.5px; font-weight: 600; cursor: pointer; border: 1px solid ${isYesterday ? '#4f46e5' : 'rgba(255,255,255,0.15)'}; background: ${isYesterday ? '#4f46e5' : 'rgba(255,255,255,0.06)'}; color: ${isYesterday ? '#fff' : '#94a3b8'};">
              Yesterday
            </button>
          </div>
        </div>

        <!-- Custom Styled Date Input Bar -->
        <div style="background: rgba(30,41,59,0.7); border: 1px solid rgba(255,255,255,0.12); border-radius: 10px; padding: 8px 12px; display: flex; align-items: center; gap: 10px; margin-bottom: 14px;">
          <i class="fas fa-calendar-day" style="color: #818cf8; font-size: 15px;"></i>
          <div style="flex: 1;">
            <input type="date" id="datePicker" value="${this.selectedDate}" style="background: transparent; border: none; color: #f8fafc; font-size: 13.5px; font-weight: 600; width: 100%; outline: none; cursor: pointer;">
          </div>
          <span style="font-size: 11.5px; color: #94a3b8; font-weight: 500;">${this.formatDate(this.selectedDate)}</span>
        </div>

        <!-- List for Date-Wise Journeys -->
        ${this.dateLoading ? `
          <div style="text-align: center; padding: 24px; color: rgba(255,255,255,0.5);">
            <i class="fas fa-circle-notch fa-spin me-2"></i>Loading journeys for ${this.formatDate(this.selectedDate)}...
          </div>
        ` : this.dateJourneys.length > 0 ? `
          <div class="date-journeys-list" style="display: flex; flex-direction: column; gap: 12px;">
            ${this.dateJourneys.map(j => this.renderJourneyCard(j, false)).join('')}
          </div>
        ` : `
          <div style="padding: 24px 16px; background: rgba(30,41,59,0.5); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; text-align: center;">
            <div style="font-size: 24px; margin-bottom: 6px;">🚗</div>
            <div style="font-size: 13.5px; font-weight: 600; color: #e2e8f0;">No journeys recorded on this date</div>
            <div style="font-size: 11px; color: #94a3b8; margin-top: 3px;">Try picking another date using the filter above.</div>
          </div>
        `}
      </div>
    `;

    this.attachEventListeners();
  }

  private renderJourneyCard(journey: TeamJourney, isLive: boolean): string {
    const isExpanded = this.expandedJourneyId === journey.id;
    const time = this.formatTime(journey.start_time);
    const purposeText = this.formatPurposeText(journey.purpose);
    const transportText = this.formatTransportIconText(journey.transport_mode);

    let elapsedText = '';
    if (isLive && journey.start_time) {
      const diffMs = Math.max(0, Date.now() - new Date(journey.start_time).getTime());
      const totalMins = Math.floor(diffMs / 60000);
      const hours = Math.floor(totalMins / 60);
      const mins = totalMins % 60;
      elapsedText = hours > 0 ? `${hours}h ${mins}m elapsed` : `${mins}m elapsed`;
    }

    const cardBorder = isLive 
      ? 'border: 1px solid rgba(34,197,94,0.45); background: rgba(22,101,52,0.12);' 
      : (isExpanded ? 'border: 1px solid #4f46e5; background: rgba(79,70,229,0.15);' : 'border: 1px solid rgba(255,255,255,0.08); background: rgba(30,41,59,0.85);');

    return `
      <div class="journey-card-container" data-journey-id="${journey.id}" style="border-radius: 12px; overflow: hidden;">
        <div class="journey-card" data-journey-id="${journey.id}" style="${cardBorder} border-radius: ${isExpanded ? '12px 12px 0 0' : '12px'}; padding: 14px 16px; cursor: pointer; transition: all 0.2s;">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
            <div>
              <div style="font-size: 14px; font-weight: 700; color: #fff;">${journey.employee_name}</div>
              <div style="font-size: 11px; color: #94a3b8; font-weight: 500; margin-top: 1px;">
                ${journey.emp_code ? `<span style="background: rgba(255,255,255,0.08); padding: 1px 6px; border-radius: 4px;">${journey.emp_code}</span>` : ''}
                ${isLive ? `<span style="color: #4ade80; margin-left: 6px; font-weight: 600;">● Started ${time}${elapsedText ? ` (${elapsedText})` : ''}</span>` : ''}
              </div>
            </div>

            <div style="display: flex; align-items: center; gap: 8px;">
              ${isLive ? `
                <span style="background: rgba(34,197,94,0.2); color: #4ade80; border: 1px solid rgba(34,197,94,0.4); font-size: 10.5px; font-weight: 700; padding: 2px 8px; border-radius: 12px; display: inline-flex; align-items: center; gap: 4px;">
                  <span style="width: 5px; height: 5px; border-radius: 50%; background: #22c55e;"></span> In Progress
                </span>
              ` : `
                <span style="background: rgba(148,163,184,0.15); color: #cbd5e1; border: 1px solid rgba(148,163,184,0.3); font-size: 10.5px; font-weight: 600; padding: 2px 8px; border-radius: 12px;">
                  ${journey.status === 'completed' ? '✓ Completed' : journey.status}
                </span>
              `}
              <i class="fas fa-chevron-down" style="color: rgba(255,255,255,0.4); font-size: 12px; transition: transform 0.25s; ${isExpanded ? 'transform: rotate(180deg);' : ''}"></i>
            </div>
          </div>

          <!-- Route Points Summary -->
          <div style="display: flex; flex-direction: column; gap: 4px; margin-bottom: 10px; font-size: 12.5px;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="color: #22c55e; font-size: 11px;">●</span>
              <span style="color: #cbd5e1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 90%;">${journey.start_location}</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="color: ${journey.end_location ? '#ef4444' : '#f59e0b'}; font-size: 11px;">●</span>
              <span style="color: ${journey.end_location ? '#cbd5e1' : '#f59e0b'}; font-style: ${journey.end_location ? 'normal' : 'italic'}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 90%;">
                ${journey.end_location || 'Trip In Progress...'}
              </span>
            </div>
          </div>

          <!-- Metadata Strip -->
          <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 6px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.06); font-size: 11.5px; color: #94a3b8;">
            <div style="display: flex; align-items: center; gap: 10px;">
              <span><i class="far fa-clock me-1"></i>${time}</span>
              <span>${transportText}</span>
              <span style="color: #fff; font-weight: 600;"><i class="fas fa-route me-1 text-primary"></i>${journey.distance_km?.toFixed(1) || '0.0'} km</span>
            </div>
            <span style="background: rgba(99,102,241,0.15); color: #818cf8; padding: 1px 7px; border-radius: 4px; font-weight: 600; font-size: 10.5px;">
              ${purposeText}
            </span>
          </div>

          <!-- Action Button for Live Journeys -->
          ${isLive ? `
            <div style="margin-top: 10px; padding-top: 8px; border-top: 1px dashed rgba(220,38,38,0.3);">
              <button
                class="force-stop-btn"
                data-journey-id="${journey.id}"
                data-employee-name="${journey.employee_name}"
                style="
                  width: 100%; padding: 7px 12px; background: rgba(220,38,38,0.15);
                  border: 1px solid rgba(220,38,38,0.4); border-radius: 8px;
                  color: #fca5a5; font-size: 12px; font-weight: 600; cursor: pointer;
                  display: flex; align-items: center; justify-content: center; gap: 6px;
                "
              ><i class="fas fa-hand-paper" style="font-size: 11px;"></i> Force Stop Journey</button>
            </div>
          ` : ''}
        </div>

        <!-- Inline Detail Drawer -->
        <div class="journey-inline-detail" style="display: ${isExpanded ? 'block' : 'none'};" id="journey-detail-${journey.id}">
          <div style="text-align: center; padding: 20px; color: rgba(255,255,255,0.5);">
            <i class="fas fa-spinner fa-spin me-2"></i> Loading journey details & route...
          </div>
        </div>
      </div>
    `;
  }

  private formatPurposeText(purpose: string): string {
    if (!purpose) return 'Field Visit';
    const clean = purpose.replace(/_/g, ' ').trim();
    return clean.charAt(0).toUpperCase() + clean.slice(1);
  }

  private formatTransportIconText(mode: string): string {
    const m = (mode || '').toLowerCase();
    if (m.includes('bike') || m === 'motorcycle') return '🏍️ Bike';
    if (m.includes('car')) return '🚗 Car';
    if (m.includes('electric') || m.includes('ebike')) return '⚡ E-Bike';
    if (m.includes('company')) return '🏢 Company Vehicle';
    if (m.includes('cart')) return '🛻 Cart';
    if (m.includes('bus') || m.includes('transport')) return '🚌 Transport';
    if (m.includes('walk')) return '🚶 Walking';
    return '🚗 ' + (mode ? mode.charAt(0).toUpperCase() + mode.slice(1) : 'Vehicle');
  }

  private attachEventListeners(): void {
    // Segmented toggle
    document.getElementById('switchMyJourneysBtn')?.addEventListener('click', () => {
      routerService.navigate('journeys');
    });

    // Refresh active button
    document.getElementById('refreshActiveBtn')?.addEventListener('click', async () => {
      await this.loadActiveJourneysOnly();
    });

    // Quick date pills
    document.getElementById('quickTodayBtn')?.addEventListener('click', async () => {
      const today = new Date().toISOString().split('T')[0];
      if (this.selectedDate !== today) {
        this.selectedDate = today;
        await this.loadDateJourneysOnly();
      }
    });

    document.getElementById('quickYesterdayBtn')?.addEventListener('click', async () => {
      const yestDate = new Date();
      yestDate.setDate(yestDate.getDate() - 1);
      const yest = yestDate.toISOString().split('T')[0];
      if (this.selectedDate !== yest) {
        this.selectedDate = yest;
        await this.loadDateJourneysOnly();
      }
    });

    // Date picker input
    document.getElementById('datePicker')?.addEventListener('change', async (e) => {
      const val = (e.target as HTMLInputElement).value;
      if (val && val !== this.selectedDate) {
        this.selectedDate = val;
        await this.loadDateJourneysOnly();
      }
    });

    // Journey cards expand click
    const journeyCards = this.container.querySelectorAll('.journey-card[data-journey-id]');
    journeyCards.forEach(card => {
      card.addEventListener('click', () => {
        const journeyId = (card as HTMLElement).dataset.journeyId;
        if (journeyId) {
          this.toggleJourneyDetail(parseInt(journeyId));
        }
      });
    });

    // Force stop buttons
    const forceStopBtns = this.container.querySelectorAll('.force-stop-btn');
    forceStopBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const journeyId = (btn as HTMLElement).dataset.journeyId;
        const employeeName = (btn as HTMLElement).dataset.employeeName || 'this employee';
        if (journeyId) {
          this.openForceStopModal(parseInt(journeyId), employeeName);
        }
      });
    });
  }

  private async toggleJourneyDetail(journeyId: number): Promise<void> {
    if (this.expandedJourneyId === journeyId) {
      this.expandedJourneyId = null;
      this.stopPlaybackInterval();
      this.updateContent();
    } else {
      this.expandedJourneyId = journeyId;
      this.updateContent();
      await this.loadJourneyDetailInline(journeyId);
    }
  }

  private async loadJourneyDetailInline(journeyId: number): Promise<void> {
    const container = document.getElementById(`journey-detail-${journeyId}`);
    if (!container) return;

    try {
      const response = await apiService.get<any>(`/staff/journeys/${journeyId}/track-points`);
      
      if (response.success && response.data) {
        const journey = response.data.journey || response.data;
        const trackPoints = response.data.track_points || journey.track_points || [];
        this.currentTrackPoints = trackPoints;
        
        let duration = '--';
        let durationMins = 0;
        if (journey.start_time) {
          const startTimeMs = new Date(journey.start_time).getTime();
          const endTimeMs = journey.end_time ? new Date(journey.end_time).getTime() : Date.now();
          if (!isNaN(startTimeMs) && !isNaN(endTimeMs) && endTimeMs >= startTimeMs) {
            const diffMs = endTimeMs - startTimeMs;
            durationMins = Math.round(diffMs / 60000);
            duration = durationMins >= 60 ? `${Math.floor(durationMins / 60)}h ${durationMins % 60}m` : `${durationMins}m`;
          }
        } else if (journey.total_duration_minutes) {
          durationMins = Math.round(journey.total_duration_minutes);
          duration = durationMins >= 60 ? `${Math.floor(durationMins / 60)}h ${durationMins % 60}m` : `${durationMins}m`;
        }

        let avgSpeed = Math.round(journey.average_speed_kmh || 0);
        if (avgSpeed === 0 && durationMins > 0 && (journey.total_distance_km || 0) > 0) {
          avgSpeed = Math.round((journey.total_distance_km || 0) / (durationMins / 60));
        }

        const stops = this.detectStops(trackPoints);
        const offlinePeriods = this.detectOfflinePeriods(trackPoints);
        const batteryStats = this.getJourneyBatteryStats(trackPoints);
        const batteryRange = this.formatBatteryRange(trackPoints);
        const batteryColorClass = this.getBatteryColorClass(batteryStats);
        
        // DC_GUARD_001: Handle empty trackPoints gracefully
        if (!trackPoints || trackPoints.length === 0) {
          container.innerHTML = `
            <div style="padding: 24px; background: rgba(30,41,59,0.98); border: 1px solid #4f46e5; border-top: none; border-radius: 0 0 12px 12px; text-align: center;">
              <div style="font-size: 48px; margin-bottom: 12px;">📍</div>
              <div style="font-size: 16px; color: #fff; font-weight: 600; margin-bottom: 8px;">No GPS Data Available</div>
              <div style="font-size: 13px; color: #8892b0;">This journey has no recorded GPS track points.</div>
              <div style="font-size: 13px; color: #8892b0; margin-top: 4px;">Possible reasons: GPS was disabled, journey in progress, or data capture failed.</div>
            </div>
          `;
          return;
        }
        
        const startPoint = trackPoints[0];
        const endPoint = trackPoints[trackPoints.length - 1];

        container.innerHTML = `
          <div style="padding: 16px; background: rgba(30,41,59,0.98); border: 1px solid #4f46e5; border-top: none; border-radius: 0 0 12px 12px;">
            <!-- Stats Grid -->
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 16px;">
              <div style="background: rgba(22,33,62,0.8); padding: 12px 8px; border-radius: 8px; text-align: center;">
                <div style="font-size: 18px; font-weight: bold; color: #fff;">${(journey.total_distance_km || 0).toFixed(2)}</div>
                <div style="font-size: 10px; color: #8892b0; text-transform: uppercase;">KM</div>
              </div>
              <div style="background: rgba(22,33,62,0.8); padding: 12px 8px; border-radius: 8px; text-align: center;">
                <div style="font-size: 18px; font-weight: bold; color: #fff;">${duration}</div>
                <div style="font-size: 10px; color: #8892b0; text-transform: uppercase;">Duration</div>
              </div>
              <div style="background: rgba(22,33,62,0.8); padding: 12px 8px; border-radius: 8px; text-align: center;">
                <div style="font-size: 18px; font-weight: bold; color: #4ade80;">₹${(journey.reimbursement_amount || 0).toFixed(0)}</div>
                <div style="font-size: 10px; color: #8892b0; text-transform: uppercase;">Amount</div>
              </div>
              <div style="background: rgba(22,33,62,0.8); padding: 12px 8px; border-radius: 8px; text-align: center;">
                <div style="font-size: 18px; font-weight: bold; color: #fff;">${stops.length}</div>
                <div style="font-size: 10px; color: #8892b0; text-transform: uppercase;">Stops</div>
              </div>
            </div>
            
            <!-- Second Stats Row -->
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 16px;">
              <div style="background: rgba(22,33,62,0.8); padding: 12px 8px; border-radius: 8px; text-align: center;">
                <div style="font-size: 18px; font-weight: bold; color: #fff;">${trackPoints.length}</div>
                <div style="font-size: 10px; color: #8892b0; text-transform: uppercase;">GPS Pts</div>
              </div>
              <div style="background: rgba(22,33,62,0.8); padding: 12px 8px; border-radius: 8px; text-align: center;">
                <div style="font-size: 18px; font-weight: bold; color: #fff;">${avgSpeed}</div>
                <div style="font-size: 10px; color: #8892b0; text-transform: uppercase;">Avg km/h</div>
              </div>
              <div style="background: rgba(22,33,62,0.8); padding: 12px 8px; border-radius: 8px; text-align: center;">
                <div style="font-size: 18px; font-weight: bold; color: #fff;">${Math.round(journey.max_speed_kmh || 0)}</div>
                <div style="font-size: 10px; color: #8892b0; text-transform: uppercase;">Max km/h</div>
              </div>
              <div style="background: rgba(22,33,62,0.8); padding: 12px 8px; border-radius: 8px; text-align: center; ${batteryColorClass}">
                <div style="font-size: 16px; font-weight: bold; color: ${batteryStats.min !== null && batteryStats.min < 20 ? '#ef4444' : batteryStats.min !== null && batteryStats.min < 50 ? '#f59e0b' : '#4ade80'};">${batteryRange}</div>
                <div style="font-size: 10px; color: #8892b0; text-transform: uppercase;">Battery %</div>
              </div>
            </div>
            
            <!-- Info Grid -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px;">
              <div><span style="font-size: 11px; color: #8892b0; text-transform: uppercase;">Company</span><div style="color: #fff; font-size: 14px;">${journey.company_name || 'N/A'}</div></div>
              <div><span style="font-size: 11px; color: #8892b0; text-transform: uppercase;">Transport</span><div style="color: #fff; font-size: 14px;">${this.getTransportIcon(journey.transport_mode)} ${this.formatTransportMode(journey.transport_mode)}</div></div>
            </div>
            
            <!-- Route Points Section -->
            <div style="margin-bottom: 16px;">
              <h5 style="margin: 0 0 12px 0; font-size: 14px; color: #fff; font-weight: 600;">Route Points (${stops.length} stops)</h5>
              <div style="display: flex; flex-direction: column; gap: 10px;">
                <!-- Start Point -->
                <div style="display: flex; gap: 12px; align-items: flex-start;">
                  <div style="width: 28px; height: 28px; background: #4ade80; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 14px; flex-shrink: 0;">▶</div>
                  <div style="flex: 1;">
                    <span style="font-weight: 600; color: #fff; display: block;">Start Point</span>
                    <span class="stop-address-start" style="font-size: 13px; color: #64d2ff; display: block;">${startPoint?.address || this.formatCoords(startPoint)}</span>
                    <span style="font-size: 12px; color: #8892b0;">${this.formatTime(journey.start_time)}${typeof startPoint?.battery_percentage === 'number' ? ` • 🔋${startPoint.battery_percentage}%` : ''}</span>
                  </div>
                </div>
                
                <!-- Stops -->
                ${stops.map((stop: any, i: number) => {
                  const stopPoint = trackPoints[stop.startIndex];
                  const battery = stopPoint?.battery_percentage;
                  const hasBattery = typeof battery === 'number';
                  return `
                  <div style="display: flex; gap: 12px; align-items: flex-start;">
                    <div style="width: 28px; height: 28px; background: #f59e0b; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 14px; flex-shrink: 0;">⏸</div>
                    <div style="flex: 1;">
                      <span style="font-weight: 600; color: #fff; display: block;">Stop ${i + 1} <span style="color: #8892b0; font-weight: normal;">(${this.formatStopDuration(stop.durationMinutes)})</span></span>
                      <span class="stop-address-${i}" style="font-size: 13px; color: #64d2ff; display: block;">${stop.address || this.formatCoords(stopPoint)}</span>
                      ${hasBattery ? `<span style="font-size: 12px; color: #8892b0;">🔋${battery}%</span>` : ''}
                    </div>
                  </div>
                `}).join('')}
                
                <!-- End Point -->
                <div style="display: flex; gap: 12px; align-items: flex-start;">
                  <div style="width: 28px; height: 28px; background: #ef4444; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 14px; flex-shrink: 0;">🏁</div>
                  <div style="flex: 1;">
                    <span style="font-weight: 600; color: #fff; display: block;">End Point</span>
                    <span class="stop-address-end" style="font-size: 13px; color: #64d2ff; display: block;">${endPoint?.address || this.formatCoords(endPoint)}</span>
                    <span style="font-size: 12px; color: #8892b0;">${journey.end_time ? this.formatTime(journey.end_time) : 'In Progress'}${typeof endPoint?.battery_percentage === 'number' ? ` • 🔋${endPoint.battery_percentage}%` : ''}</span>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Offline Periods Section -->
            ${offlinePeriods.length > 0 ? `
            <div style="margin-bottom: 16px;">
              <h5 style="margin: 0 0 12px 0; font-size: 14px; color: #fff; font-weight: 600;">⚠️ Offline Periods (${offlinePeriods.length})</h5>
              <div style="display: flex; flex-direction: column; gap: 8px;">
                ${offlinePeriods.map((period, i) => `
                  <div style="display: flex; gap: 12px; align-items: center; background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.3); border-radius: 8px; padding: 10px;">
                    <div style="width: 28px; height: 28px; background: rgba(239,68,68,0.3); border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 14px; flex-shrink: 0;">📵</div>
                    <div style="flex: 1;">
                      <span style="font-weight: 600; color: #ef4444; display: block;">${this.formatOfflineDuration(period.durationMinutes)} offline</span>
                      <span style="font-size: 12px; color: #f87171;">${this.formatTime(period.startTime.toISOString())} - ${this.formatTime(period.endTime.toISOString())}</span>
                      <span style="font-size: 11px; color: #8892b0; display: block;">${period.reason}</span>
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>
            ` : ''}
            
            <!-- Playback Controls -->
            ${trackPoints.length >= 2 ? `
            <div style="margin-bottom: 16px;">
              <h5 style="margin: 0 0 12px 0; font-size: 14px; color: #fff; font-weight: 600;">🎬 Route Playback</h5>
              <div style="background: rgba(22,33,62,0.8); border-radius: 8px; padding: 12px;">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                  <button id="playPauseBtn-${journeyId}" style="width: 40px; height: 40px; border-radius: 50%; background: #4f46e5; border: none; color: #fff; font-size: 16px; cursor: pointer; display: flex; align-items: center; justify-content: center;">▶</button>
                  <button id="resetBtn-${journeyId}" style="width: 36px; height: 36px; border-radius: 50%; background: rgba(255,255,255,0.1); border: none; color: #fff; font-size: 14px; cursor: pointer;">↺</button>
                  <input type="range" id="playbackSlider-${journeyId}" min="0" max="${trackPoints.length - 1}" value="0" style="flex: 1; height: 6px; cursor: pointer;">
                  <select id="playbackSpeed-${journeyId}" style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 4px; color: #fff; padding: 4px 8px; font-size: 12px;">
                    <option value="1">1x</option>
                    <option value="2" selected>2x</option>
                    <option value="4">4x</option>
                    <option value="8">8x</option>
                  </select>
                </div>
                <div id="playbackInfo-${journeyId}" style="text-align: center; font-size: 12px; color: #8892b0;">
                  Point 1 / ${trackPoints.length}
                </div>
              </div>
            </div>
            ` : ''}
            
            <!-- Map Section -->
            <div id="teamJourneyMapInline-${journeyId}" style="height: 250px; border-radius: 8px; overflow: hidden; margin-bottom: 16px;"></div>
            
            <!-- Open in Maps Buttons -->
            <div style="display: flex; gap: 8px; margin-bottom: 16px;">
              <button id="openGoogleMaps-${journeyId}" style="flex: 1; padding: 12px; border-radius: 8px; background: #4285f4; color: #fff; border: none; cursor: pointer; font-size: 14px; font-weight: 500;">
                📍 Open Route in Google Maps
              </button>
            </div>
            <div style="display: flex; gap: 8px;">
              <button id="openStartMaps-${journeyId}" style="flex: 1; padding: 10px; border-radius: 8px; background: rgba(74,222,128,0.2); color: #4ade80; border: 1px solid #4ade80; cursor: pointer; font-size: 12px;">
                Start Location
              </button>
              <button id="openEndMaps-${journeyId}" style="flex: 1; padding: 10px; border-radius: 8px; background: rgba(239,68,68,0.2); color: #ef4444; border: 1px solid #ef4444; cursor: pointer; font-size: 12px;">
                End Location
              </button>
            </div>
          </div>
        `;

        // Attach event listeners
        this.attachPlaybackListeners(journeyId, trackPoints);
        this.attachMapOpenListeners(journeyId, startPoint, endPoint, trackPoints);
        
        // Load Leaflet map
        if (trackPoints.length >= 2) {
          setTimeout(() => {
            if (this.leafletMap) {
              this.leafletMap.destroy();
            }
            this.leafletMap = new LeafletJourneyMap({
              containerId: `teamJourneyMapInline-${journeyId}`,
              trackPoints: trackPoints.map((tp: any) => ({
                latitude: tp.latitude,
                longitude: tp.longitude,
                accuracy_m: tp.accuracy_m,
                timestamp: tp.timestamp,
                address: tp.address || '',
                battery_percentage: tp.battery_percentage
              })),
              stops: stops.map((s: any) => ({
                address: s.address || '',
                durationMinutes: s.durationMinutes,
                startIndex: s.startIndex
              })),
              hidePlaybackControls: true
            });
            this.leafletMap.mount();
            
            // Load addresses
            setTimeout(() => {
              this.loadRoutePointAddresses(trackPoints, stops, journeyId);
            }, 200);
          }, 100);
        }
      }
    } catch (error) {
      console.error('[TeamJourneys] Failed to load journey detail:', error);
      container.innerHTML = '<div style="padding: 20px; text-align: center; color: #dc2626;">Failed to load details</div>';
    }
  }

  private attachPlaybackListeners(journeyId: number, trackPoints: any[]): void {
    const playPauseBtn = document.getElementById(`playPauseBtn-${journeyId}`);
    const resetBtn = document.getElementById(`resetBtn-${journeyId}`);
    const slider = document.getElementById(`playbackSlider-${journeyId}`) as HTMLInputElement;
    const speedSelect = document.getElementById(`playbackSpeed-${journeyId}`) as HTMLSelectElement;

    if (playPauseBtn) {
      playPauseBtn.addEventListener('click', () => this.togglePlayback(journeyId, trackPoints));
    }
    if (resetBtn) {
      resetBtn.addEventListener('click', () => this.resetPlayback(journeyId, trackPoints));
    }
    if (slider) {
      slider.addEventListener('input', () => {
        this.playbackState.index = parseInt(slider.value);
        this.updatePlaybackInfo(journeyId, trackPoints.length);
        if (this.leafletMap) {
          this.leafletMap.setPlaybackIndex(this.playbackState.index);
        }
      });
    }
    if (speedSelect) {
      speedSelect.addEventListener('change', () => {
        this.playbackState.speed = parseInt(speedSelect.value);
        if (this.playbackState.playing) {
          this.stopPlaybackInterval();
          this.startPlaybackInterval(journeyId, trackPoints);
        }
      });
    }
  }

  private attachMapOpenListeners(journeyId: number, startPoint: any, endPoint: any, trackPoints: any[]): void {
    document.getElementById(`openGoogleMaps-${journeyId}`)?.addEventListener('click', () => {
      this.openFullRouteInMaps(trackPoints);
    });
    document.getElementById(`openStartMaps-${journeyId}`)?.addEventListener('click', () => {
      if (startPoint?.latitude && startPoint?.longitude) {
        this.openLocationInMaps(startPoint.latitude, startPoint.longitude, 'Start Location');
      }
    });
    document.getElementById(`openEndMaps-${journeyId}`)?.addEventListener('click', () => {
      if (endPoint?.latitude && endPoint?.longitude) {
        this.openLocationInMaps(endPoint.latitude, endPoint.longitude, 'End Location');
      }
    });
  }

  private togglePlayback(journeyId: number, trackPoints: any[]): void {
    const btn = document.getElementById(`playPauseBtn-${journeyId}`);
    if (this.playbackState.playing) {
      this.stopPlaybackInterval();
      if (btn) btn.textContent = '▶';
    } else {
      this.startPlaybackInterval(journeyId, trackPoints);
      if (btn) btn.textContent = '⏸';
    }
    this.playbackState.playing = !this.playbackState.playing;
  }

  private startPlaybackInterval(journeyId: number, trackPoints: any[]): void {
    const interval = 500 / this.playbackState.speed;
    this.playbackState.interval = setInterval(() => {
      if (this.playbackState.index < trackPoints.length - 1) {
        this.playbackState.index++;
        const slider = document.getElementById(`playbackSlider-${journeyId}`) as HTMLInputElement;
        if (slider) slider.value = String(this.playbackState.index);
        this.updatePlaybackInfo(journeyId, trackPoints.length);
        if (this.leafletMap) {
          this.leafletMap.setPlaybackIndex(this.playbackState.index);
        }
      } else {
        this.stopPlaybackInterval();
        const btn = document.getElementById(`playPauseBtn-${journeyId}`);
        if (btn) btn.textContent = '▶';
        this.playbackState.playing = false;
      }
    }, interval);
  }

  private stopPlaybackInterval(): void {
    if (this.playbackState.interval) {
      clearInterval(this.playbackState.interval);
      this.playbackState.interval = null;
    }
  }

  private resetPlayback(journeyId: number, trackPoints: any[]): void {
    this.stopPlaybackInterval();
    this.playbackState.index = 0;
    this.playbackState.playing = false;
    const btn = document.getElementById(`playPauseBtn-${journeyId}`);
    if (btn) btn.textContent = '▶';
    const slider = document.getElementById(`playbackSlider-${journeyId}`) as HTMLInputElement;
    if (slider) slider.value = '0';
    this.updatePlaybackInfo(journeyId, trackPoints.length);
    if (this.leafletMap) {
      this.leafletMap.setPlaybackIndex(0);
    }
  }

  private updatePlaybackInfo(journeyId: number, total: number): void {
    const infoEl = document.getElementById(`playbackInfo-${journeyId}`);
    if (infoEl) {
      const point = this.currentTrackPoints[this.playbackState.index];
      const time = point?.timestamp ? this.formatTime(point.timestamp) : '--:--';
      const battery = typeof point?.battery_percentage === 'number' ? ` | 🔋${point.battery_percentage}%` : '';
      infoEl.textContent = `Point ${this.playbackState.index + 1} / ${total} | ${time}${battery}`;
    }
  }

  private openFullRouteInMaps(trackPoints: any[]): void {
    if (trackPoints.length < 2) return;
    
    const start = trackPoints[0];
    const end = trackPoints[trackPoints.length - 1];
    
    // Build waypoints (sample every 10th point for up to 10 waypoints)
    const waypointIndices: number[] = [];
    if (trackPoints.length > 2) {
      const step = Math.max(1, Math.floor((trackPoints.length - 2) / 8));
      for (let i = step; i < trackPoints.length - 1 && waypointIndices.length < 8; i += step) {
        waypointIndices.push(i);
      }
    }
    
    const waypoints = waypointIndices.map(i => `${trackPoints[i].latitude},${trackPoints[i].longitude}`).join('|');
    
    let url = `https://www.google.com/maps/dir/?api=1&origin=${start.latitude},${start.longitude}&destination=${end.latitude},${end.longitude}&travelmode=driving`;
    if (waypoints) {
      url += `&waypoints=${waypoints}`;
    }
    
    window.open(url, '_blank');
  }

  private openLocationInMaps(lat: number, lng: number, name: string): void {
    const url = `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;
    window.open(url, '_blank');
  }

  private async showJourneyDetail(journeyId: number): Promise<void> {
    const modal = document.getElementById('journeyDetailModal');
    const body = document.getElementById('journeyDetailBody');
    
    if (!modal || !body) return;
    
    modal.style.display = 'flex';
    body.innerHTML = '<div class="loading-state">Loading journey details...</div>';

    try {
      const response = await apiService.get<any>(`/staff/journeys/${journeyId}/track-points`);
      
      if (response.success && response.data) {
        const journey = response.data.journey || response.data;
        const trackPoints = response.data.track_points || journey.track_points || [];
        
        let duration = '--';
        if (journey.start_time && journey.end_time) {
          const startDate = new Date(journey.start_time);
          const endDate = new Date(journey.end_time);
          const diffMs = endDate.getTime() - startDate.getTime();
          const durationMins = Math.round(diffMs / 60000);
          const hours = Math.floor(durationMins / 60);
          const mins = durationMins % 60;
          duration = hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
        } else if (journey.total_duration_minutes) {
          const durationMins = Math.round(journey.total_duration_minutes);
          const hours = Math.floor(durationMins / 60);
          const mins = durationMins % 60;
          duration = hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
        } else if (journey.start_time) {
          const startDate = new Date(journey.start_time);
          const diffMs = Math.max(0, Date.now() - startDate.getTime());
          const durationMins = Math.round(diffMs / 60000);
          const hours = Math.floor(durationMins / 60);
          const mins = durationMins % 60;
          duration = hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
        }

        const startAddress = trackPoints[0]?.address || journey.start_location || '';
        const endAddress = trackPoints[trackPoints.length - 1]?.address || journey.end_location || '';
        
        const stops = this.detectStops(trackPoints);
        const ratePerKm = journey.rate_per_km || 4;

        body.innerHTML = `
          <div class="detail-section">
            <h5 class="detail-title">Journey Info</h5>
            <div class="detail-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
              <div class="detail-item">
                <span class="detail-label" style="font-size: 11px; color: #8892b0; text-transform: uppercase;">Date</span>
                <span class="detail-value" style="font-size: 14px; color: #fff;">${this.formatDate(journey.date || journey.start_time)}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label" style="font-size: 11px; color: #8892b0; text-transform: uppercase;">Status</span>
                <span class="detail-value" style="font-size: 14px; color: #4ade80;">${journey.status || 'completed'}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label" style="font-size: 11px; color: #8892b0; text-transform: uppercase;">Company</span>
                <span class="detail-value" style="font-size: 14px; color: #fff;">${journey.company_name || 'N/A'}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label" style="font-size: 11px; color: #8892b0; text-transform: uppercase;">Transport</span>
                <span class="detail-value" style="font-size: 14px; color: #fff;">${this.getTransportIcon(journey.transport_mode)} ${this.formatTransportMode(journey.transport_mode)} @ ${(journey.transport_mode === 'electric_bike' && ratePerKm == 0.5) ? '₹1/2km' : `₹${ratePerKm}/km`}</span>
              </div>
              <div class="detail-item" style="grid-column: span 2;">
                <span class="detail-label" style="font-size: 11px; color: #8892b0; text-transform: uppercase;">Purpose</span>
                <span class="detail-value" style="font-size: 14px; color: #fff;">📋 ${journey.purpose_description || journey.purpose || 'Other'}</span>
              </div>
            </div>
          </div>

          <div class="detail-section">
            <h5 class="detail-title">Route Summary</h5>
            <div class="route-summary-stats" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;">
              <div class="stat-box" style="background: rgba(22, 33, 62, 0.8); padding: 12px 8px; border-radius: 8px; text-align: center;">
                <span class="stat-value" style="font-size: 18px; font-weight: bold; color: #fff; display: block;">${(journey.total_distance_km || journey.distance_km || 0).toFixed(2)}</span>
                <span class="stat-label" style="font-size: 10px; color: #8892b0; text-transform: uppercase;">KM</span>
              </div>
              <div class="stat-box" style="background: rgba(22, 33, 62, 0.8); padding: 12px 8px; border-radius: 8px; text-align: center;">
                <span class="stat-value" style="font-size: 18px; font-weight: bold; color: #fff; display: block;">${duration}</span>
                <span class="stat-label" style="font-size: 10px; color: #8892b0; text-transform: uppercase;">Duration</span>
              </div>
              <div class="stat-box" style="background: rgba(22, 33, 62, 0.8); padding: 12px 8px; border-radius: 8px; text-align: center;">
                <span class="stat-value" style="font-size: 18px; font-weight: bold; color: #fff; display: block;">${Math.round(journey.average_speed_kmh || 0)}</span>
                <span class="stat-label" style="font-size: 10px; color: #8892b0; text-transform: uppercase;">Avg km/h</span>
              </div>
              <div class="stat-box" style="background: rgba(22, 33, 62, 0.8); padding: 12px 8px; border-radius: 8px; text-align: center;">
                <span class="stat-value" style="font-size: 18px; font-weight: bold; color: #fff; display: block;">${Math.round(journey.max_speed_kmh || 0)}</span>
                <span class="stat-label" style="font-size: 10px; color: #8892b0; text-transform: uppercase;">Max km/h</span>
              </div>
            </div>
            <div class="route-summary-stats" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-top: 8px;">
              <div class="stat-box" style="background: rgba(22, 33, 62, 0.8); padding: 12px 8px; border-radius: 8px; text-align: center;">
                <span class="stat-value" style="font-size: 18px; font-weight: bold; color: #4ade80; display: block;">₹${(journey.reimbursement_amount || 0).toFixed(0)}</span>
                <span class="stat-label" style="font-size: 10px; color: #8892b0; text-transform: uppercase;">${journey.approval_status || 'Pending'}</span>
              </div>
              <div class="stat-box" style="background: rgba(22, 33, 62, 0.8); padding: 12px 8px; border-radius: 8px; text-align: center;">
                <span class="stat-value" style="font-size: 18px; font-weight: bold; color: #fff; display: block;">${trackPoints.length}</span>
                <span class="stat-label" style="font-size: 10px; color: #8892b0; text-transform: uppercase;">GPS Points</span>
              </div>
              <div class="stat-box" style="background: rgba(22, 33, 62, 0.8); padding: 12px 8px; border-radius: 8px; text-align: center;">
                <span class="stat-value" style="font-size: 18px; font-weight: bold; color: #fff; display: block;">${stops.length}</span>
                <span class="stat-label" style="font-size: 10px; color: #8892b0; text-transform: uppercase;">Stops</span>
              </div>
              <div class="stat-box" style="background: rgba(22, 33, 62, 0.8); padding: 12px 8px; border-radius: 8px; text-align: center;">
                <span class="stat-value" style="font-size: 18px; font-weight: bold; color: #fff; display: block;">${this.formatBatteryRange(trackPoints)}</span>
                <span class="stat-label" style="font-size: 10px; color: #8892b0; text-transform: uppercase;">Battery %</span>
              </div>
            </div>
          </div>

          <div class="detail-section">
            <h5 class="detail-title">Route Points</h5>
            <div class="stops-panel" style="display: flex; flex-direction: column; gap: 12px;">
              <div class="stop-item start" style="display: flex; gap: 12px; align-items: flex-start;">
                <div class="stop-icon" style="width: 24px; height: 24px; background: #4ade80; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 12px;">▶</div>
                <div class="stop-info" style="flex: 1;">
                  <span class="stop-label" style="font-weight: 600; color: #fff; display: block;">Start Point</span>
                  <span class="stop-address" style="font-size: 13px; color: #64d2ff; display: block;">${startAddress || this.formatCoords(trackPoints[0])}</span>
                  <span class="stop-time" style="font-size: 12px; color: #8892b0;">${this.formatTime(journey.start_time)}</span>
                </div>
              </div>
              ${stops.map((stop: any, i: number) => {
                const stopPoint = trackPoints[stop.startIndex];
                return `
                <div class="stop-item pause" style="display: flex; gap: 12px; align-items: flex-start;">
                  <div class="stop-icon" style="width: 24px; height: 24px; background: #f59e0b; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 12px;">⏸</div>
                  <div class="stop-info" style="flex: 1;">
                    <span class="stop-label" style="font-weight: 600; color: #fff; display: block;">Stop ${i + 1} <span style="color: #8892b0; font-weight: normal;">(${this.formatStopDuration(stop.durationMinutes)})</span></span>
                    <span class="stop-address" style="font-size: 13px; color: #64d2ff; display: block;">${stop.address || this.formatCoords(stopPoint)}</span>
                  </div>
                </div>
              `}).join('')}
              <div class="stop-item end" style="display: flex; gap: 12px; align-items: flex-start;">
                <div class="stop-icon" style="width: 24px; height: 24px; background: #ef4444; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 12px;">🏁</div>
                <div class="stop-info" style="flex: 1;">
                  <span class="stop-label" style="font-weight: 600; color: #fff; display: block;">End Point</span>
                  <span class="stop-address" style="font-size: 13px; color: #64d2ff; display: block;">${endAddress || this.formatCoords(trackPoints[trackPoints.length - 1])}</span>
                  <span class="stop-time" style="font-size: 12px; color: #8892b0;">${journey.end_time ? this.formatTime(journey.end_time) : 'In Progress'}</span>
                </div>
              </div>
            </div>
          </div>

          <div id="teamJourneyMapSection" class="map-section"></div>
        `;

        if (trackPoints.length >= 2) {
          setTimeout(() => {
            if (this.leafletMap) {
              this.leafletMap.destroy();
            }
            this.leafletMap = new LeafletJourneyMap({
              containerId: 'teamJourneyMapSection',
              trackPoints: trackPoints.map((tp: any) => ({
                latitude: tp.latitude,
                longitude: tp.longitude,
                accuracy_m: tp.accuracy_m,
                timestamp: tp.timestamp,
                address: tp.address || '',
                battery_percentage: tp.battery_percentage
              })),
              stops: stops.map((s: any) => ({
                address: s.address || '',
                durationMinutes: s.durationMinutes,
                startIndex: s.startIndex
              })),
              hidePlaybackControls: true
            });
            this.leafletMap.mount();
            
            setTimeout(() => {
              this.loadRoutePointAddresses(trackPoints, stops);
            }, 200);
          }, 100);
        }
      } else {
        body.innerHTML = `
          <div class="error-state">
            <p>Failed to load journey details</p>
            <p class="error-message">${response.error || 'Unknown error'}</p>
          </div>
        `;
      }
    } catch (error: any) {
      body.innerHTML = `
        <div class="error-state">
          <p>Failed to load journey details</p>
          <p class="error-message">${error.message || 'Unknown error'}</p>
        </div>
      `;
    }
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  private formatTime(timeStr: string): string {
    if (!timeStr) return '--:--';
    const date = new Date(timeStr);
    return date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  }

  private getTransportIcon(mode: string): string {
    const icons: { [key: string]: string } = {
      'bike': '🏍️',
      'car': '🚗',
      'electric_bike': '⚡',
      'company_vehicle': '🏢',
      'cart': '🛻',
      'local_transport': '🚌',
      'others': '🚶'
    };
    return icons[mode] || '🚗';
  }

  private formatTransportMode(mode: string): string {
    const names: { [key: string]: string } = {
      'bike': 'Bike',
      'car': 'Car',
      'electric_bike': 'E-Bike',
      'company_vehicle': 'Company Vehicle',
      'cart': 'Cart',
      'local_transport': 'Local Transport',
      'others': 'Other'
    };
    return names[mode] || mode || 'Bike';
  }

  private detectStops(trackPoints: any[]): any[] {
    if (!trackPoints || trackPoints.length < 2) return [];
    
    const MIN_STOP_DURATION_MS = 2 * 60 * 1000; // 2 minutes minimum
    const MAX_MOVEMENT_THRESHOLD = 0.05; // 50 meters
    const stops: any[] = [];
    
    let stopStartIndex = -1;
    let stopStartTime: Date | null = null;
    
    for (let i = 1; i < trackPoints.length; i++) {
      const prev = trackPoints[i - 1];
      const curr = trackPoints[i];
      
      const dist = this.haversineDistance(
        prev.latitude, prev.longitude,
        curr.latitude, curr.longitude
      );
      
      if (dist < MAX_MOVEMENT_THRESHOLD) {
        if (stopStartIndex === -1) {
          stopStartIndex = i - 1;
          const ts = prev.timestamp || prev.captured_at;
          stopStartTime = ts ? new Date(ts) : null;
        }
      } else {
        if (stopStartIndex !== -1 && stopStartTime) {
          const currTs = curr.timestamp || curr.captured_at;
          const stopEndTime = currTs ? new Date(currTs) : null;
          
          if (stopEndTime) {
            const durationMs = stopEndTime.getTime() - stopStartTime.getTime();
            
            if (durationMs >= MIN_STOP_DURATION_MS) {
              stops.push({
                address: trackPoints[stopStartIndex].address || '',
                durationMinutes: Math.round(durationMs / 60000),
                startIndex: stopStartIndex,
                battery: trackPoints[stopStartIndex].battery_percentage
              });
            }
          }
        }
        stopStartIndex = -1;
        stopStartTime = null;
      }
    }
    
    if (stopStartIndex !== -1 && stopStartTime) {
      const lastPoint = trackPoints[trackPoints.length - 1];
      const lastTs = lastPoint.timestamp || lastPoint.captured_at;
      if (lastTs) {
        const durationMs = new Date(lastTs).getTime() - stopStartTime.getTime();
        if (durationMs >= MIN_STOP_DURATION_MS) {
          stops.push({
            address: trackPoints[stopStartIndex].address || '',
            durationMinutes: Math.round(durationMs / 60000),
            startIndex: stopStartIndex,
            battery: trackPoints[stopStartIndex].battery_percentage
          });
        }
      }
    }
    
    return stops.slice(0, 10);
  }

  private detectOfflinePeriods(trackPoints: any[]): OfflinePeriod[] {
    if (!trackPoints || trackPoints.length < 2) return [];
    
    const MIN_GAP_MS = 60 * 1000; // 1 minute minimum gap to consider offline
    const periods: OfflinePeriod[] = [];
    
    for (let i = 1; i < trackPoints.length; i++) {
      const prev = trackPoints[i - 1];
      const curr = trackPoints[i];
      
      const prevTs = prev.timestamp || prev.captured_at;
      const currTs = curr.timestamp || curr.captured_at;
      
      if (!prevTs || !currTs) continue;
      
      const prevTime = new Date(prevTs);
      const currTime = new Date(currTs);
      const gapMs = currTime.getTime() - prevTime.getTime();
      
      if (gapMs >= MIN_GAP_MS) {
        const durationMins = Math.round(gapMs / 60000);
        let reason = 'GPS signal lost';
        
        if (gapMs > 10 * 60 * 1000) {
          reason = 'Extended offline period (app in background or device off)';
        } else if (gapMs > 5 * 60 * 1000) {
          reason = 'App may have been in background';
        } else if (gapMs > 2 * 60 * 1000) {
          reason = 'Temporary GPS signal loss';
        }
        
        periods.push({
          startTime: prevTime,
          endTime: currTime,
          durationMinutes: durationMins,
          reason: reason,
          startIndex: i - 1,
          endIndex: i
        });
      }
    }
    
    return periods;
  }

  private getJourneyBatteryStats(trackPoints: any[]): { start: number | null; end: number | null; min: number | null } {
    if (!trackPoints || trackPoints.length === 0) {
      return { start: null, end: null, min: null };
    }
    
    const firstBattery = trackPoints[0]?.battery_percentage;
    const lastBattery = trackPoints[trackPoints.length - 1]?.battery_percentage;
    
    const startBattery = (typeof firstBattery === 'number') ? firstBattery : null;
    const endBattery = (typeof lastBattery === 'number') ? lastBattery : null;
    
    const allBatteries = trackPoints
      .map(tp => tp.battery_percentage)
      .filter((b): b is number => b !== null && b !== undefined && typeof b === 'number');
    
    const minBattery = allBatteries.length > 0 ? Math.min(...allBatteries) : null;
    
    return { start: startBattery, end: endBattery, min: minBattery };
  }

  private formatBatteryRange(trackPoints: any[]): string {
    const stats = this.getJourneyBatteryStats(trackPoints);
    if (stats.start === null && stats.end === null) return '--';
    if (stats.start === null) return `→${stats.end}%`;
    if (stats.end === null) return `${stats.start}%→`;
    return `${stats.start}→${stats.end}%`;
  }

  private getBatteryColorClass(stats: { start: number | null; end: number | null; min: number | null }): string {
    if (stats.min === null) return '';
    if (stats.min >= 50) return 'battery-good';
    if (stats.min >= 20) return 'battery-warning';
    return 'battery-danger';
  }

  private formatOfflineDuration(mins: number): string {
    if (mins < 1) return '<1m';
    if (mins < 60) return `${mins}m`;
    const hours = Math.floor(mins / 60);
    const remainingMins = mins % 60;
    return remainingMins > 0 ? `${hours}h ${remainingMins}m` : `${hours}h`;
  }

  private haversineDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
  }

  private formatCoords(point: any): string {
    if (!point) return 'Unknown location';
    const lat = point.latitude?.toFixed(5) || '0.00000';
    const lng = point.longitude?.toFixed(5) || '0.00000';
    return `${lat}, ${lng}`;
  }

  private formatStopDuration(mins: number): string {
    if (mins < 60) return `${mins}m`;
    const hours = Math.floor(mins / 60);
    const remainingMins = mins % 60;
    return remainingMins > 0 ? `${hours}h ${remainingMins}m` : `${hours}h`;
  }

  private async reverseGeocode(lat: number, lng: number): Promise<string> {
    const cacheKey = `${lat.toFixed(4)},${lng.toFixed(4)}`;
    if (this.addressCache.has(cacheKey)) {
      return this.addressCache.get(cacheKey)!;
    }
    
    try {
      const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18`;
      const response = await fetch(url, {
        headers: { 'User-Agent': 'MyntReal-Mobile/1.0' }
      });
      
      if (response.ok) {
        const data = await response.json();
        const address = data.address || {};
        const parts: string[] = [];
        
        for (const key of ['road', 'neighbourhood', 'suburb', 'city', 'town', 'village']) {
          if (address[key]) {
            parts.push(address[key]);
            if (parts.length >= 2) break;
          }
        }
        
        const locationName = parts.length > 0 ? parts.join(', ') : `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
        this.addressCache.set(cacheKey, locationName);
        return locationName;
      }
    } catch (err) {
      console.warn('[DC_GEOCODE] Reverse geocode failed:', err);
    }
    
    return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
  }

  private async loadRoutePointAddresses(trackPoints: any[], stops: any[], journeyId?: number): Promise<void> {
    if (!trackPoints || trackPoints.length === 0) return;
    
    const startPoint = trackPoints[0];
    const endPoint = trackPoints[trackPoints.length - 1];
    
    if (startPoint?.latitude && startPoint?.longitude) {
      const startAddr = await this.reverseGeocode(startPoint.latitude, startPoint.longitude);
      const startEl = journeyId 
        ? document.querySelector(`.stop-address-start`)
        : document.querySelector('.stop-item.start .stop-address');
      if (startEl) startEl.textContent = startAddr;
    }
    
    for (let i = 0; i < stops.length; i++) {
      const stopPoint = trackPoints[stops[i].startIndex];
      if (stopPoint?.latitude && stopPoint?.longitude) {
        await new Promise(resolve => setTimeout(resolve, 300));
        const stopAddr = await this.reverseGeocode(stopPoint.latitude, stopPoint.longitude);
        const stopEl = journeyId 
          ? document.querySelector(`.stop-address-${i}`)
          : document.querySelectorAll('.stop-item.pause .stop-address')[i];
        if (stopEl) stopEl.textContent = stopAddr;
      }
    }
    
    if (endPoint?.latitude && endPoint?.longitude) {
      await new Promise(resolve => setTimeout(resolve, 300));
      const endAddr = await this.reverseGeocode(endPoint.latitude, endPoint.longitude);
      const endEl = journeyId 
        ? document.querySelector(`.stop-address-end`)
        : document.querySelector('.stop-item.end .stop-address');
      if (endEl) endEl.textContent = endAddr;
    }
  }

  cleanup(): void {
    this.pendingTimers.forEach(t => clearTimeout(t));
    this.pendingTimers = [];
    if (this.playbackState.interval) {
      clearInterval(this.playbackState.interval);
      this.playbackState.interval = null;
    }
    this.playbackState.playing = false;
  }
}
