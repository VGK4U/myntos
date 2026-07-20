/**
 * Staff Location History Page
 * DC Protocol: DC_MOBILE_STAFF_LOCATION_001
 * View GPS location history with timestamps
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface LocationPoint {
  id: number;
  latitude: number;
  longitude: number;
  accuracy: number;
  timestamp: string;
  battery_level: number | null;
  activity_type: string | null;
}

export class LocationHistoryPage {
  private container: HTMLElement;
  private locations: LocationPoint[] = [];
  private loading: boolean = true;
  private selectedDate: string = '';

  constructor(container: HTMLElement) {
    this.container = container;
    const now = new Date();
    this.selectedDate = now.toISOString().split('T')[0];
  }

  async init(): Promise<void> {
    this.render();
    await this.loadLocations();
  }

  private async loadLocations(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<any>(`/staff/attendance/location/history?date=${this.selectedDate}`);
      if (response.success && response.data) {
        this.locations = response.data.locations || response.data || [];
      }
    } catch (error) {
      console.error('[LocationHistory] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Location History', showBack: true })}
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: 'Location History', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    content.innerHTML = `
      <div class="date-picker card">
        <input type="date" id="datePicker" value="${this.selectedDate}" class="form-input">
      </div>

      <div class="location-summary card">
        <div class="summary-grid">
          <div class="summary-item">
            <span class="summary-value">${this.locations.length}</span>
            <span class="summary-label">Points</span>
          </div>
          <div class="summary-item">
            <span class="summary-value">${this.calculateDistance()}</span>
            <span class="summary-label">km Traveled</span>
          </div>
        </div>
      </div>

      <h4 class="section-title">Location Timeline</h4>
      ${this.locations.length > 0 ? `
        <div class="location-timeline">
          ${this.locations.map((loc, idx) => this.renderLocationPoint(loc, idx)).join('')}
        </div>
      ` : `
        <div class="empty-state card">
          <div class="empty-icon">📍</div>
          <p>No location data for this date</p>
        </div>
      `}
    `;

    document.getElementById('datePicker')?.addEventListener('change', (e) => {
      this.selectedDate = (e.target as HTMLInputElement).value;
      this.loadLocations();
    });
  }

  private renderLocationPoint(loc: LocationPoint, index: number): string {
    const time = new Date(loc.timestamp).toLocaleTimeString('en', { 
      hour: '2-digit', minute: '2-digit' 
    });
    const accuracyClass = loc.accuracy <= 100 ? 'high' : loc.accuracy <= 500 ? 'medium' : 'low';

    return `
      <div class="timeline-item">
        <div class="timeline-marker ${accuracyClass}"></div>
        <div class="timeline-content card">
          <div class="timeline-time">${time}</div>
          <div class="timeline-coords">
            ${loc.latitude.toFixed(6)}, ${loc.longitude.toFixed(6)}
          </div>
          <div class="timeline-meta">
            <span class="accuracy ${accuracyClass}">±${Math.round(loc.accuracy)}m</span>
            ${loc.battery_level ? `<span class="battery">🔋 ${loc.battery_level}%</span>` : ''}
          </div>
        </div>
      </div>
    `;
  }

  private calculateDistance(): string {
    if (this.locations.length < 2) return '0.0';
    
    let total = 0;
    for (let i = 1; i < this.locations.length; i++) {
      total += this.haversine(
        this.locations[i - 1].latitude, this.locations[i - 1].longitude,
        this.locations[i].latitude, this.locations[i].longitude
      );
    }
    return total.toFixed(1);
  }

  private haversine(lat1: number, lon1: number, lat2: number, lon2: number): number {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }
}
