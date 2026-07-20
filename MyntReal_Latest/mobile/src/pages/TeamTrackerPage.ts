/**
 * Staff Team Tracker Page
 * DC Protocol: DC_MOBILE_STAFF_TRACKER_001
 * Live GPS tracking of team members
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface TeamLocation {
  id: number;
  employee_name: string;
  emp_code: string;
  latitude: number;
  longitude: number;
  accuracy: number;
  last_update: string;
  status: 'online' | 'offline' | 'stale';
  battery_level: number | null;
  is_clocked_in: boolean;
  has_active_journey: boolean;
}

export class TeamTrackerPage {
  private container: HTMLElement;
  private teamLocations: TeamLocation[] = [];
  private loading: boolean = true;
  private refreshInterval: any = null;
  private isDestroyed: boolean = false;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadTeamLocations();
    this.startAutoRefresh();
  }

  destroy(): void {
    this.isDestroyed = true;
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
  }

  cleanup(): void {
    this.destroy();
  }

  private startAutoRefresh(): void {
    this.refreshInterval = setInterval(() => this.loadTeamLocations(), 30000);
  }

  private async loadTeamLocations(): Promise<void> {
    if (this.isDestroyed) return;
    try {
      // DC Protocol: Match web's endpoint exactly
      const response = await apiService.get<any>('/staff/attendance/location/team/live');
      if (this.isDestroyed) return;
      if (response.success && response.data) {
        this.teamLocations = response.data.locations || response.data || [];
        this.updateContent();
      }
    } catch (error) {
      console.error('[TeamTracker] Failed to load:', error);
    }

    if (this.isDestroyed) return;
    if (this.loading) {
      this.loading = false;
      this.updateContent();
    }
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Live Team Tracker', showBack: true })}
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: 'Live Team Tracker', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    const online = this.teamLocations.filter(l => l.status === 'online').length;
    const onJourney = this.teamLocations.filter(l => l.has_active_journey).length;

    content.innerHTML = `
      <div class="tracker-header card">
        <div class="tracker-stats">
          <div class="stat-item">
            <span class="stat-value online">${online}</span>
            <span class="stat-label">Online</span>
          </div>
          <div class="stat-item">
            <span class="stat-value journey">${onJourney}</span>
            <span class="stat-label">On Journey</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">${this.teamLocations.length}</span>
            <span class="stat-label">Total</span>
          </div>
        </div>
        <button class="btn btn-secondary refresh-btn" id="refreshBtn">
          🔄 Refresh
        </button>
      </div>

      <div class="tracker-notice card info">
        <p>📍 Locations auto-refresh every 30 seconds</p>
      </div>

      ${this.teamLocations.length > 0 ? `
        <div class="location-list">
          ${this.teamLocations.map(loc => this.renderLocation(loc)).join('')}
        </div>
      ` : `
        <div class="empty-state card">
          <div class="empty-icon">📍</div>
          <p>No team members with active location tracking</p>
        </div>
      `}
    `;

    document.getElementById('refreshBtn')?.addEventListener('click', () => {
      this.loadTeamLocations();
    });
  }

  private renderLocation(loc: TeamLocation): string {
    const statusClass = loc.status;
    const lastUpdate = this.formatTimeSince(loc.last_update);
    const accuracyClass = loc.accuracy <= 100 ? 'high' : loc.accuracy <= 500 ? 'medium' : 'low';

    return `
      <div class="location-card card ${statusClass}">
        <div class="location-header">
          <div class="employee-info">
            <h4>${loc.employee_name}</h4>
            <span class="emp-code">${loc.emp_code}</span>
          </div>
          <div class="location-badges">
            <span class="status-dot ${statusClass}"></span>
            ${loc.has_active_journey ? '<span class="journey-badge">🚗</span>' : ''}
            ${loc.is_clocked_in ? '<span class="clock-badge">⏰</span>' : ''}
          </div>
        </div>
        <div class="location-coords">
          <span class="coords">${loc.latitude.toFixed(6)}, ${loc.longitude.toFixed(6)}</span>
          <span class="accuracy ${accuracyClass}">±${Math.round(loc.accuracy)}m</span>
        </div>
        <div class="location-meta">
          <span>Updated: ${lastUpdate}</span>
          ${loc.battery_level ? `<span>🔋 ${loc.battery_level}%</span>` : ''}
        </div>
      </div>
    `;
  }

  private formatTimeSince(dateStr: string): string {
    const now = new Date();
    const then = new Date(dateStr);
    const diffMs = now.getTime() - then.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return then.toLocaleDateString('en', { day: 'numeric', month: 'short' });
  }
}
