/**
 * Journey Route Map Component
 * DC Protocol: DC_MOBILE_MAP_001
 * Displays journey path with track points, start/end markers
 */

interface TrackPoint {
  latitude: number;
  longitude: number;
  accuracy_m: number;
  timestamp: string;
  is_wvv_compliant?: boolean;
}

interface JourneyRoute {
  journey_id: number;
  start_time: string;
  end_time?: string;
  start_location: { latitude: number; longitude: number; address?: string };
  end_location?: { latitude: number; longitude: number; address?: string };
  track_points: TrackPoint[];
  total_distance_km: number;
  duration_minutes: number;
  status: 'active' | 'paused' | 'completed';
}

interface MapConfig {
  containerId: string;
  showControls?: boolean;
  allowPan?: boolean;
  showAccuracyCircles?: boolean;
}

export class JourneyRouteMap {
  private container: HTMLElement | null = null;
  private config: MapConfig;
  private journeyData: JourneyRoute | null = null;
  private canvas: HTMLCanvasElement | null = null;
  private ctx: CanvasRenderingContext2D | null = null;
  private bounds: { minLat: number; maxLat: number; minLng: number; maxLng: number } | null = null;
  private scale: number = 1;
  private offsetX: number = 0;
  private offsetY: number = 0;

  constructor(config: MapConfig) {
    this.config = {
      showControls: true,
      allowPan: true,
      showAccuracyCircles: false,
      ...config
    };
  }

  mount(): void {
    this.container = document.getElementById(this.config.containerId);
    if (!this.container) {
      console.error('[DC_MAP] Container not found:', this.config.containerId);
      return;
    }

    this.render();
  }

  setJourneyData(data: JourneyRoute): void {
    this.journeyData = data;
    this.calculateBounds();
    this.redraw();
  }

  updateLivePosition(point: TrackPoint): void {
    if (this.journeyData) {
      this.journeyData.track_points.push(point);
      this.calculateBounds();
      this.redraw();
    }
  }

  private render(): void {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="journey-map-container">
        <div class="map-header">
          <div class="map-stats" id="mapStats">
            <span class="stat-item">
              <span class="stat-icon">📍</span>
              <span id="pointCount">0</span> points
            </span>
            <span class="stat-item">
              <span class="stat-icon">📏</span>
              <span id="distanceKm">0.0</span> km
            </span>
            <span class="stat-item">
              <span class="stat-icon">⏱️</span>
              <span id="duration">0m</span>
            </span>
          </div>
          ${this.config.showControls ? `
            <div class="map-controls">
              <button class="map-btn" id="zoomIn" title="Zoom In">+</button>
              <button class="map-btn" id="zoomOut" title="Zoom Out">−</button>
              <button class="map-btn" id="fitBounds" title="Fit Route">⬜</button>
            </div>
          ` : ''}
        </div>
        
        <div class="map-canvas-wrapper">
          <canvas id="journeyCanvas"></canvas>
          <div class="map-legend">
            <div class="legend-item">
              <span class="legend-marker start"></span> Start
            </div>
            <div class="legend-item">
              <span class="legend-marker end"></span> End
            </div>
            <div class="legend-item">
              <span class="legend-line"></span> Route
            </div>
          </div>
        </div>
        
        <div class="map-info" id="mapInfo">
          <p class="no-data">No journey data loaded</p>
        </div>
      </div>
    `;

    this.setupCanvas();
    this.attachEventListeners();
    this.addStyles();
  }

  private setupCanvas(): void {
    this.canvas = document.getElementById('journeyCanvas') as HTMLCanvasElement;
    if (!this.canvas) return;

    const wrapper = this.canvas.parentElement;
    if (wrapper) {
      this.canvas.width = wrapper.clientWidth;
      this.canvas.height = 300;
    }

    this.ctx = this.canvas.getContext('2d');
  }

  private attachEventListeners(): void {
    document.getElementById('zoomIn')?.addEventListener('click', () => this.zoom(1.2));
    document.getElementById('zoomOut')?.addEventListener('click', () => this.zoom(0.8));
    document.getElementById('fitBounds')?.addEventListener('click', () => this.fitBounds());

    if (this.config.allowPan && this.canvas) {
      let isDragging = false;
      let lastX = 0;
      let lastY = 0;

      this.canvas.addEventListener('mousedown', (e) => {
        isDragging = true;
        lastX = e.clientX;
        lastY = e.clientY;
      });

      this.canvas.addEventListener('mousemove', (e) => {
        if (isDragging) {
          this.offsetX += e.clientX - lastX;
          this.offsetY += e.clientY - lastY;
          lastX = e.clientX;
          lastY = e.clientY;
          this.redraw();
        }
      });

      this.canvas.addEventListener('mouseup', () => isDragging = false);
      this.canvas.addEventListener('mouseleave', () => isDragging = false);

      this.canvas.addEventListener('touchstart', (e) => {
        if (e.touches.length === 1) {
          isDragging = true;
          lastX = e.touches[0].clientX;
          lastY = e.touches[0].clientY;
        }
      });

      this.canvas.addEventListener('touchmove', (e) => {
        if (isDragging && e.touches.length === 1) {
          this.offsetX += e.touches[0].clientX - lastX;
          this.offsetY += e.touches[0].clientY - lastY;
          lastX = e.touches[0].clientX;
          lastY = e.touches[0].clientY;
          this.redraw();
        }
      });

      this.canvas.addEventListener('touchend', () => isDragging = false);
    }
  }

  private calculateBounds(): void {
    if (!this.journeyData || this.journeyData.track_points.length === 0) {
      this.bounds = null;
      return;
    }

    const points = this.journeyData.track_points;
    let minLat = points[0].latitude;
    let maxLat = points[0].latitude;
    let minLng = points[0].longitude;
    let maxLng = points[0].longitude;

    for (const point of points) {
      minLat = Math.min(minLat, point.latitude);
      maxLat = Math.max(maxLat, point.latitude);
      minLng = Math.min(minLng, point.longitude);
      maxLng = Math.max(maxLng, point.longitude);
    }

    const latPadding = (maxLat - minLat) * 0.1 || 0.001;
    const lngPadding = (maxLng - minLng) * 0.1 || 0.001;

    this.bounds = {
      minLat: minLat - latPadding,
      maxLat: maxLat + latPadding,
      minLng: minLng - lngPadding,
      maxLng: maxLng + lngPadding
    };
  }

  private latLngToCanvas(lat: number, lng: number): { x: number; y: number } {
    if (!this.bounds || !this.canvas) return { x: 0, y: 0 };

    const latRange = this.bounds.maxLat - this.bounds.minLat;
    const lngRange = this.bounds.maxLng - this.bounds.minLng;

    const x = ((lng - this.bounds.minLng) / lngRange) * this.canvas.width * this.scale + this.offsetX;
    const y = ((this.bounds.maxLat - lat) / latRange) * this.canvas.height * this.scale + this.offsetY;

    return { x, y };
  }

  private redraw(): void {
    if (!this.ctx || !this.canvas) return;

    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    this.drawGrid();

    if (!this.journeyData || this.journeyData.track_points.length === 0) {
      this.drawNoData();
      return;
    }

    this.drawRoute();
    this.drawMarkers();
    this.updateStats();
  }

  private drawGrid(): void {
    if (!this.ctx || !this.canvas) return;

    this.ctx.strokeStyle = '#2a2a3e';
    this.ctx.lineWidth = 1;

    for (let x = 0; x < this.canvas.width; x += 50) {
      this.ctx.beginPath();
      this.ctx.moveTo(x, 0);
      this.ctx.lineTo(x, this.canvas.height);
      this.ctx.stroke();
    }

    for (let y = 0; y < this.canvas.height; y += 50) {
      this.ctx.beginPath();
      this.ctx.moveTo(0, y);
      this.ctx.lineTo(this.canvas.width, y);
      this.ctx.stroke();
    }
  }

  private drawNoData(): void {
    if (!this.ctx || !this.canvas) return;

    this.ctx.fillStyle = '#888';
    this.ctx.font = '16px sans-serif';
    this.ctx.textAlign = 'center';
    this.ctx.fillText('No route data available', this.canvas.width / 2, this.canvas.height / 2);
  }

  private drawRoute(): void {
    if (!this.ctx || !this.journeyData) return;

    const points = this.journeyData.track_points;
    if (points.length < 2) return;

    this.ctx.strokeStyle = '#4CAF50';
    this.ctx.lineWidth = 3;
    this.ctx.lineCap = 'round';
    this.ctx.lineJoin = 'round';

    this.ctx.beginPath();
    const start = this.latLngToCanvas(points[0].latitude, points[0].longitude);
    this.ctx.moveTo(start.x, start.y);

    for (let i = 1; i < points.length; i++) {
      const point = this.latLngToCanvas(points[i].latitude, points[i].longitude);
      this.ctx.lineTo(point.x, point.y);
    }

    this.ctx.stroke();

    if (this.config.showAccuracyCircles) {
      this.ctx.strokeStyle = 'rgba(76, 175, 80, 0.3)';
      this.ctx.lineWidth = 1;

      for (const point of points) {
        const pos = this.latLngToCanvas(point.latitude, point.longitude);
        const radius = Math.max(3, point.accuracy_m / 10);
        
        this.ctx.beginPath();
        this.ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
        this.ctx.stroke();
      }
    }
  }

  private drawMarkers(): void {
    if (!this.ctx || !this.journeyData) return;

    const points = this.journeyData.track_points;
    if (points.length === 0) return;

    const startPos = this.latLngToCanvas(points[0].latitude, points[0].longitude);
    this.ctx.fillStyle = '#4CAF50';
    this.ctx.beginPath();
    this.ctx.arc(startPos.x, startPos.y, 10, 0, Math.PI * 2);
    this.ctx.fill();
    this.ctx.fillStyle = '#fff';
    this.ctx.font = 'bold 12px sans-serif';
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'middle';
    this.ctx.fillText('S', startPos.x, startPos.y);

    if (points.length > 1) {
      const endPoint = points[points.length - 1];
      const endPos = this.latLngToCanvas(endPoint.latitude, endPoint.longitude);
      
      const endColor = this.journeyData.status === 'completed' ? '#f44336' : '#FF9800';
      this.ctx.fillStyle = endColor;
      this.ctx.beginPath();
      this.ctx.arc(endPos.x, endPos.y, 10, 0, Math.PI * 2);
      this.ctx.fill();
      this.ctx.fillStyle = '#fff';
      this.ctx.fillText(this.journeyData.status === 'completed' ? 'E' : '●', endPos.x, endPos.y);
    }
  }

  private updateStats(): void {
    if (!this.journeyData) return;

    const pointCount = document.getElementById('pointCount');
    const distanceKm = document.getElementById('distanceKm');
    const duration = document.getElementById('duration');

    if (pointCount) pointCount.textContent = String(this.journeyData.track_points.length);
    if (distanceKm) distanceKm.textContent = this.journeyData.total_distance_km.toFixed(2);
    if (duration) duration.textContent = `${this.journeyData.duration_minutes}m`;

    const mapInfo = document.getElementById('mapInfo');
    if (mapInfo && this.journeyData.track_points.length > 0) {
      const start = this.journeyData.start_location;
      const end = this.journeyData.end_location;
      
      mapInfo.innerHTML = `
        <div class="info-row">
          <span class="info-label">Start:</span>
          <span class="info-value">${start.address || `${start.latitude.toFixed(5)}, ${start.longitude.toFixed(5)}`}</span>
        </div>
        ${end ? `
          <div class="info-row">
            <span class="info-label">End:</span>
            <span class="info-value">${end.address || `${end.latitude.toFixed(5)}, ${end.longitude.toFixed(5)}`}</span>
          </div>
        ` : ''}
        <div class="info-row">
          <span class="info-label">Status:</span>
          <span class="info-value status-${this.journeyData.status}">${this.journeyData.status}</span>
        </div>
      `;
    }
  }

  private zoom(factor: number): void {
    this.scale *= factor;
    this.scale = Math.max(0.5, Math.min(5, this.scale));
    this.redraw();
  }

  private fitBounds(): void {
    this.scale = 1;
    this.offsetX = 0;
    this.offsetY = 0;
    this.redraw();
  }

  private addStyles(): void {
    if (document.getElementById('journey-map-styles')) return;

    const style = document.createElement('style');
    style.id = 'journey-map-styles';
    style.textContent = `
      .journey-map-container {
        background: #1a1a2e;
        border-radius: 12px;
        overflow: hidden;
      }

      .map-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 16px;
        background: #16213e;
        border-bottom: 1px solid #2a2a3e;
      }

      .map-stats {
        display: flex;
        gap: 16px;
      }

      .stat-item {
        display: flex;
        align-items: center;
        gap: 4px;
        color: #ccc;
        font-size: 14px;
      }

      .stat-icon {
        font-size: 16px;
      }

      .map-controls {
        display: flex;
        gap: 8px;
      }

      .map-btn {
        width: 32px;
        height: 32px;
        border: none;
        border-radius: 6px;
        background: #2a2a3e;
        color: #fff;
        font-size: 18px;
        cursor: pointer;
        transition: background 0.2s;
      }

      .map-btn:hover {
        background: #3a3a4e;
      }

      .map-canvas-wrapper {
        position: relative;
        background: #1a1a2e;
      }

      #journeyCanvas {
        display: block;
        width: 100%;
        cursor: grab;
      }

      #journeyCanvas:active {
        cursor: grabbing;
      }

      .map-legend {
        position: absolute;
        bottom: 12px;
        right: 12px;
        background: rgba(22, 33, 62, 0.9);
        padding: 8px 12px;
        border-radius: 8px;
        display: flex;
        gap: 12px;
      }

      .legend-item {
        display: flex;
        align-items: center;
        gap: 6px;
        color: #ccc;
        font-size: 12px;
      }

      .legend-marker {
        width: 12px;
        height: 12px;
        border-radius: 50%;
      }

      .legend-marker.start {
        background: #4CAF50;
      }

      .legend-marker.end {
        background: #f44336;
      }

      .legend-line {
        width: 20px;
        height: 3px;
        background: #4CAF50;
        border-radius: 2px;
      }

      .map-info {
        padding: 12px 16px;
        border-top: 1px solid #2a2a3e;
      }

      .info-row {
        display: flex;
        justify-content: space-between;
        padding: 4px 0;
        font-size: 13px;
      }

      .info-label {
        color: #888;
      }

      .info-value {
        color: #fff;
      }

      .status-active {
        color: #4CAF50;
      }

      .status-paused {
        color: #FF9800;
      }

      .status-completed {
        color: #f44336;
      }

      .no-data {
        color: #666;
        text-align: center;
        margin: 0;
      }
    `;
    document.head.appendChild(style);
  }

  destroy(): void {
    if (this.container) {
      this.container.innerHTML = '';
    }
    this.canvas = null;
    this.ctx = null;
    this.journeyData = null;
  }
}
