/**
 * Enhanced Journey Map Component using Leaflet
 * DC Protocol: DC_MOBILE_LEAFLET_MAP_001
 * Supports satellite, street, and traffic view options like Google Maps
 */

import L from 'leaflet';

interface TrackPoint {
  latitude: number;
  longitude: number;
  accuracy_m?: number;
  timestamp?: string;
  address?: string;
  battery_percentage?: number;
}

interface JourneyStop {
  address: string;
  durationMinutes: number;
  startIndex: number;
}

interface MapOptions {
  containerId: string;
  trackPoints: TrackPoint[];
  stops?: JourneyStop[];
  onViewChange?: (view: string) => void;
  hidePlaybackControls?: boolean;
}

type MapView = 'street' | 'satellite' | 'terrain';

export class LeafletJourneyMap {
  private map: L.Map | null = null;
  private container: HTMLElement | null = null;
  private trackPoints: TrackPoint[] = [];
  private stops: JourneyStop[] = [];
  private routeLine: L.Polyline | null = null;
  private progressLine: L.Polyline | null = null;
  private currentMarker: L.CircleMarker | null = null;
  private startMarker: L.Marker | null = null;
  private endMarker: L.Marker | null = null;
  private stopMarkers: L.Marker[] = [];
  private currentView: MapView = 'street';
  private tileLayers: { [key: string]: L.TileLayer } = {};
  private playbackIndex: number = 0;
  private isPlaying: boolean = false;
  private playbackInterval: any = null;
  private playbackSpeed: number = 2;
  private onViewChange?: (view: string) => void;
  
  // DC_GEOCODE_004: Address cache for playback location names
  private addressCache: Map<string, string> = new Map();

  constructor(private options: MapOptions) {
    this.trackPoints = options.trackPoints;
    this.stops = options.stops || [];
    this.onViewChange = options.onViewChange;
  }

  mount(): void {
    this.container = document.getElementById(this.options.containerId);
    if (!this.container) {
      console.error('[LeafletMap] Container not found:', this.options.containerId);
      return;
    }

    this.render();
    this.initMap();
  }

  private render(): void {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="leaflet-journey-map">
        <div class="map-view-controls">
          <button class="view-btn active" data-view="street" title="Street View">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 12h18M3 6h18M3 18h18"/>
            </svg>
            <span>Street</span>
          </button>
          <button class="view-btn" data-view="satellite" title="Satellite View">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M2 12h20M12 2a10 10 0 0110 10"/>
            </svg>
            <span>Satellite</span>
          </button>
          <button class="view-btn" data-view="terrain" title="Terrain View">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M8 20L12 10l4 10M12 10l8-6M12 10L4 4"/>
            </svg>
            <span>Terrain</span>
          </button>
        </div>
        <div id="leafletMapView" class="leaflet-map-view"></div>
        <div class="map-legend-overlay">
          <span class="legend-item"><span class="dot start"></span>Start</span>
          <span class="legend-item"><span class="dot end"></span>End</span>
          <span class="legend-item"><span class="dot stop"></span>Stops</span>
        </div>
      </div>
      
      ${!this.options.hidePlaybackControls ? `
      <div class="playback-section">
        <h5 class="section-label">Route Playback</h5>
        <div class="playback-controls-enhanced">
          <button id="playPauseBtn" class="playback-btn-lg play" title="Play">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
          </button>
          <button id="resetPlayback" class="playback-btn-sm" title="Reset">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 12a9 9 0 019-9 9 9 0 016.36 2.64L21 3v6h-6l2.64-2.64A7 7 0 0012 5a7 7 0 00-7 7 7 7 0 007 7 7 7 0 005.66-2.88"/>
            </svg>
          </button>
          <div class="slider-container">
            <input type="range" id="playbackSlider" class="playback-slider-enhanced" min="0" max="${this.trackPoints.length - 1}" value="0">
            <div class="slider-progress" id="sliderProgress"></div>
          </div>
          <div class="speed-selector">
            <button id="speedBtn" class="speed-btn">2x</button>
          </div>
        </div>
        <div class="playback-info-bar">
          <span id="currentLocation" class="current-loc">--</span>
          <span id="playbackCounter" class="counter">${this.playbackIndex + 1} / ${this.trackPoints.length}</span>
        </div>
      </div>
      ` : ''}
    `;

    this.addStyles();
    this.attachEventListeners();
  }

  private initMap(): void {
    if (this.trackPoints.length === 0) return;

    const mapEl = document.getElementById('leafletMapView');
    if (!mapEl) return;

    const center = this.trackPoints[0];
    this.map = L.map('leafletMapView', {
      zoomControl: false,
      attributionControl: false
    }).setView([center.latitude, center.longitude], 14);

    L.control.zoom({ position: 'topright' }).addTo(this.map);

    this.tileLayers = {
      street: L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19
      }),
      satellite: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19
      }),
      terrain: L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
        maxZoom: 17
      })
    };

    this.tileLayers.street.addTo(this.map);
    this.drawRoute();
    this.fitBounds();
  }

  private drawRoute(): void {
    if (!this.map || this.trackPoints.length < 2) return;

    const latLngs = this.trackPoints.map(p => [p.latitude, p.longitude] as [number, number]);

    this.routeLine = L.polyline(latLngs, {
      color: 'rgba(255,255,255,0.3)',
      weight: 4,
      dashArray: '8, 8'
    }).addTo(this.map);

    this.progressLine = L.polyline([], {
      color: '#00d09c',
      weight: 5,
      lineCap: 'round',
      lineJoin: 'round'
    }).addTo(this.map);

    const startIcon = L.divIcon({
      className: 'custom-marker start-marker',
      html: '<div class="marker-inner">S</div>',
      iconSize: [28, 28],
      iconAnchor: [14, 14]
    });

    const endIcon = L.divIcon({
      className: 'custom-marker end-marker',
      html: '<div class="marker-inner">E</div>',
      iconSize: [28, 28],
      iconAnchor: [14, 14]
    });

    const startPoint = this.trackPoints[0];
    const startBattery = startPoint.battery_percentage !== undefined ? `<br>🔋 ${startPoint.battery_percentage}%` : '';
    this.startMarker = L.marker([startPoint.latitude, startPoint.longitude], { icon: startIcon })
      .bindPopup(`<b>Start Point</b><br>${startPoint.address || 'Journey Start'}${startBattery}`)
      .addTo(this.map);

    const endPoint = this.trackPoints[this.trackPoints.length - 1];
    const endBattery = endPoint.battery_percentage !== undefined ? `<br>🔋 ${endPoint.battery_percentage}%` : '';
    this.endMarker = L.marker([endPoint.latitude, endPoint.longitude], { icon: endIcon })
      .bindPopup(`<b>End Point</b><br>${endPoint.address || 'Journey End'}${endBattery}`)
      .addTo(this.map);

    this.stops.forEach((stop, idx) => {
      const point = this.trackPoints[stop.startIndex];
      if (point) {
        const stopIcon = L.divIcon({
          className: 'custom-marker stop-marker',
          html: `<div class="marker-inner">${idx + 1}</div>`,
          iconSize: [24, 24],
          iconAnchor: [12, 12]
        });

        const marker = L.marker([point.latitude, point.longitude], { icon: stopIcon })
          .bindPopup(`<b>Stop ${idx + 1}</b><br>${stop.address || 'Unknown location'}<br>Duration: ${this.formatDuration(stop.durationMinutes)}`)
          .addTo(this.map!);

        this.stopMarkers.push(marker);
      }
    });

    this.currentMarker = L.circleMarker([startPoint.latitude, startPoint.longitude], {
      radius: 10,
      color: '#fff',
      weight: 3,
      fillColor: '#ffc107',
      fillOpacity: 1
    }).addTo(this.map);
  }

  private fitBounds(): void {
    if (!this.map || !this.routeLine) return;
    this.map.fitBounds(this.routeLine.getBounds(), { padding: [30, 30] });
  }

  private switchView(view: MapView): void {
    if (!this.map || this.currentView === view) return;

    this.tileLayers[this.currentView].remove();
    this.tileLayers[view].addTo(this.map);
    this.currentView = view;

    document.querySelectorAll('.view-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-view') === view);
    });

    if (this.onViewChange) this.onViewChange(view);
  }

  private attachEventListeners(): void {
    document.querySelectorAll('.view-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const view = btn.getAttribute('data-view') as MapView;
        this.switchView(view);
      });
    });

    document.getElementById('playPauseBtn')?.addEventListener('click', () => this.togglePlayback());
    document.getElementById('resetPlayback')?.addEventListener('click', () => this.resetPlayback());

    const slider = document.getElementById('playbackSlider') as HTMLInputElement;
    slider?.addEventListener('input', () => {
      this.playbackIndex = parseInt(slider.value);
      this.updatePlaybackUI();
    });

    document.getElementById('speedBtn')?.addEventListener('click', () => this.cycleSpeed());
  }

  private togglePlayback(): void {
    const btn = document.getElementById('playPauseBtn');
    if (this.isPlaying) {
      this.stopPlayback();
      if (btn) {
        btn.innerHTML = `<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>`;
        btn.classList.remove('pause');
        btn.classList.add('play');
      }
    } else {
      this.startPlayback();
      if (btn) {
        btn.innerHTML = `<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>`;
        btn.classList.remove('play');
        btn.classList.add('pause');
      }
    }
    this.isPlaying = !this.isPlaying;
  }

  private startPlayback(): void {
    const interval = 500 / this.playbackSpeed;
    this.playbackInterval = setInterval(() => {
      if (this.playbackIndex < this.trackPoints.length - 1) {
        this.playbackIndex++;
        this.updatePlaybackUI();
      } else {
        this.stopPlayback();
        this.isPlaying = false;
        const btn = document.getElementById('playPauseBtn');
        if (btn) {
          btn.innerHTML = `<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>`;
          btn.classList.remove('pause');
          btn.classList.add('play');
        }
      }
    }, interval);
  }

  private stopPlayback(): void {
    if (this.playbackInterval) {
      clearInterval(this.playbackInterval);
      this.playbackInterval = null;
    }
  }

  private resetPlayback(): void {
    this.stopPlayback();
    this.playbackIndex = 0;
    this.isPlaying = false;
    const btn = document.getElementById('playPauseBtn');
    if (btn) {
      btn.innerHTML = `<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>`;
      btn.classList.remove('pause');
      btn.classList.add('play');
    }
    this.updatePlaybackUI();
  }

  private cycleSpeed(): void {
    const speeds = [1, 2, 4, 8];
    const currentIdx = speeds.indexOf(this.playbackSpeed);
    this.playbackSpeed = speeds[(currentIdx + 1) % speeds.length];
    const btn = document.getElementById('speedBtn');
    if (btn) btn.textContent = `${this.playbackSpeed}x`;

    if (this.isPlaying) {
      this.stopPlayback();
      this.startPlayback();
    }
  }

  private updatePlaybackUI(): void {
    const slider = document.getElementById('playbackSlider') as HTMLInputElement;
    const counter = document.getElementById('playbackCounter');
    const locEl = document.getElementById('currentLocation');
    const progressEl = document.getElementById('sliderProgress');

    if (slider) slider.value = String(this.playbackIndex);
    if (counter) counter.textContent = `${this.playbackIndex + 1} / ${this.trackPoints.length}`;

    const point = this.trackPoints[this.playbackIndex];
    if (locEl && point) {
      // DC_GEOCODE_005: Show location name instead of coordinates during playback
      if (point.address) {
        locEl.textContent = point.address;
      } else {
        locEl.textContent = 'Loading...';
        this.reverseGeocodeForPlayback(point.latitude, point.longitude, locEl);
      }
    }

    const percent = (this.playbackIndex / (this.trackPoints.length - 1)) * 100;
    if (progressEl) progressEl.style.width = `${percent}%`;

    if (this.currentMarker && point) {
      this.currentMarker.setLatLng([point.latitude, point.longitude]);
    }

    if (this.progressLine) {
      const progressLatLngs = this.trackPoints.slice(0, this.playbackIndex + 1).map(p => [p.latitude, p.longitude] as [number, number]);
      this.progressLine.setLatLngs(progressLatLngs);
    }

    if (this.map && point) {
      this.map.panTo([point.latitude, point.longitude], { animate: true, duration: 0.3 });
    }
  }

  // DC_GEOCODE_006: Reverse geocode for playback with caching
  private async reverseGeocodeForPlayback(lat: number, lng: number, element: HTMLElement): Promise<void> {
    const cacheKey = `${lat.toFixed(4)},${lng.toFixed(4)}`;
    
    // Check cache first
    if (this.addressCache.has(cacheKey)) {
      element.textContent = this.addressCache.get(cacheKey)!;
      return;
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
        
        // Update element if still showing this point
        if (element.textContent === 'Loading...') {
          element.textContent = locationName;
        }
      }
    } catch (err) {
      console.warn('[DC_GEOCODE] Playback geocode failed:', err);
      if (element.textContent === 'Loading...') {
        element.textContent = `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
      }
    }
  }

  private formatDuration(minutes: number): string {
    if (minutes < 60) return `${Math.round(minutes)}m`;
    const hours = Math.floor(minutes / 60);
    const mins = Math.round(minutes % 60);
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  }

  private addStyles(): void {
    if (document.getElementById('leaflet-journey-map-styles')) return;

    const style = document.createElement('style');
    style.id = 'leaflet-journey-map-styles';
    style.textContent = `
      .leaflet-journey-map {
        position: relative;
        border-radius: 12px;
        overflow: hidden;
        background: #1a1a2e;
      }

      .map-view-controls {
        display: flex;
        gap: 4px;
        padding: 8px 12px;
        background: linear-gradient(180deg, rgba(26,26,46,0.95) 0%, rgba(26,26,46,0.8) 100%);
        border-bottom: 1px solid rgba(255,255,255,0.1);
      }

      .view-btn {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 8px 12px;
        border: none;
        border-radius: 8px;
        background: rgba(255,255,255,0.1);
        color: rgba(255,255,255,0.7);
        font-size: 12px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
      }

      .view-btn:hover {
        background: rgba(255,255,255,0.15);
      }

      .view-btn.active {
        background: linear-gradient(135deg, #00d09c 0%, #00b386 100%);
        color: white;
      }

      .leaflet-map-view {
        height: 280px;
        background: #16213e;
      }

      .map-legend-overlay {
        position: absolute;
        bottom: 10px;
        left: 10px;
        display: flex;
        gap: 12px;
        padding: 6px 10px;
        background: rgba(26,26,46,0.9);
        border-radius: 6px;
        font-size: 11px;
        color: rgba(255,255,255,0.8);
        z-index: 1000;
      }

      .legend-item {
        display: flex;
        align-items: center;
        gap: 4px;
      }

      .legend-item .dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
      }

      .dot.start { background: #4CAF50; }
      .dot.end { background: #f44336; }
      .dot.stop { background: #ff9800; }

      .custom-marker {
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .custom-marker .marker-inner {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 100%;
        border-radius: 50%;
        font-weight: bold;
        font-size: 12px;
        color: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      }

      .start-marker .marker-inner {
        background: #4CAF50;
      }

      .end-marker .marker-inner {
        background: #f44336;
      }

      .stop-marker .marker-inner {
        background: #ff9800;
        font-size: 10px;
      }

      .playback-section {
        padding: 16px;
        background: rgba(22, 33, 62, 0.5);
        border-top: 1px solid rgba(255,255,255,0.1);
      }

      .section-label {
        font-size: 13px;
        font-weight: 600;
        color: rgba(255,255,255,0.9);
        margin-bottom: 12px;
      }

      .playback-controls-enhanced {
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .playback-btn-lg {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        border: none;
        background: linear-gradient(135deg, #00d09c 0%, #00b386 100%);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(0, 208, 156, 0.3);
        transition: all 0.2s;
      }

      .playback-btn-lg:hover {
        transform: scale(1.05);
      }

      .playback-btn-lg.pause {
        background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
        box-shadow: 0 4px 12px rgba(255, 152, 0, 0.3);
      }

      .playback-btn-sm {
        width: 36px;
        height: 36px;
        border-radius: 8px;
        border: none;
        background: rgba(255,255,255,0.1);
        color: rgba(255,255,255,0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: background 0.2s;
      }

      .playback-btn-sm:hover {
        background: rgba(255,255,255,0.2);
      }

      .slider-container {
        flex: 1;
        position: relative;
        height: 6px;
        background: rgba(255,255,255,0.15);
        border-radius: 3px;
        overflow: hidden;
      }

      .playback-slider-enhanced {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        opacity: 0;
        cursor: pointer;
        z-index: 2;
      }

      .slider-progress {
        position: absolute;
        top: 0;
        left: 0;
        height: 100%;
        background: linear-gradient(90deg, #00d09c 0%, #00b386 100%);
        border-radius: 3px;
        transition: width 0.1s;
      }

      .speed-selector {
        display: flex;
        align-items: center;
      }

      .speed-btn {
        padding: 6px 12px;
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.2);
        background: transparent;
        color: rgba(255,255,255,0.9);
        font-size: 12px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
      }

      .speed-btn:hover {
        background: rgba(255,255,255,0.1);
        border-color: rgba(255,255,255,0.3);
      }

      .playback-info-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 12px;
        padding-top: 12px;
        border-top: 1px solid rgba(255,255,255,0.1);
      }

      .current-loc {
        font-size: 12px;
        color: rgba(255,255,255,0.7);
        max-width: 70%;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .counter {
        font-size: 12px;
        color: rgba(255,255,255,0.5);
        font-weight: 500;
      }
    `;
    document.head.appendChild(style);
  }

  // DC Protocol (Feb 02, 2026): External playback control for Team Journeys
  setPlaybackIndex(index: number): void {
    if (index < 0 || index >= this.trackPoints.length) return;
    this.playbackIndex = index;
    this.updatePlaybackUI();
  }

  // DC Protocol (Feb 02, 2026): Get current playback state
  getPlaybackState(): { index: number; total: number; isPlaying: boolean } {
    return {
      index: this.playbackIndex,
      total: this.trackPoints.length,
      isPlaying: this.isPlaying
    };
  }

  destroy(): void {
    this.stopPlayback();
    if (this.map) {
      this.map.remove();
      this.map = null;
    }
  }
}
