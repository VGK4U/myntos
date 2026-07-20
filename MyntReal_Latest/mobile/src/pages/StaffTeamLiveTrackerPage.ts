/**
 * Staff Team Live Tracker Page
 * DC Protocol: DC_MOBILE_LIVE_TRACKER_001
 * View real-time team member locations with map and list
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import L from 'leaflet';

interface LiveLocation {
  employee_id: number;
  employee_name?: string;
  name?: string;
  emp_code: string;
  department?: string;
  designation?: string;
  latitude?: number;
  longitude?: number;
  lat?: number;
  lng?: number;
  address?: string;
  accuracy?: number;
  accuracy_m?: number;
  last_update?: string;
  captured_at?: string;
  status?: string;
  is_on_journey?: boolean;
  is_on_break?: boolean;
  journey_purpose?: string;
  battery_level?: number;
  battery_percentage?: number;
  break_type?: string;
  clock_in_time?: string;
  total_break_minutes?: number;
  worked_minutes?: number;
  total_distance_km?: number;
  journey_count_today?: number;
  journey_km_today?: number;
  avg_speed_kmh?: number;
  is_last_known?: boolean;
  gps_status?: string;
  gps_status_reason?: string;
  offline_duration_min?: number;
  last_battery_pct?: number;
  app_version?: string;
  app_platform?: string;
  employee?: {
    role_name?: string;
    department_name?: string;
  };
}

type MapView = 'street' | 'satellite' | 'terrain';

export class StaffTeamLiveTrackerPage {
  private container: HTMLElement;
  private locations: LiveLocation[] = [];
  private loading: boolean = true;
  private autoRefresh: boolean = true;
  private refreshInterval: any = null;
  private isDestroyed: boolean = false;
  private map: L.Map | null = null;
  private markers: { [key: number]: L.Marker } = {};
  private currentView: MapView = 'street';
  private tileLayers: { [key: string]: L.TileLayer } = {};
  private selectedEmployeeId: number | null = null;
  private selectedDate: string = new Date().toISOString().split('T')[0];

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    // DC_LIVE_TRACKER_OPEN_MAPS (Feb 2026): Register global function for opening in external maps
    (window as any).openInExternalMaps = (lat: number, lng: number, name: string, mapType: string) => {
      this.openInExternalMaps(lat, lng, name, mapType);
    };
    
    this.render();
    this.initMap();
    await this.loadLocations();
    this.startAutoRefresh();
  }
  
  // DC_LIVE_TRACKER_OPEN_MAPS (Feb 2026): Open employee location in external maps app
  private openInExternalMaps(lat: number, lng: number, name: string, mapType: string): void {
    if (!lat || !lng) {
      alert('Location coordinates not available');
      return;
    }
    
    const encodedName = encodeURIComponent(name || 'Employee Location');
    let url: string;
    
    if (mapType === 'apple') {
      // Apple Maps - works on iOS and opens in Apple Maps app
      url = `https://maps.apple.com/?q=${encodedName}&ll=${lat},${lng}&z=16`;
    } else {
      // Google Maps - works on Android and web, opens in Google Maps app on mobile
      url = `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;
    }
    
    // Open in new tab/app
    window.open(url, '_blank');
  }

  private startAutoRefresh(): void {
    if (this.autoRefresh) {
      this.refreshInterval = setInterval(() => this.loadLocations(), 30000);
    }
  }

  private stopAutoRefresh(): void {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
  }

  cleanup(): void {
    this.isDestroyed = true;
    this.stopAutoRefresh();
    if (this.map) {
      this.map.remove();
      this.map = null;
    }
  }

  private async loadLocations(): Promise<void> {
    if (this.isDestroyed) return;
    try {
      const today = new Date().toISOString().split('T')[0];
      const isToday = this.selectedDate === today;
      
      // DC Protocol (Jan 28, 2026): Use live endpoint for today, history for past dates
      const endpoint = isToday 
        ? '/staff/attendance/location/team/live'
        : `/staff/attendance/location/team/live?date=${this.selectedDate}`;
      
      const response = await apiService.get<any>(endpoint);
      if (this.isDestroyed) return;
      console.log('[StaffTeamLiveTrackerPage] API response:', response);

      if (response.success !== false && response.data) {
        const data = response.data as any;
        this.locations = data.locations || (Array.isArray(data) ? data : []);
        console.log('[StaffTeamLiveTrackerPage] Loaded locations:', this.locations.length);
        console.log('[StaffTeamLiveTrackerPage] Debug info:', data.debug);
        console.log('[StaffTeamLiveTrackerPage] Summary:', data.summary);
        // DC Protocol (Jan 29, 2026): Show debug info in console for troubleshooting
        if (data.debug) {
          console.log(`[DC_DEBUG] User: ${data.debug.user_emp_code}, Team: ${data.debug.team_count}, Attendance: ${data.debug.attendance_count}`);
        }
      } else {
        console.warn('[StaffTeamLiveTrackerPage] No data in response:', response);
        this.locations = [];
      }
      this.loading = false;
      this.updateMap();
      this.updateList();
      this.updateStats();
    } catch (error) {
      if (this.isDestroyed) return;
      console.error('[StaffTeamLiveTrackerPage] Failed to load:', error);
      this.loading = false;
      this.locations = [];
      this.updateList();
    }
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container live-tracker-page">
        ${PageHeader.render({ title: 'Team Live Tracker', showBack: true })}
        
        <div class="date-filter-row compact">
          <input type="date" id="selectedDate" class="form-input" value="${this.selectedDate}" max="${new Date().toISOString().split('T')[0]}">
          <button class="btn btn-primary btn-sm" id="applyDateBtn">Apply</button>
        </div>
        
        <div class="refresh-controls">
          <label class="toggle-label">
            <input type="checkbox" id="autoRefresh" ${this.autoRefresh ? 'checked' : ''}>
            <span>Auto-refresh (30s)</span>
          </label>
          <button class="btn btn-secondary btn-sm" id="refreshNow">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 2v6h-6"/>
              <path d="M3 12a9 9 0 0 1 15-6.7L21 8"/>
              <path d="M3 22v-6h6"/>
              <path d="M21 12a9 9 0 0 1-15 6.7L3 16"/>
            </svg>
            Refresh
          </button>
        </div>

        <div class="stats-row">
          <div class="stat-card mini success">
            <span class="stat-value" id="activeCount">0</span>
            <span class="stat-label">Active</span>
          </div>
          <div class="stat-card mini warning">
            <span class="stat-value" id="breakCount">0</span>
            <span class="stat-label">Break</span>
          </div>
          <div class="stat-card mini info">
            <span class="stat-value" id="journeyCount">0</span>
            <span class="stat-label">Journey</span>
          </div>
          <div class="stat-card mini">
            <span class="stat-value" id="offlineCount">0</span>
            <span class="stat-label">Offline</span>
          </div>
        </div>

        <!-- Map View Controls -->
        <div class="map-view-controls">
          <button class="view-btn active" data-view="street">Street</button>
          <button class="view-btn" data-view="satellite">Satellite</button>
          <button class="view-btn" data-view="terrain">Terrain</button>
        </div>

        <!-- Map Container -->
        <div id="liveTrackerMap" class="live-tracker-map"></div>

        <!-- Employee List Below Map -->
        <div class="list-section-header">
          <span>Team Members</span>
          <span class="badge" id="teamCount">0</span>
        </div>
        <div class="list-container" id="locationsList">
          <div class="loading-state">Loading live locations...</div>
        </div>
      </div>

      <style>
        .live-tracker-page .stats-row {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 8px;
          padding: 12px 16px;
          background: var(--bg-secondary);
        }
        .live-tracker-page .stat-card.mini {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 8px 4px;
          background: var(--bg-primary);
          border-radius: 8px;
          text-align: center;
        }
        .live-tracker-page .stat-card.mini .stat-value {
          font-size: 20px;
          font-weight: 700;
          line-height: 1.2;
        }
        .live-tracker-page .stat-card.mini .stat-label {
          font-size: 10px;
          color: var(--text-secondary);
          margin-top: 2px;
        }
        .live-tracker-page .stat-card.mini.success .stat-value { color: #10b981; }
        .live-tracker-page .stat-card.mini.warning .stat-value { color: #f59e0b; }
        .live-tracker-page .stat-card.mini.info .stat-value { color: #3b82f6; }
        .live-tracker-page .map-view-controls {
          display: flex;
          gap: 8px;
          padding: 8px 16px;
          background: var(--bg-secondary);
        }
        .live-tracker-page .view-btn {
          flex: 1;
          padding: 8px 12px;
          border: 1px solid var(--border-color);
          border-radius: 8px;
          background: var(--bg-primary);
          color: var(--text-secondary);
          font-size: 12px;
          font-weight: 500;
          cursor: pointer;
        }
        .live-tracker-page .view-btn.active {
          background: var(--primary);
          color: white;
          border-color: var(--primary);
        }
        .live-tracker-map {
          height: 280px;
          margin: 0 16px;
          border-radius: 12px;
          overflow: hidden;
          border: 1px solid var(--border-color);
        }
        .list-section-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 16px;
          font-weight: 600;
          color: var(--text-primary);
        }
        .list-section-header .badge {
          background: var(--primary);
          color: white;
          padding: 2px 8px;
          border-radius: 12px;
          font-size: 12px;
        }
        .employee-card {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 16px;
          background: var(--bg-primary);
          border-bottom: 1px solid var(--border-color);
          cursor: pointer;
          transition: background 0.2s;
        }
        .employee-card:active, .employee-card.selected {
          background: var(--bg-secondary);
        }
        .employee-avatar {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 600;
          color: white;
          font-size: 14px;
        }
        .employee-avatar.active { background: #10b981; }
        .employee-avatar.break { background: #f59e0b; }
        .employee-avatar.journey { background: #3b82f6; }
        .employee-avatar.offline { background: #9ca3af; }
        .employee-info { flex: 1; }
        .employee-name { font-weight: 600; color: var(--text-primary); font-size: 14px; }
        .employee-role { font-size: 12px; color: var(--text-secondary); }
        .employee-status { text-align: right; }
        .status-badge {
          padding: 4px 10px;
          border-radius: 20px;
          font-size: 11px;
          font-weight: 600;
        }
        .status-badge.active { background: #dcfce7; color: #166534; }
        .status-badge.break { background: #fef3c7; color: #92400e; }
        .status-badge.journey { background: #dbeafe; color: #1e40af; }
        .status-badge.offline { background: #f3f4f6; color: #6b7280; }
        .last-seen { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
        .battery-indicator { font-size: 11px; margin-left: 8px; }
        .battery-indicator.low { color: #dc2626; }
        .app-version-badge { 
          font-size: 10px; padding: 2px 6px; border-radius: 4px; 
          background: #1e3a5f; color: #64ffda; margin-left: 6px;
        }
        .app-version-badge.unknown { background: #4a3728; color: #ffa500; }
      </style>
    `;

    PageHeader.attachBackHandler();
    this.attachEventListeners();
  }

  private initMap(): void {
    const mapContainer = document.getElementById('liveTrackerMap');
    if (!mapContainer) return;

    this.map = L.map(mapContainer).setView([20.5937, 78.9629], 5);

    // DC_MAP_LAYERS_001: Multiple map layer options
    this.tileLayers['street'] = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap',
      maxZoom: 19
    });

    this.tileLayers['satellite'] = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      attribution: '© Esri',
      maxZoom: 19
    });

    this.tileLayers['terrain'] = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', {
      attribution: '© Esri',
      maxZoom: 19
    });

    this.tileLayers['street'].addTo(this.map);
  }

  private attachEventListeners(): void {
    document.getElementById('autoRefresh')?.addEventListener('change', (e) => {
      this.autoRefresh = (e.target as HTMLInputElement).checked;
      if (this.autoRefresh) {
        this.startAutoRefresh();
      } else {
        this.stopAutoRefresh();
      }
    });

    document.getElementById('refreshNow')?.addEventListener('click', () => {
      this.loading = true;
      this.updateList();
      this.loadLocations();
    });

    // DC Protocol (Jan 28, 2026): Date picker for viewing previous days
    document.getElementById('applyDateBtn')?.addEventListener('click', () => {
      const dateInput = document.getElementById('selectedDate') as HTMLInputElement;
      if (dateInput && dateInput.value) {
        this.selectedDate = dateInput.value;
        const today = new Date().toISOString().split('T')[0];
        // Disable auto-refresh for past dates
        if (this.selectedDate !== today) {
          this.autoRefresh = false;
          this.stopAutoRefresh();
          const checkbox = document.getElementById('autoRefresh') as HTMLInputElement;
          if (checkbox) checkbox.checked = false;
        }
        this.loading = true;
        this.updateList();
        this.loadLocations();
      }
    });

    // View controls
    this.container.querySelectorAll('.view-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const view = (e.currentTarget as HTMLElement).dataset.view as MapView;
        this.switchMapView(view);
      });
    });

    const backBtn = this.container.querySelector('[data-back]');
    backBtn?.addEventListener('click', () => {
      this.stopAutoRefresh();
    });
  }

  private switchMapView(view: MapView): void {
    if (!this.map || view === this.currentView) return;

    // Update buttons
    this.container.querySelectorAll('.view-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-view') === view);
    });

    // Switch tile layer
    if (this.tileLayers[this.currentView]) {
      this.map.removeLayer(this.tileLayers[this.currentView]);
    }
    if (this.tileLayers[view]) {
      this.tileLayers[view].addTo(this.map);
    }
    this.currentView = view;
  }

  private updateStats(): void {
    const active = this.locations.filter(l => this.getStatus(l) === 'active').length;
    const onBreak = this.locations.filter(l => this.getStatus(l) === 'break').length;
    const onJourney = this.locations.filter(l => this.getStatus(l) === 'journey').length;
    const offline = this.locations.filter(l => this.getStatus(l) === 'offline').length;

    const activeEl = document.getElementById('activeCount');
    const breakEl = document.getElementById('breakCount');
    const journeyEl = document.getElementById('journeyCount');
    const offlineEl = document.getElementById('offlineCount');
    const teamEl = document.getElementById('teamCount');

    if (activeEl) activeEl.textContent = active.toString();
    if (breakEl) breakEl.textContent = onBreak.toString();
    if (journeyEl) journeyEl.textContent = onJourney.toString();
    if (offlineEl) offlineEl.textContent = offline.toString();
    if (teamEl) teamEl.textContent = this.locations.length.toString();
  }

  private updateMap(): void {
    if (!this.map) return;

    // Clear existing markers
    Object.values(this.markers).forEach(m => this.map!.removeLayer(m));
    this.markers = {};

    const bounds: L.LatLngTuple[] = [];

    this.locations.forEach(loc => {
      const lat = loc.lat ?? loc.latitude;
      const lng = loc.lng ?? loc.longitude;
      if (!lat || !lng) return;

      const status = this.getStatus(loc);
      const name = loc.name || loc.employee_name || loc.emp_code;
      const color = status === 'journey' ? '#3b82f6' : status === 'break' ? '#f59e0b' : status === 'active' ? '#10b981' : '#9ca3af';

      const icon = L.divIcon({
        className: 'custom-marker',
        html: `<div style="width: 32px; height: 32px; background: ${color}; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 11px;">${this.getInitials(name)}</div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16]
      });

      const marker = L.marker([lat, lng], { icon }).addTo(this.map!);

      // Enhanced popup with all details including travel stats
      const batteryPct = loc.battery_percentage ?? loc.battery_level;
      const clockIn = loc.clock_in_time ? new Date(loc.clock_in_time).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : 'N/A';
      const breakMins = loc.total_break_minutes || 0;
      const breakDisplay = breakMins > 0 ? `${Math.floor(breakMins / 60)}h ${breakMins % 60}m` : 'None';
      const workedMins = loc.worked_minutes || 0;
      const workedDisplay = workedMins > 0 ? `${Math.floor(workedMins / 60)}h ${workedMins % 60}m` : 'N/A';
      const lastUpdate = loc.captured_at || loc.last_update;
      const accuracy = loc.accuracy_m ?? loc.accuracy;
      
      // DC Protocol (Jan 28, 2026): Travel stats
      const totalTravelKm = loc.total_distance_km || 0;
      const journeyCount = loc.journey_count_today || 0;
      const journeyKm = loc.journey_km_today || 0;
      const avgSpeed = loc.avg_speed_kmh || 0;
      const isLastKnown = loc.is_last_known ? ' (last known)' : '';
      
      // DC Protocol (Jan 28, 2026): GPS status and offline reason
      const gpsStatus = loc.gps_status || 'active';
      const gpsReason = loc.gps_status_reason || '';
      const offlineDuration = loc.offline_duration_min || 0;
      const lastBattery = loc.last_battery_pct ?? batteryPct;
      
      // Format GPS status for display
      const gpsStatusLabels: { [key: string]: string } = {
        'active': '✅ Active',
        'permission_denied': '🚫 Permission Denied',
        'gps_disabled': '📍 GPS Off',
        'network_error': '📶 Network Error',
        'app_background': '📱 App Background',
        'location_timeout': '⏱️ GPS Timeout'
      };
      const gpsStatusDisplay = gpsStatusLabels[gpsStatus] || gpsStatus;
      const offlineDurationDisplay = offlineDuration > 0 ? `${offlineDuration} min` : '';

      marker.bindPopup(`
        <div style="min-width: 200px;">
          <strong style="font-size: 13px;">${name}</strong>${isLastKnown ? '<span style="color:#f59e0b;font-size:10px;"> (last known)</span>' : ''}<br>
          <small style="color: #666;">${loc.employee?.role_name || ''}</small>
          <hr style="margin: 6px 0; border-color: #eee;">
          <div style="font-size: 11px; line-height: 1.6;">
            <b>Status:</b> ${status}<br>
            <b>Clock-in:</b> ${clockIn}<br>
            <b>Worked:</b> ${workedDisplay}<br>
            <b>Breaks:</b> ${breakDisplay}<br>
            <hr style="margin: 4px 0; border-color: #eee;">
            <b>Total Travel:</b> ${totalTravelKm.toFixed(2)} km<br>
            <b>Journeys:</b> ${journeyCount} (${journeyKm.toFixed(2)} km)<br>
            <b>Avg Speed:</b> ${avgSpeed.toFixed(1)} km/h<br>
            <hr style="margin: 4px 0; border-color: #eee;">
            <b>GPS:</b> ${gpsStatusDisplay}${offlineDurationDisplay ? ` <span style="color:#f59e0b;">(${offlineDurationDisplay})</span>` : ''}${gpsReason && gpsStatus !== 'active' ? `<br><small style="color:#888;">${gpsReason}</small>` : ''}<br>
            <b>Battery:</b> ${lastBattery != null ? lastBattery + '%' : 'N/A'}<br>
            <b>Accuracy:</b> ${accuracy ? Math.round(accuracy) + 'm' : 'N/A'}<br>
            <b>Updated:</b> ${lastUpdate ? this.formatTimeAgo(lastUpdate) : 'N/A'}
          </div>
          <hr style="margin: 6px 0; border-color: #eee;">
          <div style="display: flex; gap: 8px;">
            <button onclick="window.openInExternalMaps(${lat}, ${lng}, '${name.replace(/'/g, "\\'")}', 'google')" style="flex: 1; padding: 6px 8px; font-size: 10px; background: #fff; border: 1px solid #4285f4; color: #4285f4; border-radius: 4px; cursor: pointer;">
              Google Maps
            </button>
            <button onclick="window.openInExternalMaps(${lat}, ${lng}, '${name.replace(/'/g, "\\'")}', 'apple')" style="flex: 1; padding: 6px 8px; font-size: 10px; background: #fff; border: 1px solid #666; color: #666; border-radius: 4px; cursor: pointer;">
              Apple Maps
            </button>
          </div>
        </div>
      `);

      marker.on('click', () => {
        this.selectEmployee(loc.employee_id);
      });

      this.markers[loc.employee_id] = marker;
      bounds.push([lat, lng]);
    });

    if (bounds.length > 0) {
      if (bounds.length === 1) {
        this.map.setView(bounds[0], 15);
      } else {
        this.map.fitBounds(bounds, { padding: [30, 30] });
      }
    }
  }

  private updateList(): void {
    const listContainer = document.getElementById('locationsList');
    if (!listContainer) return;

    if (this.loading) {
      listContainer.innerHTML = '<div class="loading-state">Loading live locations...</div>';
      return;
    }

    if (this.locations.length === 0) {
      listContainer.innerHTML = '<div class="empty-state">No team members with location data</div>';
      return;
    }

    // Sort: active/journey/break first, offline last
    const sorted = [...this.locations].sort((a, b) => {
      const order: { [key: string]: number } = { journey: 0, active: 1, break: 2, offline: 3 };
      return (order[this.getStatus(a)] || 3) - (order[this.getStatus(b)] || 3);
    });

    listContainer.innerHTML = sorted.map(loc => {
      const status = this.getStatus(loc);
      const name = loc.name || loc.employee_name || loc.emp_code;
      const initials = this.getInitials(name);
      const lastUpdate = loc.captured_at || loc.last_update;
      const batteryPct = loc.last_battery_pct ?? loc.battery_percentage ?? loc.battery_level;
      
      // DC Protocol (Jan 28, 2026): GPS status for offline reasons
      const gpsStatus = loc.gps_status || 'active';
      const offlineDuration = loc.offline_duration_min || 0;
      
      // DC Protocol: Show meaningful status for missing GPS data
      let lastSeenDisplay = lastUpdate ? this.formatTimeAgo(lastUpdate) : 'GPS pending';
      if (!lastUpdate && status === 'active') {
        lastSeenDisplay = 'No GPS data';
      } else if (status === 'offline' && lastUpdate) {
        const d = new Date(lastUpdate);
        lastSeenDisplay = d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }) + ' ' + d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
      } else if (status === 'offline' && !lastUpdate) {
        lastSeenDisplay = 'No data';
      }
      
      // DC Protocol (Jan 28, 2026): Show GPS status reason in offline subtitle
      const gpsReasonIcons: { [key: string]: string } = {
        'permission_denied': '🚫',
        'gps_disabled': '📍',
        'network_error': '📶',
        'app_background': '📱',
        'location_timeout': '⏱️'
      };
      const offlineReasonHtml = gpsStatus !== 'active' && gpsReasonIcons[gpsStatus] 
        ? `<span style="color:#f59e0b;">${gpsReasonIcons[gpsStatus]} ${offlineDuration > 0 ? offlineDuration + 'm' : ''}</span>` 
        : '';

      const batteryHtml = batteryPct != null 
        ? `<span class="battery-indicator ${batteryPct < 20 ? 'low' : ''}">🔋${batteryPct}%</span>` 
        : '';

      const appVersionHtml = loc.app_version 
        ? `<span class="app-version-badge">v${loc.app_version}</span>` 
        : '<span class="app-version-badge unknown">No App</span>';

      return `
        <div class="employee-card ${this.selectedEmployeeId === loc.employee_id ? 'selected' : ''}" data-emp-id="${loc.employee_id}">
          <div class="employee-avatar ${status}">${initials}</div>
          <div class="employee-info">
            <div class="employee-name">${name}${batteryHtml}</div>
            <div class="employee-role">${loc.employee?.role_name || loc.designation || ''} ${appVersionHtml}</div>
          </div>
          <div class="employee-status">
            <span class="status-badge ${status}">${status === 'journey' ? 'Journey' : status === 'break' ? (loc.break_type || 'Break') : status === 'active' ? 'Active' : 'Offline'}</span>
            <div class="last-seen">${status === 'offline' ? 'Last: ' : ''}${lastSeenDisplay} ${offlineReasonHtml}</div>
          </div>
        </div>
      `;
    }).join('');

    // Attach click handlers
    listContainer.querySelectorAll('.employee-card').forEach(card => {
      card.addEventListener('click', () => {
        const empId = parseInt((card as HTMLElement).dataset.empId || '0');
        this.focusEmployee(empId);
      });
    });
  }

  private selectEmployee(empId: number): void {
    this.selectedEmployeeId = empId;
    // Update list selection
    this.container.querySelectorAll('.employee-card').forEach(card => {
      card.classList.toggle('selected', (card as HTMLElement).dataset.empId === empId.toString());
    });
  }

  private focusEmployee(empId: number): void {
    this.selectEmployee(empId);
    const marker = this.markers[empId];
    if (marker && this.map) {
      this.map.setView(marker.getLatLng(), 16);
      marker.openPopup();
    }
  }

  private getStatus(loc: LiveLocation): string {
    if (loc.status) return loc.status === 'on_journey' ? 'journey' : loc.status === 'on_break' ? 'break' : loc.status;
    if (loc.is_on_journey) return 'journey';
    if (loc.is_on_break) return 'break';
    const lastUpdate = loc.captured_at || loc.last_update;
    if (lastUpdate && this.isRecent(lastUpdate)) return 'active';
    return 'offline';
  }

  private isRecent(dateStr: string): boolean {
    if (!dateStr) return false;
    const diff = Date.now() - new Date(dateStr).getTime();
    return diff < 10 * 60 * 1000; // 10 minutes
  }

  private getInitials(name: string): string {
    if (!name) return '??';
    const parts = name.split(' ');
    return parts.length > 1 ? (parts[0][0] + parts[1][0]).toUpperCase() : name.substring(0, 2).toUpperCase();
  }

  private formatTimeAgo(dateStr: string): string {
    if (!dateStr) return 'Unknown';
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return new Date(dateStr).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
  }
}
