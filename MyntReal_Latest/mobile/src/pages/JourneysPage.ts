/**
 * Journeys Page - Full Workflow
 * DC Protocol: DC_MOBILE_JOURNEYS_001
 * Start Journey → GPS Tracking → End Journey with Photo
 */

import { apiService } from '../services/api.service';
import { gpsService } from '../services/gps.service';
import { PageHeader } from '../components/PageHeader';
import { LeafletJourneyMap } from '../components/LeafletJourneyMap';

interface Journey {
  id: number;
  date: string;
  start_time: string;
  end_time: string | null;
  start_location: string | null;
  end_location: string | null;
  distance_km: number | null;
  transport_mode: string;
  company_name: string;
  status: string;
  reimbursement_amount: number | null;
  purpose: string | null;
}

interface Company {
  id: number;
  name: string;
}

interface ActiveJourney {
  id: number;
  start_time: string;
  company_name: string;
  transport_mode: string;
  purpose: string;
  session_token?: string;
  distance_km?: number;
  stops_count?: number;
  track_points_count?: number;
}

const TRANSPORT_MODES = [
  { id: 'bike', name: 'Bike', icon: '🏍️', rate: 4 },
  { id: 'car', name: 'Car', icon: '🚗', rate: 8 },
  { id: 'electric_bike', name: 'E-Bike', icon: '⚡', rate: 1 },
  { id: 'cart', name: 'Cart', icon: '🛻', rate: 10 },
  { id: 'local_transport', name: 'Local', icon: '🚌', rate: 3 },
  { id: 'others', name: 'Other', icon: '🚶', rate: 2 }
];

const PURPOSES = [
  { id: 'client_visit', name: 'Client Visit', icon: '👥' },
  { id: 'site_inspection', name: 'Site Inspection', icon: '🔍' },
  { id: 'meeting', name: 'Meeting', icon: '🤝' },
  { id: 'delivery', name: 'Delivery', icon: '📦' },
  { id: 'collection', name: 'Collection', icon: '💰' },
  { id: 'other', name: 'Other', icon: '📋' }
];

interface KRAOption {
  id: number;
  template_name: string;
}

interface TaskOption {
  id: number;
  title: string;
}

export class JourneysPage {
  private container: HTMLElement;
  private journeys: Journey[] = [];
  private companies: Company[] = [];
  private activeJourney: ActiveJourney | null = null;
  private loading: boolean = true;
  private currentMonth: Date = new Date();
  private selectedTransport: string = 'bike';
  private selectedPurpose: string = 'client_visit';
  private heartbeatInterval: any = null;
  private myKras: KRAOption[] = [];
  private myTasks: TaskOption[] = [];
  private leafletMap: LeafletJourneyMap | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  cleanup(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
    this.stopPlaybackInterval();
    if (this.leafletMap) {
      this.leafletMap.destroy();
      this.leafletMap = null;
    }
  }

  async init(): Promise<void> {
    this.render();
    await Promise.all([
      this.loadCompanies(),
      this.checkActiveJourney(),
      this.loadJourneys(),
      this.loadMyKras(),
      this.loadMyTasks()
    ]);
  }

  private async loadMyKras(): Promise<void> {
    try {
      const response = await apiService.get<any>('/staff/kra/instances?status=in_progress,pending');
      if (response.success && response.data) {
        const instances = response.data.instances || response.data || [];
        this.myKras = instances.map((kra: any) => ({
          id: kra.id,
          template_name: kra.template_name || kra.title || `KRA #${kra.id}`
        }));
      }
    } catch (error) {
      console.error('[JourneysPage] Failed to load KRAs:', error);
      this.myKras = [];
    }
    this.updateKraSelect();
  }

  private async loadMyTasks(): Promise<void> {
    try {
      const response = await apiService.get<any>('/staff/tasks/assigned-to-me?status=in_progress,pending');
      if (response.success && response.data) {
        const tasks = response.data.tasks || response.data || [];
        this.myTasks = tasks.map((task: any) => ({
          id: task.id,
          title: task.title || `Task #${task.id}`
        }));
      }
    } catch (error) {
      console.error('[JourneysPage] Failed to load tasks:', error);
      this.myTasks = [];
    }
    this.updateTaskSelect();
  }

  private updateKraSelect(): void {
    const select = document.getElementById('kraSelect') as HTMLSelectElement;
    if (!select) return;
    select.innerHTML = '<option value="">-- None --</option>' + 
      this.myKras.map(k => `<option value="${k.id}">${k.template_name}</option>`).join('');
  }

  private updateTaskSelect(): void {
    const select = document.getElementById('taskSelect') as HTMLSelectElement;
    if (!select) return;
    select.innerHTML = '<option value="">-- None --</option>' + 
      this.myTasks.map(t => `<option value="${t.id}">${t.title}</option>`).join('');
  }

  private async loadCompanies(): Promise<void> {
    try {
      const response = await apiService.get<{ companies: Company[] }>('/staff/journeys/companies');
      console.log('[JourneysPage] Companies API response:', response);
      if (response.success && response.data) {
        const companiesData = response.data.companies || response.data;
        this.companies = Array.isArray(companiesData) ? companiesData : [];
        console.log('[JourneysPage] Loaded companies:', this.companies.length);
      } else {
        console.warn('[JourneysPage] Companies API failed:', response.error);
        this.companies = [];
      }
    } catch (error) {
      console.error('[JourneysPage] Failed to load companies:', error);
      this.companies = [];
    }
    this.updateCompanySelect();
  }

  private async checkActiveJourney(): Promise<void> {
    try {
      const response = await apiService.get<any>('/staff/journeys/active');
      console.log('[JourneysPage] Active journey response:', response);
      if (response.success && response.data) {
        const journey = response.data.journey;
        if (journey && journey.id) {
          const storedToken = await apiService.getJourneyToken();
          const todayStr = new Date().toISOString().split('T')[0];
          const journeyDate = journey.start_time ? journey.start_time.split('T')[0] : todayStr;
          const isStale = journeyDate < todayStr;
          this.activeJourney = {
            id: journey.id,
            start_time: journey.start_time,
            company_name: journey.company_name || 'N/A',
            transport_mode: this.formatTransportMode(journey.transport_mode) || 'N/A',
            purpose: this.formatPurpose(journey.purpose) || 'N/A',
            session_token: storedToken || undefined,
            is_stale: isStale,
            stale_date: isStale ? journeyDate : undefined
          } as any;
          console.log('[JourneysPage] Active journey found:', this.activeJourney, 'isStale:', isStale);
          this.startHeartbeat();
        }
      }
    } catch (error) {
      console.error('[JourneysPage] No active journey:', error);
    }
    this.updateUI();
  }

  private formatTransportMode(mode: string | null): string {
    if (!mode) return 'N/A';
    const found = TRANSPORT_MODES.find(t => t.id === mode);
    return found ? found.name : mode;
  }

  private formatPurpose(purpose: string | null): string {
    if (!purpose) return 'N/A';
    const found = PURPOSES.find(p => p.id === purpose);
    return found ? `${found.icon} ${found.name}` : purpose.replace(/_/g, ' ');
  }

  private async loadJourneys(): Promise<void> {
    this.loading = true;
    this.updateList();

    try {
      const year = this.currentMonth.getFullYear();
      const month = this.currentMonth.getMonth() + 1;
      const fromDate = `${year}-${String(month).padStart(2, '0')}-01`;
      const lastDay = new Date(year, month, 0).getDate();
      const toDate = `${year}-${String(month).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`;
      console.log(`[JourneysPage] Loading journeys for ${fromDate} to ${toDate}`);
      
      const response = await apiService.get<{ journeys: Journey[] }>(
        `/staff/journeys/my?start_date=${fromDate}&end_date=${toDate}`
      );
      
      console.log('[JourneysPage] API response:', JSON.stringify(response, null, 2));

      if (response.success && response.data) {
        const data = response.data as any;
        this.journeys = data.journeys || (Array.isArray(data) ? data : []);
        console.log(`[JourneysPage] Loaded ${this.journeys.length} journeys`);
      } else {
        console.warn('[JourneysPage] API failed:', response.error);
        this.journeys = [];
      }
    } catch (error) {
      console.error('[JourneysPage] Failed to load:', error);
      this.journeys = [];
    }

    this.loading = false;
    this.updateList();
  }

  private render(): void {
    const monthName = this.currentMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'My Journeys', showBack: false })}
        
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

        <!-- Journey Stats - Web Parity -->
        <div class="journeys-stats" id="summary">
          <div class="stat-card">
            <div class="stat-icon blue">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                <path d="M2 17l10 5 10-5"/>
                <path d="M2 12l10 5 10-5"/>
              </svg>
            </div>
            <div class="stat-info">
              <div class="stat-value" id="totalJourneys">--</div>
              <div class="stat-label">Journeys</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon purple">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
              </svg>
            </div>
            <div class="stat-info">
              <div class="stat-value" id="totalDistance">--</div>
              <div class="stat-label">Total KM</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon green">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="12" y1="1" x2="12" y2="23"/>
                <path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>
              </svg>
            </div>
            <div class="stat-info">
              <div class="stat-value" id="totalReimbursement">--</div>
              <div class="stat-label">Approved</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon yellow">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
            </div>
            <div class="stat-info">
              <div class="stat-value" id="pendingCount">--</div>
              <div class="stat-label">Pending</div>
            </div>
          </div>
        </div>

        <!-- Active Journey Card -->
        <div class="active-journey-card card" id="activeJourneyCard" style="display: none;">
          <div class="active-header">
            <span class="pulse-dot"></span>
            <span>Journey In Progress</span>
          </div>
          <div class="active-details" id="activeDetails"></div>
          <button class="btn btn-danger btn-block" id="endJourneyBtn">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="6" y="6" width="12" height="12"/>
            </svg>
            End Journey
          </button>
        </div>

        <!-- Start Journey Card -->
        <div class="start-journey-card card" id="startJourneyCard">
          <h4 class="card-title">Start New Journey</h4>
          
          <div class="form-group">
            <label>Company <span class="required">*</span></label>
            <select id="companySelect" class="form-select">
              <option value="">Select Company</option>
            </select>
          </div>

          <div class="form-group">
            <label>Transport Mode</label>
            <div class="transport-options" id="transportOptions">
              ${TRANSPORT_MODES.map(t => `
                <button class="transport-btn ${t.id === this.selectedTransport ? 'active' : ''}" data-mode="${t.id}">
                  <span class="transport-icon">${t.icon}</span>
                  <span class="transport-name">${t.name}</span>
                  <span class="transport-rate">₹${t.rate}/km</span>
                </button>
              `).join('')}
            </div>
          </div>

          <div class="form-group">
            <label>Purpose</label>
            <div class="purpose-options" id="purposeOptions">
              ${PURPOSES.map(p => `
                <button class="purpose-btn ${p.id === this.selectedPurpose ? 'active' : ''}" data-purpose="${p.id}">
                  <span class="purpose-icon">${p.icon}</span>
                  <span class="purpose-name">${p.name}</span>
                </button>
              `).join('')}
            </div>
          </div>

          <div class="form-group">
            <label>Client/Location (Optional)</label>
            <input type="text" id="clientName" class="form-input" placeholder="Enter client or location name">
          </div>

          <div class="form-group">
            <label>Link to KRA (Optional)</label>
            <select id="kraSelect" class="form-select">
              <option value="">-- None --</option>
            </select>
          </div>

          <div class="form-group">
            <label>Link to Task (Optional)</label>
            <select id="taskSelect" class="form-select">
              <option value="">-- None --</option>
            </select>
          </div>

          <div class="form-group">
            <label>Notes (Optional)</label>
            <textarea id="journeyNotes" class="form-textarea" rows="2" placeholder="Brief description"></textarea>
          </div>

          <div class="gps-status" id="gpsStatus">
            <span class="gps-indicator"></span>
            <span>Checking GPS...</span>
          </div>

          <button class="btn btn-success btn-block" id="startJourneyBtn">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            Start Journey
          </button>
        </div>

        <h4 class="section-title">Journey History</h4>
        <div class="list-container" id="journeysList">
          <div class="loading-state">Loading...</div>
        </div>
      </div>

      <!-- End Journey Modal -->
      <div class="modal-overlay" id="endJourneyModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Complete Journey</h4>
            <button class="modal-close" id="closeEndModal">&times;</button>
          </div>
          <div class="modal-body">
            <p>Upload a photo to confirm your destination:</p>
            <div class="photo-upload-area" id="photoUploadArea">
              <input type="file" id="journeyPhoto" accept="image/*" capture="environment" style="display: none;">
              <div class="upload-placeholder" id="uploadPlaceholder">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                  <circle cx="8.5" cy="8.5" r="1.5"/>
                  <polyline points="21 15 16 10 5 21"/>
                </svg>
                <span>Tap to capture photo</span>
              </div>
              <img id="photoPreview" class="photo-preview" style="display: none;">
            </div>
            <div class="form-group mt-3">
              <label>End Notes (Optional)</label>
              <textarea id="endNotes" class="form-textarea" rows="2" placeholder="Any notes about the journey"></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="cancelEndBtn">Cancel</button>
            <button class="btn btn-success" id="confirmEndBtn">Complete Journey</button>
          </div>
        </div>
      </div>

      <!-- Journey Detail Modal -->
      <div class="modal-overlay" id="journeyDetailModal" style="display: none;">
        <div class="modal-content modal-large">
          <div class="modal-header">
            <h4>Journey Details</h4>
            <button class="modal-close" id="closeDetailModal">&times;</button>
          </div>
          <div class="modal-body" id="journeyDetailBody">
            <div class="loading-state">Loading journey details...</div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="closeDetailBtn">Close</button>
          </div>
        </div>
      </div>
    `;

    this.attachListeners();
    this.checkGPS();
  }

  private attachListeners(): void {
    PageHeader.attachListeners({ title: 'My Journeys', showBack: false });

    document.getElementById('prevMonth')?.addEventListener('click', () => {
      this.currentMonth.setMonth(this.currentMonth.getMonth() - 1);
      this.render();
      this.loadJourneys();
    });

    document.getElementById('nextMonth')?.addEventListener('click', () => {
      this.currentMonth.setMonth(this.currentMonth.getMonth() + 1);
      this.render();
      this.loadJourneys();
    });

    // Transport mode selection
    this.container.querySelectorAll('.transport-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this.selectedTransport = btn.getAttribute('data-mode') || 'bike';
        this.container.querySelectorAll('.transport-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      });
    });

    // Purpose selection
    this.container.querySelectorAll('.purpose-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this.selectedPurpose = btn.getAttribute('data-purpose') || 'other';
        this.container.querySelectorAll('.purpose-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      });
    });

    // Start journey
    document.getElementById('startJourneyBtn')?.addEventListener('click', () => this.startJourney());

    // End journey
    document.getElementById('endJourneyBtn')?.addEventListener('click', () => this.showEndModal());

    // Modal controls
    document.getElementById('closeEndModal')?.addEventListener('click', () => this.hideEndModal());
    document.getElementById('cancelEndBtn')?.addEventListener('click', () => this.hideEndModal());
    document.getElementById('confirmEndBtn')?.addEventListener('click', () => this.endJourney());

    // Photo upload
    const photoUploadArea = document.getElementById('photoUploadArea');
    const photoInput = document.getElementById('journeyPhoto') as HTMLInputElement;
    photoUploadArea?.addEventListener('click', () => photoInput?.click());
    photoInput?.addEventListener('change', (e) => this.handlePhotoSelect(e));

    // Detail modal controls
    document.getElementById('closeDetailModal')?.addEventListener('click', () => this.hideDetailModal());
    document.getElementById('closeDetailBtn')?.addEventListener('click', () => this.hideDetailModal());
  }

  private async checkGPS(): Promise<void> {
    const gpsStatus = document.getElementById('gpsStatus');
    if (!gpsStatus) return;

    try {
      const position = await gpsService.getCurrentPosition();
      if (position) {
        const accuracy = position.accuracy_m || 0;
        gpsStatus.innerHTML = `
          <span class="gps-indicator active"></span>
          <span>GPS Ready (Accuracy: ${accuracy.toFixed(0)}m)</span>
        `;
      } else {
        gpsStatus.innerHTML = `
          <span class="gps-indicator error"></span>
          <span>GPS unavailable - Enable location</span>
        `;
      }
    } catch (error) {
      gpsStatus.innerHTML = `
        <span class="gps-indicator error"></span>
        <span>GPS error - Check permissions</span>
      `;
    }
  }

  private updateCompanySelect(): void {
    const select = document.getElementById('companySelect') as HTMLSelectElement;
    if (!select) return;

    select.innerHTML = `
      <option value="">Select Company</option>
      ${this.companies.map(c => `<option value="${c.id}">${c.name}</option>`).join('')}
    `;
  }

  private updateUI(): void {
    const startCard = document.getElementById('startJourneyCard');
    const activeCard = document.getElementById('activeJourneyCard');
    
    if (this.activeJourney) {
      if (startCard) startCard.style.display = 'none';
      if (activeCard) {
        activeCard.style.display = 'block';
        const details = document.getElementById('activeDetails');
        if (details) {
          const distance = (this.activeJourney as any).distance_km ?? 0;
          const stops = (this.activeJourney as any).stops_count ?? 0;
          const points = (this.activeJourney as any).track_points_count ?? 0;
          const isStale = (this.activeJourney as any).is_stale === true;
          const staleDate = (this.activeJourney as any).stale_date;

          const staleBanner = isStale ? `
            <div style="
              background: rgba(220,38,38,0.15);
              border: 1px solid rgba(220,38,38,0.5);
              border-radius: 10px;
              padding: 12px 14px;
              margin-bottom: 12px;
              display: flex;
              align-items: flex-start;
              gap: 10px;
            ">
              <span style="font-size: 18px; flex-shrink: 0;">⚠️</span>
              <div>
                <div style="color: #fca5a5; font-weight: 700; font-size: 13px; margin-bottom: 2px;">
                  Stuck Journey from ${staleDate ? new Date(staleDate + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : 'a previous date'}
                </div>
                <div style="color: rgba(252,165,165,0.8); font-size: 12px; line-height: 1.4;">
                  This journey was never ended. You must end this journey before starting a new one. If you cannot end it, ask your manager to force-stop it.
                </div>
              </div>
            </div>
          ` : '';
          
          details.innerHTML = `
            ${staleBanner}
            <div class="active-info">
              <span class="info-label">Company:</span>
              <span class="info-value">${this.activeJourney.company_name || 'N/A'}</span>
            </div>
            <div class="active-info">
              <span class="info-label">Started:</span>
              <span class="info-value">${this.formatTime(this.activeJourney.start_time)}</span>
            </div>
            <div class="active-info">
              <span class="info-label">Transport:</span>
              <span class="info-value">${this.activeJourney.transport_mode || 'N/A'}</span>
            </div>
            <div class="active-info">
              <span class="info-label">Purpose:</span>
              <span class="info-value">${this.activeJourney.purpose || 'N/A'}</span>
            </div>
            <div class="active-stats">
              <div class="stat-box">
                <span class="stat-value" id="liveDistance">${distance.toFixed(1)}</span>
                <span class="stat-label">KM</span>
              </div>
              <div class="stat-box">
                <span class="stat-value" id="liveStops">${stops}</span>
                <span class="stat-label">Stops</span>
              </div>
              <div class="stat-box">
                <span class="stat-value" id="livePoints">${points}</span>
                <span class="stat-label">Points</span>
              </div>
            </div>
          `;
        }
      }
    } else {
      if (startCard) startCard.style.display = 'block';
      if (activeCard) activeCard.style.display = 'none';
    }
  }

  private async startJourney(): Promise<void> {
    const companySelect = document.getElementById('companySelect') as HTMLSelectElement;
    const clientName = (document.getElementById('clientName') as HTMLInputElement)?.value || '';
    const notes = (document.getElementById('journeyNotes') as HTMLTextAreaElement)?.value || '';
    const kraSelect = document.getElementById('kraSelect') as HTMLSelectElement;
    const taskSelect = document.getElementById('taskSelect') as HTMLSelectElement;

    if (!companySelect?.value) {
      alert('Please select a company');
      return;
    }

    try {
      const position = await gpsService.getCurrentPosition();
      if (!position) {
        alert('GPS is required to start a journey. Please enable location services.');
        return;
      }

      // DC Protocol: Match web's payload structure exactly
      const selectedKraId = kraSelect?.value || '';
      const selectedTaskId = taskSelect?.value || '';

      const payload: any = {
        company_id: parseInt(companySelect.value),
        transport_mode: this.selectedTransport,
        purpose: this.selectedPurpose,
        client_name: clientName,
        purpose_description: notes,
        gps_enabled: true,
        gps_permission_denied: false,
        location: {
          latitude: position.latitude,
          longitude: position.longitude,
          accuracy: position.accuracy_m || 0,
          speed: position.speed_kmh || null,
          heading: position.heading || null
        },
        device_info: {
          userAgent: navigator.userAgent,
          platform: navigator.platform
        },
        linked_kra_id: selectedKraId ? parseInt(selectedKraId) : null,
        linked_task_id: selectedTaskId ? parseInt(selectedTaskId) : null
      };

      console.log('[JourneysPage] Starting journey with payload:', payload);
      const response = await apiService.post<any>('/staff/journeys/start', payload);
      console.log('[JourneysPage] Start journey response:', response);
      
      if (response.success && response.data) {
        // Backend returns { success, journey: {...}, journey_session_token }
        const journey = response.data.journey;
        const sessionToken = response.data.journey_session_token;
        
        if (journey) {
          this.activeJourney = {
            id: journey.id,
            start_time: journey.start_time,
            company_name: journey.company_name || 'N/A',
            transport_mode: journey.transport_mode || 'N/A',
            purpose: journey.purpose || 'N/A',
            session_token: sessionToken
          };
        }
        
        if (sessionToken) {
          await apiService.setJourneyToken(sessionToken);
        }
        
        // DC Protocol (Feb 2026): Start GPS journey tracking for live location updates
        if (journey?.id) {
          try {
            gpsService.startJourneyTracking(journey.id);
            console.log(`[JourneysPage] GPS journey tracking started for journey ${journey.id}`);
          } catch (gpsErr: any) {
            console.warn('[JourneysPage] GPS tracking start failed (non-fatal):', gpsErr);
          }
        }
        
        this.startHeartbeat();
        this.updateUI();
        this.loadJourneys();
        alert('Journey started successfully!');
      } else {
        alert(response.error || 'Failed to start journey');
      }
    } catch (error: any) {
      const msg = error?.message || '';
      if (msg.includes('null') || msg.includes('undefined') || msg.includes('Cannot read')) {
        console.error('[JourneysPage] Internal error in startJourney:', error);
        alert('Something went wrong starting the journey. Please try again.');
      } else {
        alert(msg || 'Failed to start journey');
      }
    }
  }

  private startHeartbeat(): void {
    if (this.heartbeatInterval) clearInterval(this.heartbeatInterval);
    
    // Send first heartbeat immediately to get initial stats
    this.sendHeartbeat();
    
    this.heartbeatInterval = setInterval(async () => {
      if (!this.activeJourney) {
        clearInterval(this.heartbeatInterval);
        return;
      }
      await this.sendHeartbeat();
    }, 30000); // 30 second heartbeat
  }

  private async sendHeartbeat(): Promise<void> {
    if (!this.activeJourney) return;
    
    try {
      const position = await gpsService.getCurrentPosition();
      const sessionToken = await apiService.getJourneyToken();
      
      // Build heartbeat URL with session token
      let heartbeatUrl = `/staff/journeys/${this.activeJourney.id}/heartbeat`;
      if (sessionToken) {
        heartbeatUrl += `?session_token=${encodeURIComponent(sessionToken)}`;
      }

      // DC Protocol: Backend expects nested location object matching JourneyHeartbeatRequest schema
      const payload: any = {};
      if (position) {
        payload.location = {
          latitude: position.latitude,
          longitude: position.longitude,
          accuracy: position.accuracy_m || 0,
          speed: position.speed_kmh || null,
          heading: position.heading || null
        };
        payload.speed_kmh = position.speed_kmh || null;
      }
      
      const response = await apiService.post<any>(heartbeatUrl, payload);
      
      // Update real-time stats from heartbeat response
      if (response.success && response.data) {
        const data = response.data;
        if (this.activeJourney) {
          this.activeJourney.distance_km = data.distance_km ?? data.total_distance_km ?? this.activeJourney.distance_km;
          this.activeJourney.stops_count = data.stops_count ?? data.stop_count ?? this.activeJourney.stops_count;
          this.activeJourney.track_points_count = data.track_points_count ?? data.points_count ?? this.activeJourney.track_points_count;
          this.updateLiveStats();
        }
      }
    } catch (error) {
      console.error('[JourneysPage] Heartbeat failed:', error);
    }
  }

  private updateLiveStats(): void {
    if (!this.activeJourney) return;
    
    const distanceEl = document.getElementById('liveDistance');
    const stopsEl = document.getElementById('liveStops');
    const pointsEl = document.getElementById('livePoints');
    
    if (distanceEl) distanceEl.textContent = (this.activeJourney.distance_km ?? 0).toFixed(1);
    if (stopsEl) stopsEl.textContent = String(this.activeJourney.stops_count ?? 0);
    if (pointsEl) pointsEl.textContent = String(this.activeJourney.track_points_count ?? 0);
  }

  private showEndModal(): void {
    const modal = document.getElementById('endJourneyModal');
    if (modal) modal.style.display = 'flex';
  }

  private hideEndModal(): void {
    const modal = document.getElementById('endJourneyModal');
    if (modal) modal.style.display = 'none';
  }

  private handlePhotoSelect(e: Event): void {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const preview = document.getElementById('photoPreview') as HTMLImageElement;
      const placeholder = document.getElementById('uploadPlaceholder');
      if (preview && event.target?.result) {
        preview.src = event.target.result as string;
        preview.style.display = 'block';
        if (placeholder) placeholder.style.display = 'none';
      }
    };
    reader.readAsDataURL(file);
  }

  private async endJourney(): Promise<void> {
    if (!this.activeJourney) return;

    const photoInput = document.getElementById('journeyPhoto') as HTMLInputElement;
    const photoFile = photoInput?.files?.[0];

    // Mandatory photo validation
    if (!photoFile) {
      alert('Photo is required to complete the journey. Please capture a photo.');
      return;
    }

    try {
      const position = await gpsService.getCurrentPosition();
      const notes = (document.getElementById('endNotes') as HTMLTextAreaElement)?.value || '';

      // DC Protocol: Backend expects 2 separate API calls:
      // 1. /end - JSON body with location and notes
      // 2. /photo - FormData with photo file

      // Step 1: End journey with JSON body
      const sessionToken = await apiService.getJourneyToken();
      let endUrl = `/staff/journeys/${this.activeJourney.id}/end`;
      if (sessionToken) {
        endUrl += `?session_token=${encodeURIComponent(sessionToken)}`;
      }

      const endPayload: any = { notes };
      if (position) {
        endPayload.location = {
          latitude: position.latitude,
          longitude: position.longitude,
          accuracy: position.accuracy_m || 0
        };
      }

      console.log('[JourneysPage] Ending journey with payload:', endPayload);
      const endResponse = await apiService.post(endUrl, endPayload);
      
      if (!endResponse.success) {
        alert(endResponse.error || 'Failed to end journey');
        return;
      }

      // Step 2: Upload photo separately
      const photoFormData = new FormData();
      photoFormData.append('photo', photoFile);

      let photoUrl = `/staff/journeys/${this.activeJourney.id}/photo`;
      if (sessionToken) {
        photoUrl += `?session_token=${encodeURIComponent(sessionToken)}`;
      }

      console.log('[JourneysPage] Uploading journey photo...');
      const photoResponse = await apiService.postFormData(photoUrl, photoFormData);
      
      if (!photoResponse.success) {
        console.warn('[JourneysPage] Photo upload failed:', photoResponse.error);
        // Journey already ended, just warn about photo
      }

      // Success - clean up
      clearInterval(this.heartbeatInterval);
      
      // DC Protocol (Feb 2026): Stop GPS journey tracking - heartbeats continue if still clocked in
      gpsService.stopJourneyTracking();
      console.log('[JourneysPage] GPS journey tracking stopped');
      
      this.activeJourney = null;
      await apiService.clearJourneyToken();
      this.hideEndModal();
      this.updateUI();
      this.loadJourneys();
      alert('Journey completed successfully!');
    } catch (error: any) {
      console.error('[JourneysPage] End journey error:', error);
      alert(error.message || 'Failed to end journey');
    }
  }

  private updateList(): void {
    const listContainer = document.getElementById('journeysList');
    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    if (this.journeys.length === 0) {
      listContainer.innerHTML = '<div class="empty-state">No journeys found</div>';
      return;
    }

    // Calculate stats - Web Parity
    const totalJourneys = this.journeys.length;
    const totalDistance = this.journeys.reduce((sum, j) => sum + (j.distance_km || 0), 0);
    const approvedJourneys = this.journeys.filter(j => j.status?.toLowerCase() === 'approved');
    const pendingJourneys = this.journeys.filter(j => 
      j.status?.toLowerCase() === 'pending' || j.status?.toLowerCase() === 'in_progress'
    );
    const totalApproved = approvedJourneys.reduce((sum, j) => sum + (j.reimbursement_amount || 0), 0);
    const pendingCount = pendingJourneys.length;

    const totalJourneysEl = document.getElementById('totalJourneys');
    const totalDistanceEl = document.getElementById('totalDistance');
    const totalReimbursementEl = document.getElementById('totalReimbursement');
    const pendingCountEl = document.getElementById('pendingCount');
    
    if (totalJourneysEl) totalJourneysEl.textContent = totalJourneys.toString();
    if (totalDistanceEl) totalDistanceEl.textContent = totalDistance.toFixed(1);
    if (totalReimbursementEl) totalReimbursementEl.textContent = `₹${totalApproved.toFixed(0)}`;
    if (pendingCountEl) pendingCountEl.textContent = pendingCount.toString();

    listContainer.innerHTML = this.journeys.map(journey => `
      <div class="list-item card journey-item" data-journey-id="${journey.id}">
        <div class="item-header">
          <span class="item-date">${this.formatDate(journey.date)}</span>
          <span class="status-badge ${journey.status?.toLowerCase() || 'completed'}">${journey.status || 'Completed'}</span>
        </div>
        <div class="journey-route">
          <div class="route-point start">
            <span class="route-dot"></span>
            <span class="route-text">${journey.start_location || 'Start Location'}</span>
            <span class="route-time">${this.formatTime(journey.start_time)}</span>
          </div>
          <div class="route-line"></div>
          <div class="route-point end">
            <span class="route-dot"></span>
            <span class="route-text">${journey.end_location || 'End Location'}</span>
            <span class="route-time">${journey.end_time ? this.formatTime(journey.end_time) : '--:--'}</span>
          </div>
        </div>
        <div class="journey-meta">
          <span class="meta-item">${this.getTransportIcon(journey.transport_mode)} ${journey.transport_mode || 'Vehicle'}</span>
          <span class="meta-item">📍 ${journey.distance_km ? journey.distance_km.toFixed(1) + ' km' : '--'}</span>
          <span class="meta-item">💰 ₹${journey.reimbursement_amount?.toFixed(0) || '0'}</span>
        </div>
        ${journey.company_name ? `<div class="journey-company">${journey.company_name}</div>` : ''}
        <div class="view-details-hint">Tap to view route details →</div>
      </div>
    `).join('');

    // Attach click handlers to journey items
    listContainer.querySelectorAll('.journey-item').forEach(item => {
      item.addEventListener('click', () => {
        const journeyId = item.getAttribute('data-journey-id');
        if (journeyId) {
          this.showJourneyDetail(parseInt(journeyId));
        }
      });
    });
  }

  private getTransportIcon(mode: string): string {
    const found = TRANSPORT_MODES.find(t => t.id === mode);
    return found?.icon || '🚗';
  }

  private formatDate(dateStr: string): string {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { weekday: 'short', day: 'numeric', month: 'short' });
  }

  private formatTime(timeStr: string): string {
    if (!timeStr) return '--:--';
    const date = new Date(timeStr);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  }

  // DC Protocol: Detect stops based on timestamp gaps and stationary position
  private detectStopsWithTimestamps(trackPoints: any[]): { address: string; durationMinutes: number; startIndex: number }[] {
    const stops: { address: string; durationMinutes: number; startIndex: number }[] = [];
    if (trackPoints.length < 3) return stops;

    const MIN_STOP_DURATION_MS = 120000; // 2 minutes min stop
    const MAX_MOVEMENT_THRESHOLD = 0.05; // 50 meters

    let stopStartIndex: number | null = null;
    let stopStartTime: Date | null = null;

    for (let i = 1; i < trackPoints.length; i++) {
      const prev = trackPoints[i - 1];
      const curr = trackPoints[i];
      
      const dist = this.haversineDistance(
        prev.latitude, prev.longitude,
        curr.latitude, curr.longitude
      );

      if (dist < MAX_MOVEMENT_THRESHOLD) {
        if (stopStartIndex === null) {
          stopStartIndex = i - 1;
          const ts = prev.timestamp || prev.captured_at;
          stopStartTime = ts ? new Date(ts) : null;
        }
      } else if (stopStartIndex !== null) {
        const currTs = curr.timestamp || curr.captured_at;
        const endTime = currTs ? new Date(currTs) : null;
        
        if (stopStartTime && endTime) {
          const durationMs = endTime.getTime() - stopStartTime.getTime();
          if (durationMs >= MIN_STOP_DURATION_MS) {
            stops.push({
              address: trackPoints[stopStartIndex].address || '',
              durationMinutes: Math.round(durationMs / 60000),
              startIndex: stopStartIndex
            });
          }
        }
        stopStartIndex = null;
        stopStartTime = null;
      }
    }

    // Check final stop
    if (stopStartIndex !== null && stopStartTime) {
      const lastPoint = trackPoints[trackPoints.length - 1];
      const lastTs = lastPoint.timestamp || lastPoint.captured_at;
      if (lastTs) {
        const endTime = new Date(lastTs);
        const durationMs = endTime.getTime() - stopStartTime.getTime();
        if (durationMs >= MIN_STOP_DURATION_MS) {
          stops.push({
            address: trackPoints[stopStartIndex].address || '',
            durationMinutes: Math.round(durationMs / 60000),
            startIndex: stopStartIndex
          });
        }
      }
    }

    return stops.slice(0, 10); // Max 10 stops
  }

  private haversineDistance(lat1: number, lng1: number, lat2: number, lng2: number): number {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lng2 - lng1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  private formatStopDuration(mins: number): string {
    if (mins < 60) return `${mins}m`;
    const hours = Math.floor(mins / 60);
    const remainingMins = mins % 60;
    return remainingMins > 0 ? `${hours}h ${remainingMins}m` : `${hours}h`;
  }

  private formatCoords(point: any): string {
    if (!point) return 'Unknown location';
    const lat = point.latitude?.toFixed(5) || '0.00000';
    const lng = point.longitude?.toFixed(5) || '0.00000';
    return `${lat}, ${lng}`;
  }

  // DC_GEOCODE_001: Reverse geocode coordinates to human-readable location names
  private addressCache: Map<string, string> = new Map();
  
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
        
        // Build readable location name (road/area, city/town)
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

  // DC_GEOCODE_002: Fetch addresses for route points and update UI
  private async loadRoutePointAddresses(trackPoints: any[], stops: any[]): Promise<void> {
    if (!trackPoints || trackPoints.length === 0) return;
    
    const startPoint = trackPoints[0];
    const endPoint = trackPoints[trackPoints.length - 1];
    
    // Fetch start address
    if (startPoint?.latitude && startPoint?.longitude) {
      const startAddr = await this.reverseGeocode(startPoint.latitude, startPoint.longitude);
      const startEl = document.querySelector('.stop-item.start .stop-address');
      if (startEl) startEl.textContent = startAddr;
    }
    
    // Fetch end address
    if (endPoint?.latitude && endPoint?.longitude) {
      const endAddr = await this.reverseGeocode(endPoint.latitude, endPoint.longitude);
      const endEl = document.querySelector('.stop-item.end .stop-address');
      if (endEl) endEl.textContent = endAddr;
    }
    
    // Fetch addresses for each stop (with 300ms delay between requests to respect rate limits)
    for (let i = 0; i < stops.length; i++) {
      const stopPoint = trackPoints[stops[i].startIndex];
      if (stopPoint?.latitude && stopPoint?.longitude) {
        await new Promise(resolve => setTimeout(resolve, 300)); // Rate limit delay
        const stopAddr = await this.reverseGeocode(stopPoint.latitude, stopPoint.longitude);
        const stopEls = document.querySelectorAll('.stop-item.pause .stop-address');
        if (stopEls[i]) stopEls[i].textContent = stopAddr;
      }
    }
  }

  // DC_BATTERY_DISPLAY_001: Battery percentage helpers for journey details
  // Fixed: Use actual first/last track points' battery (not filtered array)
  private getJourneyBatteryStats(trackPoints: any[]): { start: number | null; end: number | null; min: number | null } {
    if (!trackPoints || trackPoints.length === 0) {
      return { start: null, end: null, min: null };
    }
    
    // Get battery from actual first and last track points
    const firstBattery = trackPoints[0]?.battery_percentage;
    const lastBattery = trackPoints[trackPoints.length - 1]?.battery_percentage;
    
    const startBattery = (typeof firstBattery === 'number') ? firstBattery : null;
    const endBattery = (typeof lastBattery === 'number') ? lastBattery : null;
    
    // Calculate min across all defined values
    const allBatteries = trackPoints
      .map(tp => tp.battery_percentage)
      .filter((b): b is number => b !== null && b !== undefined && typeof b === 'number');
    
    const minBattery = allBatteries.length > 0 ? Math.min(...allBatteries) : null;
    
    return {
      start: startBattery,
      end: endBattery,
      min: minBattery
    };
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
    if (stats.min >= 50) return 'success';
    if (stats.min >= 20) return 'warning';
    return 'danger';
  }

  private async showJourneyDetail(journeyId: number): Promise<void> {
    const modal = document.getElementById('journeyDetailModal');
    const body = document.getElementById('journeyDetailBody');
    
    if (!modal || !body) return;
    
    modal.style.display = 'flex';
    body.innerHTML = '<div class="loading-state">Loading journey details...</div>';

    try {
      // DC Protocol: Use track-points endpoint matching web implementation
      const response = await apiService.get<any>(`/staff/journeys/${journeyId}/track-points`);
      
      if (response.success && response.data) {
        const journey = response.data.journey || response.data;
        // Track points are at top level per backend response schema
        const trackPoints = response.data.track_points || journey.track_points || [];
        
        // Calculate duration
        let duration = '--';
        let durationMins = 0;
        if (journey.start_time && journey.end_time) {
          const startDate = new Date(journey.start_time);
          const endDate = new Date(journey.end_time);
          const diffMs = endDate.getTime() - startDate.getTime();
          durationMins = Math.round(diffMs / 60000);
          const hours = Math.floor(durationMins / 60);
          const mins = durationMins % 60;
          duration = hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
        } else if (journey.total_duration_minutes) {
          durationMins = Math.round(journey.total_duration_minutes);
          const hours = Math.floor(durationMins / 60);
          const mins = durationMins % 60;
          duration = hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
        }

        // Detect stops with timestamps
        const stops = this.detectStopsWithTimestamps(trackPoints);
        
        // Get addresses from track points
        const startAddress = trackPoints[0]?.address || journey.start_location || '';
        const endAddress = trackPoints[trackPoints.length - 1]?.address || journey.end_location || '';
        
        // Get transport rate
        const transportMode = TRANSPORT_MODES.find(t => t.id === journey.transport_mode);
        const ratePerKm = journey.rate_per_km || transportMode?.rate || 0;

        body.innerHTML = `
          <div class="detail-section">
            <h5 class="detail-title">Journey Info</h5>
            <div class="detail-grid">
              <div class="detail-row">
                <span class="detail-label">Date</span>
                <span class="detail-value">${this.formatDate(journey.date || journey.start_time)}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">Status</span>
                <span class="detail-value status-${journey.status?.toLowerCase() || 'completed'}">${journey.status || 'Completed'}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">Company</span>
                <span class="detail-value">${journey.company_name || 'N/A'}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">Transport</span>
                <span class="detail-value">${this.getTransportIcon(journey.transport_mode)} ${journey.transport_mode || 'N/A'} @ ₹${ratePerKm}/km</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">Purpose</span>
                <span class="detail-value">${this.formatPurpose(journey.purpose)}</span>
              </div>
              ${journey.client_name ? `
              <div class="detail-row">
                <span class="detail-label">Client</span>
                <span class="detail-value">${journey.client_name}</span>
              </div>
              ` : ''}
            </div>
          </div>

          <div class="detail-section">
            <h5 class="detail-title">Route Summary</h5>
            <div class="route-summary-stats">
              <div class="stat-box">
                <span class="stat-value">${(journey.total_distance_km || journey.distance_km || 0).toFixed(2)}</span>
                <span class="stat-label">KM</span>
              </div>
              <div class="stat-box">
                <span class="stat-value">${duration}</span>
                <span class="stat-label">Duration</span>
              </div>
              <div class="stat-box">
                <span class="stat-value">${Math.round(journey.average_speed_kmh || 0)}</span>
                <span class="stat-label">Avg km/h</span>
              </div>
              <div class="stat-box">
                <span class="stat-value">${Math.round(journey.max_speed_kmh || 0)}</span>
                <span class="stat-label">Max km/h</span>
              </div>
            </div>
            <div class="route-summary-stats" style="margin-top: 8px;">
              <div class="stat-box ${journey.is_reimbursable ? 'success' : 'muted'}">
                <span class="stat-value">₹${(journey.reimbursement_amount || 0).toFixed(0)}</span>
                <span class="stat-label">${journey.is_reimbursable ? journey.approval_status || 'Pending' : 'Not Eligible'}</span>
              </div>
              <div class="stat-box">
                <span class="stat-value">${trackPoints.length}</span>
                <span class="stat-label">GPS Points</span>
              </div>
              <div class="stat-box">
                <span class="stat-value">${stops.length}</span>
                <span class="stat-label">Stops</span>
              </div>
              <div class="stat-box ${this.getBatteryColorClass(this.getJourneyBatteryStats(trackPoints))}">
                <span class="stat-value">${this.formatBatteryRange(trackPoints)}</span>
                <span class="stat-label">Battery %</span>
              </div>
            </div>
          </div>

          <div class="detail-section">
            <h5 class="detail-title">Route Points</h5>
            <div class="stops-panel">
              <div class="stop-item start">
                <div class="stop-icon start">▶</div>
                <div class="stop-info">
                  <span class="stop-label">Start Point</span>
                  <span class="stop-address">${startAddress || this.formatCoords(trackPoints[0])}</span>
                  <span class="stop-time">${this.formatTime(journey.start_time)}</span>
                </div>
              </div>
              ${stops.map((stop, i) => {
                const stopPoint = trackPoints[stop.startIndex];
                const locationDisplay = stop.address || this.formatCoords(stopPoint);
                return `
                <div class="stop-item pause">
                  <div class="stop-icon pause">⏸</div>
                  <div class="stop-info">
                    <span class="stop-label">Stop ${i + 1} <span class="stop-duration">(${this.formatStopDuration(stop.durationMinutes)})</span></span>
                    <span class="stop-address">${locationDisplay}</span>
                  </div>
                </div>
              `}).join('')}
              <div class="stop-item end">
                <div class="stop-icon end">🏁</div>
                <div class="stop-info">
                  <span class="stop-label">End Point</span>
                  <span class="stop-address">${endAddress || this.formatCoords(trackPoints[trackPoints.length - 1])}</span>
                  <span class="stop-time">${journey.end_time ? this.formatTime(journey.end_time) : '--:--'}</span>
                </div>
              </div>
              <div class="stops-summary">${trackPoints.length} GPS points recorded</div>
            </div>
          </div>

          ${journey.notes ? `
            <div class="detail-section">
              <h5 class="detail-title">Notes</h5>
              <p class="journey-notes">${journey.notes}</p>
            </div>
          ` : ''}

          <div id="leafletMapSection" class="map-section"></div>
        `;

        // Load enhanced Leaflet map if we have track points
        if (trackPoints.length >= 2) {
          setTimeout(() => {
            if (this.leafletMap) {
              this.leafletMap.destroy();
            }
            this.leafletMap = new LeafletJourneyMap({
              containerId: 'leafletMapSection',
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
              }))
            });
            this.leafletMap.mount();
            
            // DC_GEOCODE_003: Load location names for route points after map is mounted
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

  private playbackState: { playing: boolean; index: number; interval: any; speed: number } = {
    playing: false,
    index: 0,
    interval: null,
    speed: 2
  };

  private renderPlaybackControls(trackPoints: any[], journey: any, stops: any[]): void {
    const container = document.getElementById('playbackControlsContainer');
    if (!container || trackPoints.length < 2) return;

    container.innerHTML = `
      <div class="detail-section">
        <h5 class="detail-title">Route Playback</h5>
        <div class="playback-controls">
          <div class="playback-buttons">
            <button id="playPauseBtn" class="playback-btn play">▶</button>
            <button id="resetBtn" class="playback-btn">↺</button>
          </div>
          <div class="playback-slider-container">
            <input type="range" id="playbackSlider" class="playback-slider" min="0" max="${trackPoints.length - 1}" value="0">
          </div>
          <div class="playback-speed">
            <select id="playbackSpeed" class="speed-select">
              <option value="1">1x</option>
              <option value="2" selected>2x</option>
              <option value="4">4x</option>
              <option value="8">8x</option>
            </select>
          </div>
        </div>
        <div class="playback-info">
          <span id="playbackProgress">0 / ${trackPoints.length}</span>
        </div>
      </div>
    `;

    // Reset playback state - start from 0 for playback
    this.playbackState = { playing: false, index: 0, interval: null, speed: 2 };
    
    // Update slider to start position
    const sliderEl = document.getElementById('playbackSlider') as HTMLInputElement;
    if (sliderEl) sliderEl.value = '0';
    
    // Update canvas to show full route initially then reset for playback
    this.updatePlaybackProgress(trackPoints.length);

    const playPauseBtn = document.getElementById('playPauseBtn');
    const resetBtn = document.getElementById('resetBtn');
    const slider = document.getElementById('playbackSlider') as HTMLInputElement;
    const speedSelect = document.getElementById('playbackSpeed') as HTMLSelectElement;

    if (playPauseBtn) {
      playPauseBtn.addEventListener('click', () => this.togglePlayback(trackPoints));
    }
    if (resetBtn) {
      resetBtn.addEventListener('click', () => this.resetPlayback(trackPoints));
    }
    if (slider) {
      slider.addEventListener('input', () => {
        this.playbackState.index = parseInt(slider.value);
        this.updatePlaybackCanvas(trackPoints);
        this.updatePlaybackProgress(trackPoints.length);
      });
    }
    if (speedSelect) {
      speedSelect.addEventListener('change', () => {
        this.playbackState.speed = parseInt(speedSelect.value);
        if (this.playbackState.playing) {
          this.stopPlaybackInterval();
          this.startPlaybackInterval(trackPoints);
        }
      });
    }
  }

  private togglePlayback(trackPoints: any[]): void {
    const btn = document.getElementById('playPauseBtn');
    if (this.playbackState.playing) {
      this.stopPlaybackInterval();
      if (btn) btn.textContent = '▶';
      if (btn) btn.classList.remove('pause');
      if (btn) btn.classList.add('play');
    } else {
      this.startPlaybackInterval(trackPoints);
      if (btn) btn.textContent = '⏸';
      if (btn) btn.classList.remove('play');
      if (btn) btn.classList.add('pause');
    }
    this.playbackState.playing = !this.playbackState.playing;
  }

  private startPlaybackInterval(trackPoints: any[]): void {
    const interval = 500 / this.playbackState.speed;
    this.playbackState.interval = setInterval(() => {
      if (this.playbackState.index < trackPoints.length - 1) {
        this.playbackState.index++;
        this.updatePlaybackCanvas(trackPoints);
        this.updatePlaybackProgress(trackPoints.length);
        const slider = document.getElementById('playbackSlider') as HTMLInputElement;
        if (slider) slider.value = String(this.playbackState.index);
      } else {
        this.stopPlaybackInterval();
        const btn = document.getElementById('playPauseBtn');
        if (btn) btn.textContent = '▶';
        if (btn) btn.classList.remove('pause');
        if (btn) btn.classList.add('play');
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

  private resetPlayback(trackPoints: any[]): void {
    this.stopPlaybackInterval();
    this.playbackState.index = 0;
    this.playbackState.playing = false;
    const btn = document.getElementById('playPauseBtn');
    if (btn) btn.textContent = '▶';
    if (btn) btn.classList.remove('pause');
    if (btn) btn.classList.add('play');
    const slider = document.getElementById('playbackSlider') as HTMLInputElement;
    if (slider) slider.value = '0';
    this.updatePlaybackCanvas(trackPoints);
    this.updatePlaybackProgress(trackPoints.length);
  }

  private updatePlaybackProgress(total: number): void {
    const progressEl = document.getElementById('playbackProgress');
    if (progressEl) {
      progressEl.textContent = `${this.playbackState.index + 1} / ${total}`;
    }
  }

  private updatePlaybackCanvas(trackPoints: any[]): void {
    const canvas = document.getElementById('detailRouteCanvas') as HTMLCanvasElement;
    if (!canvas || trackPoints.length < 2) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Calculate bounds
    let minLat = trackPoints[0].latitude;
    let maxLat = trackPoints[0].latitude;
    let minLng = trackPoints[0].longitude;
    let maxLng = trackPoints[0].longitude;

    for (const point of trackPoints) {
      minLat = Math.min(minLat, point.latitude);
      maxLat = Math.max(maxLat, point.latitude);
      minLng = Math.min(minLng, point.longitude);
      maxLng = Math.max(maxLng, point.longitude);
    }

    const padding = 20;
    const latRange = maxLat - minLat || 0.001;
    const lngRange = maxLng - minLng || 0.001;

    const toCanvasX = (lng: number) => padding + ((lng - minLng) / lngRange) * (canvas.width - 2 * padding);
    const toCanvasY = (lat: number) => canvas.height - padding - ((lat - minLat) / latRange) * (canvas.height - 2 * padding);

    // Clear canvas
    ctx.fillStyle = '#1a1a2e';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw grid
    ctx.strokeStyle = '#2a2a3e';
    ctx.lineWidth = 1;
    for (let x = 0; x < canvas.width; x += 40) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, canvas.height);
      ctx.stroke();
    }
    for (let y = 0; y < canvas.height; y += 40) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(canvas.width, y);
      ctx.stroke();
    }

    // Draw faded full route
    ctx.strokeStyle = 'rgba(255,255,255,0.2)';
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    ctx.moveTo(toCanvasX(trackPoints[0].longitude), toCanvasY(trackPoints[0].latitude));
    for (let i = 1; i < trackPoints.length; i++) {
      ctx.lineTo(toCanvasX(trackPoints[i].longitude), toCanvasY(trackPoints[i].latitude));
    }
    ctx.stroke();
    ctx.setLineDash([]);

    // Draw progressive route line up to current index
    ctx.strokeStyle = '#00d09c';
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.beginPath();
    ctx.moveTo(toCanvasX(trackPoints[0].longitude), toCanvasY(trackPoints[0].latitude));
    for (let i = 1; i <= this.playbackState.index; i++) {
      ctx.lineTo(toCanvasX(trackPoints[i].longitude), toCanvasY(trackPoints[i].latitude));
    }
    ctx.stroke();

    // Draw start marker
    const startX = toCanvasX(trackPoints[0].longitude);
    const startY = toCanvasY(trackPoints[0].latitude);
    ctx.fillStyle = '#4CAF50';
    ctx.beginPath();
    ctx.arc(startX, startY, 8, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 10px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('S', startX, startY);

    // Draw end marker
    const lastPoint = trackPoints[trackPoints.length - 1];
    const endX = toCanvasX(lastPoint.longitude);
    const endY = toCanvasY(lastPoint.latitude);
    ctx.fillStyle = '#f44336';
    ctx.beginPath();
    ctx.arc(endX, endY, 8, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#fff';
    ctx.fillText('E', endX, endY);

    // Draw current position marker
    if (this.playbackState.index > 0 && this.playbackState.index < trackPoints.length) {
      const currPoint = trackPoints[this.playbackState.index];
      const currX = toCanvasX(currPoint.longitude);
      const currY = toCanvasY(currPoint.latitude);
      
      // Glow effect
      ctx.shadowColor = '#ffc107';
      ctx.shadowBlur = 10;
      ctx.fillStyle = '#ffc107';
      ctx.beginPath();
      ctx.arc(currX, currY, 6, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
      
      // White border
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  }

  private currentTrackPoints: any[] = [];

  private renderRouteMap(trackPoints: any[], journey: any): void {
    const container = document.getElementById('journeyMapContainer');
    if (!container || trackPoints.length < 2) return;

    // Store track points for playback
    this.currentTrackPoints = trackPoints;

    container.innerHTML = `
      <div class="detail-section">
        <h5 class="detail-title">Route Map</h5>
        <div class="route-canvas-container">
          <canvas id="detailRouteCanvas" width="350" height="200"></canvas>
        </div>
      </div>
    `;

    // Draw full route initially (set index to end for initial display)
    const savedIndex = this.playbackState.index;
    this.playbackState.index = trackPoints.length - 1;
    this.updatePlaybackCanvas(trackPoints);
    this.playbackState.index = savedIndex;
  }

  private hideDetailModal(): void {
    // Stop any active playback and cleanup
    this.stopPlaybackInterval();
    this.playbackState.playing = false;
    
    // Destroy Leaflet map instance
    if (this.leafletMap) {
      this.leafletMap.destroy();
      this.leafletMap = null;
    }
    
    const modal = document.getElementById('journeyDetailModal');
    if (modal) modal.style.display = 'none';
  }
}
