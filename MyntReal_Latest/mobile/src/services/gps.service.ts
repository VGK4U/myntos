/**
 * GPS Service for Background Location Tracking
 * DC Protocol: DC_MOBILE_GPS_001
 * Implements dual-tier accuracy: 500m for heartbeats, 100m for WVV
 * Enhanced with: Adaptive intervals, offline queue, WebSocket broadcast
 * Tracking only active during: Clock-in to Clock-out OR Active Journey
 * Updated: Uses native Android Foreground Service for true background tracking
 */

import { Geolocation, Position } from '@capacitor/geolocation';
import { App, AppState } from '@capacitor/app';
import { Capacitor } from '@capacitor/core';
import { apiService } from './api.service';
import { authService } from './auth.service';
import { batteryService } from './battery.service';
import { offlineQueueService } from './offline-queue.service';
import { websocketService } from './websocket.service';
import { mobileScheduler } from '../runtime';
import { BackgroundLocation, LocationUpdate } from '../plugins/background-location';
import { APP_CONFIG } from '../config/app.config';

const SCHEDULER_HEARTBEAT_ID = 'gps-heartbeat';
const SCHEDULER_TRACKPOINT_ID = 'gps-trackpoint';
const SCHEDULER_BACKGROUND_ID = 'gps-background';

const GPS_DEBUG = () => localStorage.getItem('DC_GPS_DEBUG') === '1';

interface GpsLocation {
  latitude: number;
  longitude: number;
  accuracy_m: number;
  altitude: number | null;
  speed_kmh: number | null;
  heading: number | null;
  timestamp: number;
}

export interface TrackingStatus {
  isTracking: boolean;
  isClockedIn: boolean;
  hasActiveJourney: boolean;
  batteryLevel: number | null;
  isCharging: boolean;
  lastUpdate: number | null;
  accuracy: number | null;
  adaptiveInterval: number;
  isOfflineMode: boolean;
  isSessionExpired: boolean;
  isNativeBackgroundActive: boolean;
}

// DC_GPS_DUAL_TIER_001: Accuracy thresholds
const HEARTBEAT_MAX_ACCURACY_METERS = 500;  // Relaxed for location tracking
const WVV_MAX_ACCURACY_METERS = 100;        // Strict for journey reimbursement

// DC_GPS_ADAPTIVE_001: Adaptive interval based on movement speed
const HEARTBEAT_INTERVAL_STATIONARY_MS = 60000;  // 60 seconds when stationary
const HEARTBEAT_INTERVAL_WALKING_MS = 30000;     // 30 seconds when walking
const HEARTBEAT_INTERVAL_DRIVING_MS = 15000;     // 15 seconds when driving
const TRACK_POINT_INTERVAL_MS = 10000;           // 10 seconds for journeys
const BACKGROUND_INTERVAL_MS = 60000;            // 60 seconds when backgrounded

// Speed thresholds (km/h)
const SPEED_STATIONARY = 2;    // < 2 km/h = stationary
const SPEED_WALKING = 10;       // 2-10 km/h = walking
// > 10 km/h = driving

class GpsService {
  private watchId: string | null = null;
  private currentLocation: GpsLocation | null = null;
  private previousLocation: GpsLocation | null = null;
  private heartbeatTimer: any = null;
  private trackPointTimer: any = null;
  private backgroundTimer: any = null;
  private isTracking: boolean = false;
  private activeJourneyId: number | null = null;
  private isClockedIn: boolean = false;
  private isOnBreak: boolean = false;
  private isInBackground: boolean = false;
  private onStatusChange: ((status: TrackingStatus) => void) | null = null;
  private appStateListenerHandle: any = null;
  private currentHeartbeatInterval: number = HEARTBEAT_INTERVAL_WALKING_MS;
  private isOfflineMode: boolean = false;
  private employeeId: number | null = null;

  private isSessionExpired: boolean = false;
  private sessionExpiredUnsubscribe: (() => void) | null = null;

  private nativeLocationListenerHandle: { remove: () => void } | null = null;
  private nativeStatusListenerHandle: { remove: () => void } | null = null;
  private isNativeBackgroundActive: boolean = false;
  
  private backgroundStartTime: number | null = null;
  private lastBackgroundReason: string = 'app_background';

  constructor() {
    this.setupAppStateListener();
    this.setupOfflineListener();
    this.setupSessionExpirationListener();
    this.setupNativeLocationListener();
  }

  private async setupNativeLocationListener(): Promise<void> {
    if (!Capacitor.isNativePlatform()) {
      if (GPS_DEBUG()) console.log('[DC_GPS_NATIVE] Not on native platform, skipping native listener setup');
      return;
    }

    try {
      this.nativeLocationListenerHandle = await BackgroundLocation.addListener(
        'locationUpdate',
        (data: LocationUpdate) => {
          if (!this.shouldBeTracking()) {
            if (GPS_DEBUG()) console.log('[DC_GPS_NATIVE] Location update ignored — not clocked in or on journey');
            return;
          }
          if (GPS_DEBUG()) console.log(`[DC_GPS_NATIVE] Location update: ${data.latitude.toFixed(6)}, ${data.longitude.toFixed(6)}, acc=${data.accuracy.toFixed(0)}m`);
          
          this.currentLocation = {
            latitude: data.latitude,
            longitude: data.longitude,
            accuracy_m: data.accuracy,
            altitude: null,
            speed_kmh: data.speed * 3.6,
            heading: null,
            timestamp: data.timestamp
          };
          
          if (websocketService.getConnectionStatus()) {
            websocketService.sendLocationUpdate({
              latitude: data.latitude,
              longitude: data.longitude,
              accuracy_m: data.accuracy,
              timestamp: new Date(data.timestamp).toISOString(),
              battery_percentage: data.batteryLevel
            });
          }
          
          this.notifyStatusChange();
        }
      );

      this.nativeStatusListenerHandle = await BackgroundLocation.addListener(
        'serviceStatus',
        (data) => {
          if (GPS_DEBUG()) console.log(`[DC_GPS_NATIVE] Service status: ${data.isRunning ? 'running' : 'stopped'} - ${data.reason}`);
          this.isNativeBackgroundActive = data.isRunning;
          
          if (data.reason && !data.isRunning) {
            this.lastBackgroundReason = data.reason;
          }
          
          if (data.reason === 'boot_restart' && data.isRunning) {
            this.lastBackgroundReason = 'device_reboot';
          }
          
          this.notifyStatusChange();
        }
      );

      if (GPS_DEBUG()) console.log('[DC_GPS_NATIVE] Native location listeners registered');
    } catch (error) {
      console.error('[DC_GPS_NATIVE] Failed to setup native listeners:', error);
    }
  }

  private async startNativeBackgroundTracking(): Promise<boolean> {
    if (!Capacitor.isNativePlatform()) {
      if (GPS_DEBUG()) console.log('[DC_GPS_NATIVE] Not on native platform, using JS timers');
      return false;
    }

    try {
      const permissions = await BackgroundLocation.checkPermissions();
      if (!permissions.allGranted) {
        if (GPS_DEBUG()) console.log('[DC_GPS_NATIVE] Requesting permissions...');
        const result = await BackgroundLocation.requestPermissions();
        if (!result.granted) {
          console.warn('[DC_GPS_NATIVE] Background location permissions not granted');
          return false;
        }
      }

      const batteryOptResult = await BackgroundLocation.isIgnoringBatteryOptimizations();
      if (!batteryOptResult.isIgnoring) {
        if (GPS_DEBUG()) console.log('[DC_GPS_NATIVE] Requesting battery optimization exemption...');
        await BackgroundLocation.requestBatteryOptimizationExemption();
      }

      const authToken = await apiService.getToken();
      if (!authToken) {
        console.warn('[DC_GPS_NATIVE] No auth token available');
        return false;
      }

      const apiUrl = `${APP_CONFIG.API_BASE_URL}/staff/attendance/location/update`;

      await BackgroundLocation.startTracking({
        intervalMs: BACKGROUND_INTERVAL_MS,
        authToken,
        apiUrl,
        notificationTitle: 'MNR Location Tracking',
        notificationText: 'GPS tracking is active'
      });

      this.stopHeartbeat();
      if (GPS_DEBUG()) console.log('[DC_GPS_NATIVE] Stopped JS heartbeat timer (native service handles heartbeats)');

      this.isNativeBackgroundActive = true;
      if (GPS_DEBUG()) console.log('[DC_GPS_NATIVE] Native background tracking started');
      return true;
    } catch (error) {
      console.error('[DC_GPS_NATIVE] Failed to start native tracking:', error);
      return false;
    }
  }

  private async stopNativeBackgroundTracking(): Promise<void> {
    if (!Capacitor.isNativePlatform()) return;

    try {
      await BackgroundLocation.stopTracking();
      this.isNativeBackgroundActive = false;
      if (GPS_DEBUG()) console.log('[DC_GPS_NATIVE] Native background tracking stopped');
    } catch (error) {
      console.error('[DC_GPS_NATIVE] Failed to stop native tracking:', error);
    }
  }

  async isNativeTrackingActive(): Promise<boolean> {
    if (!Capacitor.isNativePlatform()) return false;
    
    try {
      const result = await BackgroundLocation.isTracking();
      return result.isTracking;
    } catch (error) {
      return false;
    }
  }

  private setupOfflineListener(): void {
    offlineQueueService.onStatusChange((status) => {
      this.isOfflineMode = !status.isOnline;
      this.notifyStatusChange();
    });
  }

  // DC_SESSION_EXPIRY_001: Handle session expiration during journey tracking
  private setupSessionExpirationListener(): void {
    this.sessionExpiredUnsubscribe = apiService.onSessionExpired((endpoint) => {
      console.warn(`[DC_GPS_SESSION] Session expired during: ${endpoint}`);
      this.isSessionExpired = true;
      this.notifyStatusChange();
      
      // Don't stop journey tracking - queue points locally instead
      // User will be prompted to re-authenticate
      if (this.activeJourneyId) {
        if (GPS_DEBUG()) console.log('[DC_GPS_SESSION] Active journey detected - continuing with offline queue');
      }
    });
  }

  resetSessionExpiredState(): void {
    this.isSessionExpired = false;
    apiService.resetSessionExpiredFlag();
    this.notifyStatusChange();
  }

  isSessionExpiredState(): boolean {
    return this.isSessionExpired;
  }

  setEmployeeId(id: number): void {
    this.employeeId = id;
  }

  private getAdaptiveInterval(): number {
    if (!this.currentLocation || this.currentLocation.speed_kmh === null) {
      return HEARTBEAT_INTERVAL_WALKING_MS;
    }

    const speed = this.currentLocation.speed_kmh;

    if (speed < SPEED_STATIONARY) {
      return HEARTBEAT_INTERVAL_STATIONARY_MS;
    } else if (speed < SPEED_WALKING) {
      return HEARTBEAT_INTERVAL_WALKING_MS;
    } else {
      return HEARTBEAT_INTERVAL_DRIVING_MS;
    }
  }

  private updateAdaptiveInterval(): void {
    const newInterval = this.getAdaptiveInterval();
    
    if (newInterval !== this.currentHeartbeatInterval && mobileScheduler.isScheduled(SCHEDULER_HEARTBEAT_ID)) {
      if (GPS_DEBUG()) console.log(`[DC_GPS_ADAPTIVE] Interval changed: ${this.currentHeartbeatInterval}ms -> ${newInterval}ms`);
      this.currentHeartbeatInterval = newInterval;
      
      mobileScheduler.updateInterval(SCHEDULER_HEARTBEAT_ID, newInterval);
    }
  }

  private setupAppStateListener(): void {
    this.appStateListenerHandle = App.addListener('appStateChange', (state: AppState) => {
      this.isInBackground = !state.isActive;
      if (GPS_DEBUG()) console.log(`[DC_GPS] App state: ${state.isActive ? 'foreground' : 'background'}`);
      
      if (this.shouldBeTracking()) {
        if (this.isInBackground) {
          this.backgroundStartTime = Date.now();
          this.lastBackgroundReason = 'app_background';
          this.switchToBackgroundMode();
          this.reportGpsStatus('app_background', 'App moved to background');
        } else {
          if (this.backgroundStartTime) {
            const offlineDuration = Math.round((Date.now() - this.backgroundStartTime) / 1000);
            if (offlineDuration > 60) {
              this.showOfflineResumePopup(offlineDuration, this.lastBackgroundReason);
            }
            this.backgroundStartTime = null;
          }
          this.switchToForegroundMode();
          this.reportGpsStatus('active', 'App returned to foreground');
        }
      }
    });
  }
  
  private showOfflineResumePopup(durationSeconds: number, reason: string): void {
    const existingPopup = document.querySelector('.offline-resume-overlay');
    if (existingPopup) existingPopup.remove();
    
    const minutes = Math.floor(durationSeconds / 60);
    const seconds = durationSeconds % 60;
    const durationText = minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
    
    const reasonMap: Record<string, string> = {
      'device_reboot': 'Device was restarted',
      'app_background': 'App was in background',
      'app_killed': 'App was closed',
      'gps_disabled': 'GPS was disabled',
      'permission_denied': 'Location permission denied',
      'network_error': 'Network was unavailable',
      'started': 'Tracking resumed',
      'stopped': 'Tracking was stopped',
      'destroyed': 'Service was stopped',
      'boot_restart': 'Device was restarted',
      'unknown': 'Unknown reason'
    };
    const reasonText = reasonMap[reason] || reason.replace(/_/g, ' ');
    
    const overlay = document.createElement('div');
    overlay.className = 'offline-resume-overlay';
    overlay.innerHTML = `
      <div class="offline-resume-popup">
        <div class="resume-icon">📍</div>
        <div class="resume-info">
          <h3>GPS Tracking Resumed</h3>
          <div class="offline-duration">${durationText}</div>
          <div class="offline-reason">${reasonText} · Recorded in attendance</div>
        </div>
        <button id="dismissOfflinePopup">OK</button>
      </div>
    `;
    
    document.body.appendChild(overlay);
    
    document.getElementById('dismissOfflinePopup')?.addEventListener('click', () => {
      overlay.remove();
    });
    
    setTimeout(() => {
      if (overlay.parentElement) overlay.remove();
    }, 10000);
  }
  
  setBackgroundReason(reason: string): void {
    this.lastBackgroundReason = reason;
    if (!this.backgroundStartTime) {
      this.backgroundStartTime = Date.now();
    }
    if (GPS_DEBUG()) console.log(`[DC_GPS] Background reason set: ${reason}`);
  }

  async cleanup(): Promise<void> {
    if (GPS_DEBUG()) console.log('[DC_GPS] Cleaning up all tracking resources');
    await this.stopTracking();
    batteryService.stopMonitoring();
    this.isClockedIn = false;
    this.activeJourneyId = null;
    this.currentLocation = null;
    this.isSessionExpired = false;
    
    // Clean up session expiration listener
    if (this.sessionExpiredUnsubscribe) {
      this.sessionExpiredUnsubscribe();
      this.sessionExpiredUnsubscribe = null;
    }
    
    this.notifyStatusChange();
  }

  private shouldBeTracking(): boolean {
    if (this.isOnBreak) {
      return false;
    }
    return this.isClockedIn || this.activeJourneyId !== null;
  }

  // DC Protocol (Jan 28, 2026): Request background location permission for Android 10+
  // This shows the "Allow all the time" option which is needed for GPS tracking when app is minimized
  // Only prompts ONCE per install (stored in localStorage)
  private async requestBackgroundLocationPermission(): Promise<void> {
    try {
      // Check if running on Android
      const { Capacitor } = await import('@capacitor/core');
      if (Capacitor.getPlatform() !== 'android') {
        if (GPS_DEBUG()) console.log('[DC_GPS] Background location: Not Android, skipping special request');
        return;
      }

      // Check if we've already shown the background location prompt
      const promptShown = localStorage.getItem('dc_bg_location_prompt_shown');
      if (promptShown === 'true') {
        if (GPS_DEBUG()) console.log('[DC_GPS] Background location prompt already shown once');
        return;
      }

      // For Android 10+ (API 29+), we need to guide user to settings for "Always Allow"
      // The standard Geolocation.requestPermissions() only grants "While Using"
      
      // Check current permission status
      const currentStatus = await Geolocation.checkPermissions();
      if (GPS_DEBUG()) console.log('[DC_GPS] Current permission status:', JSON.stringify(currentStatus));
      
      // If we only have "while using" (location granted but not background), prompt user ONCE
      if (currentStatus.location === 'granted') {
        // Mark as shown so we don't prompt again
        localStorage.setItem('dc_bg_location_prompt_shown', 'true');
        
        // Show a dialog explaining why background location is needed
        const shouldOpenSettings = confirm(
          '📍 Background Location Required\n\n' +
          'To track your location during work hours (even when app is minimized), please:\n\n' +
          '1. Tap "OK" for instructions\n' +
          '2. Enable "Allow all the time" in Settings\n\n' +
          'This ensures accurate GPS tracking for your attendance and journey records.\n\n' +
          '(This message will only appear once)'
        );
        
        if (shouldOpenSettings) {
          // Show instructions to enable background location
          // Note: On Android 10+, "Allow all the time" can only be set in system settings
          alert(
            '📍 Enable Background Location:\n\n' +
            '1. Go to your phone Settings\n' +
            '2. Find "Apps" → "MyntReal"\n' +
            '3. Tap "Permissions" → "Location"\n' +
            '4. Select "Allow all the time"\n\n' +
            'This allows GPS tracking even when the app is minimized.'
          );
          if (GPS_DEBUG()) console.log('[DC_GPS] Showed background location instructions (first time)');
        }
      }
    } catch (error) {
      if (GPS_DEBUG()) console.log('[DC_GPS] Background location request info:', error);
      // Non-fatal - continue with foreground location
    }
  }

  private switchToBackgroundMode(): void {
    if (GPS_DEBUG()) console.log('[DC_GPS] Switching to background mode - reduced frequency');
    this.stopHeartbeat();
    
    if (mobileScheduler.isScheduled(SCHEDULER_BACKGROUND_ID)) return;
    
    mobileScheduler.schedule(
      SCHEDULER_BACKGROUND_ID,
      async () => {
        if (!this.shouldBeTracking()) {
          this.stopBackgroundMode();
          return;
        }
        
        const position = await this.getCurrentPosition();
        if (position) {
          this.currentLocation = position;
          await this.sendHeartbeat();
          
          if (this.activeJourneyId) {
            await this.sendTrackPoint();
          }
        }
      },
      BACKGROUND_INTERVAL_MS,
      { runInBackground: true, immediateOnResume: true }
    );
  }

  private switchToForegroundMode(): void {
    if (GPS_DEBUG()) console.log('[DC_GPS] Switching to foreground mode - normal frequency');
    this.stopBackgroundMode();
    
    if (this.shouldBeTracking()) {
      this.startHeartbeat();
      if (this.activeJourneyId) {
        this.startJourneyTracking(this.activeJourneyId);
      }
    }
  }

  private stopBackgroundMode(): void {
    mobileScheduler.cancel(SCHEDULER_BACKGROUND_ID);
    this.backgroundTimer = null;
  }

  setClockedIn(value: boolean): void {
    const wasTracking = this.shouldBeTracking();
    this.isClockedIn = value;
    const shouldTrack = this.shouldBeTracking();
    
    if (GPS_DEBUG()) console.log(`[DC_GPS_DIAGNOSTIC] setClockedIn(${value}): wasTracking=${wasTracking}, shouldTrack=${shouldTrack}, hasJourney=${this.activeJourneyId !== null}`);
    
    if (!wasTracking && shouldTrack) {
      if (GPS_DEBUG()) console.log('[DC_GPS_DIAGNOSTIC] Starting GPS tracking (clock-in triggered)');
      this.startTracking();
      batteryService.startMonitoring();
      this.startNativeBackgroundTracking();
    } else if (wasTracking && !shouldTrack) {
      if (GPS_DEBUG()) console.log('[DC_GPS_DIAGNOSTIC] Stopping GPS tracking (clock-out triggered)');
      this.stopTracking();
      batteryService.stopMonitoring();
      this.stopNativeBackgroundTracking();
    }
    
    this.notifyStatusChange();
  }

  setOnBreak(value: boolean): void {
    const wasTracking = this.shouldBeTracking();
    this.isOnBreak = value;
    const shouldTrack = this.shouldBeTracking();
    
    if (GPS_DEBUG()) console.log(`[DC_GPS] Break status changed: ${value ? 'STARTED' : 'ENDED'}`);
    
    if (value) {
      if (wasTracking) {
        if (GPS_DEBUG()) console.log('[DC_GPS] Pausing GPS tracking for break');
        this.stopTracking();
        this.stopNativeBackgroundTracking();
      }
    } else {
      if (!wasTracking && shouldTrack) {
        if (GPS_DEBUG()) console.log('[DC_GPS] Resuming GPS tracking after break');
        this.startTracking();
        this.startNativeBackgroundTracking();
      }
    }
    
    this.notifyStatusChange();
  }

  getTrackingStatus(): TrackingStatus {
    const battery = batteryService.getCurrentStatus();
    return {
      isTracking: this.isTracking,
      isClockedIn: this.isClockedIn,
      hasActiveJourney: this.activeJourneyId !== null,
      batteryLevel: battery?.level ?? null,
      isCharging: battery?.isCharging ?? false,
      lastUpdate: this.currentLocation?.timestamp ?? null,
      accuracy: this.currentLocation?.accuracy_m ?? null,
      adaptiveInterval: this.currentHeartbeatInterval,
      isOfflineMode: this.isOfflineMode,
      isSessionExpired: this.isSessionExpired,
      isNativeBackgroundActive: this.isNativeBackgroundActive
    };
  }

  onTrackingStatusChange(callback: (status: TrackingStatus) => void): void {
    this.onStatusChange = callback;
  }

  private notifyStatusChange(): void {
    if (this.onStatusChange) {
      this.onStatusChange(this.getTrackingStatus());
    }
  }

  /**
   * DC Protocol (Jan 28, 2026): Report GPS status change to backend
   * Called when GPS fails or recovers, so Team Live Tracker can show reason
   */
  async reportGpsStatus(
    status: 'active' | 'permission_denied' | 'gps_disabled' | 'network_error' | 'app_background' | 'location_timeout',
    reason?: string
  ): Promise<void> {
    try {
      const batteryInfo = await batteryService.getBatteryInfo();
      const batteryPct = batteryInfo?.level ?? undefined;
      
      await apiService.post('/staff/attendance/location/gps-status', {
        status,
        reason: reason || undefined,
        battery_percentage: batteryPct
      });
      if (GPS_DEBUG()) console.log(`[DC_GPS_STATUS] Reported: ${status} ${reason || ''}`);
    } catch (error) {
      console.warn('[DC_GPS_STATUS] Failed to report status:', error);
    }
  }

  async getCurrentPosition(): Promise<GpsLocation | null> {
    try {
      const position = await Geolocation.getCurrentPosition({
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 0
      });
      
      return this.mapPosition(position);
    } catch (error: any) {
      console.error('[DC_GPS] Failed to get position:', error);
      // DC Protocol (Jan 28, 2026): Report GPS failure reason
      const errorMsg = error?.message || String(error);
      if (errorMsg.includes('denied') || errorMsg.includes('permission')) {
        this.reportGpsStatus('permission_denied', 'Location permission denied');
      } else if (errorMsg.includes('timeout')) {
        this.reportGpsStatus('location_timeout', 'GPS signal timeout');
      } else if (errorMsg.includes('unavailable') || errorMsg.includes('disabled')) {
        this.reportGpsStatus('gps_disabled', 'GPS disabled on device');
      } else {
        this.reportGpsStatus('location_timeout', errorMsg.substring(0, 100));
      }
      return null;
    }
  }

  private mapPosition(position: Position): GpsLocation {
    return {
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
      accuracy_m: position.coords.accuracy,
      altitude: position.coords.altitude,
      speed_kmh: position.coords.speed ? position.coords.speed * 3.6 : null,
      heading: position.coords.heading,
      timestamp: position.timestamp
    };
  }

  async startTracking(): Promise<boolean> {
    if (GPS_DEBUG()) console.log(`[DC_GPS_DIAGNOSTIC] startTracking() called: isTracking=${this.isTracking}, isClockedIn=${this.isClockedIn}, activeJourneyId=${this.activeJourneyId}`);
    
    if (this.isTracking) {
      if (GPS_DEBUG()) console.log('[DC_GPS_DIAGNOSTIC] Already tracking, returning true');
      return true;
    }

    if (!this.shouldBeTracking()) {
      if (GPS_DEBUG()) console.log('[DC_GPS_DIAGNOSTIC] Not clocked in and no active journey - tracking not allowed');
      return false;
    }
    
    if (GPS_DEBUG()) console.log('[DC_GPS_DIAGNOSTIC] Starting GPS tracking...');

    try {
      // DC_LIVE_LOCATION_001: Request location permissions (iOS needs coarse + fine for background)
      // DC Protocol (Jan 28, 2026): Request foreground first, then background for "Always Allow" on Android 10+
      const permission = await Geolocation.requestPermissions();
      if (GPS_DEBUG()) console.log('[DC_GPS] Foreground permission status:', JSON.stringify(permission));
      
      if (permission.location !== 'granted' && permission.coarseLocation !== 'granted') {
        console.error('[DC_GPS] Location permission denied');
        this.reportGpsStatus('permission_denied', 'User denied location permission');
        return false;
      }
      
      // DC Protocol (Jan 28, 2026): For Android 10+, request background location separately
      // This triggers the "Allow all the time" / "Always Allow" dialog
      await this.requestBackgroundLocationPermission();

      // DC Protocol (Jan 29, 2026): Get immediate location before starting watch
      // This ensures we have a location for the first heartbeat
      try {
        const immediatePosition = await Geolocation.getCurrentPosition({ 
          enableHighAccuracy: true, 
          timeout: 10000 
        });
        if (immediatePosition) {
          this.currentLocation = this.mapPosition(immediatePosition);
          if (GPS_DEBUG()) console.log(`[DC_GPS] Initial location acquired: ${this.currentLocation.accuracy_m.toFixed(0)}m accuracy`);
          this.notifyStatusChange();
          
          // DC Protocol (Jan 29, 2026): Send immediate heartbeat on clock-in
          // Don't wait for the interval - send location to database right away
          this.sendHeartbeat().catch(err => console.warn('[DC_GPS] Initial heartbeat failed:', err));
        }
      } catch (initialErr) {
        console.warn('[DC_GPS] Could not get immediate location, will use watch:', initialErr);
      }

      // DC_LIVE_LOCATION_001: Start continuous position watching for real-time updates
      this.watchId = await Geolocation.watchPosition(
        { enableHighAccuracy: true },
        (position, error) => {
          if (error) {
            console.error('[DC_GPS] Watch error:', error);
            // DC Protocol (Jan 28, 2026): Report watch error
            const errorMsg = (error as any)?.message || String(error);
            if (errorMsg.includes('denied')) {
              this.reportGpsStatus('permission_denied', 'Location permission revoked');
            } else if (errorMsg.includes('unavailable')) {
              this.reportGpsStatus('gps_disabled', 'GPS unavailable');
            }
            return;
          }
          if (position) {
            this.currentLocation = this.mapPosition(position);
            if (GPS_DEBUG()) console.log(`[DC_GPS] Location update: ${this.currentLocation.accuracy_m.toFixed(0)}m accuracy`);
            this.notifyStatusChange();
          }
        }
      );

      this.isTracking = true;
      this.startHeartbeat();
      
      if (GPS_DEBUG()) console.log('[DC_GPS] Tracking started - background location enabled (clocked in or journey active)');
      this.notifyStatusChange();
      return true;
    } catch (error) {
      console.error('[DC_GPS] Failed to start tracking:', error);
      return false;
    }
  }

  async stopTracking(): Promise<void> {
    if (this.watchId) {
      await Geolocation.clearWatch({ id: this.watchId });
      this.watchId = null;
    }

    this.stopHeartbeat();
    this.stopBackgroundMode();
    this.stopJourneyTracking();
    this.isTracking = false;
    
    if (GPS_DEBUG()) console.log('[DC_GPS] Tracking stopped');
    this.notifyStatusChange();
  }

  private startHeartbeat(): void {
    if (GPS_DEBUG()) console.log(`[DC_GPS_DIAGNOSTIC] startHeartbeat() called, already scheduled: ${mobileScheduler.isScheduled(SCHEDULER_HEARTBEAT_ID)}`);
    
    if (mobileScheduler.isScheduled(SCHEDULER_HEARTBEAT_ID)) {
      if (GPS_DEBUG()) console.log('[DC_GPS_DIAGNOSTIC] Heartbeat already scheduled, skipping');
      return;
    }

    if (GPS_DEBUG()) console.log(`[DC_GPS_DIAGNOSTIC] Scheduling heartbeat with interval: ${this.currentHeartbeatInterval}ms`);
    mobileScheduler.schedule(
      SCHEDULER_HEARTBEAT_ID,
      async () => {
        if (GPS_DEBUG()) console.log('[DC_GPS_DIAGNOSTIC] Heartbeat timer fired, calling sendHeartbeat()');
        await this.sendHeartbeat();
        this.updateAdaptiveInterval();
      },
      this.currentHeartbeatInterval,
      { runImmediately: true, immediateOnResume: true, runInBackground: true }
    );
    if (GPS_DEBUG()) console.log('[DC_GPS_DIAGNOSTIC] Heartbeat scheduled successfully');
  }

  private stopHeartbeat(): void {
    mobileScheduler.cancel(SCHEDULER_HEARTBEAT_ID);
    this.heartbeatTimer = null;
  }

  private async sendHeartbeat(): Promise<void> {
    if (!this.currentLocation) {
      if (GPS_DEBUG()) console.log('[DC_GPS] No location for heartbeat');
      return;
    }

    const loc = this.currentLocation;

    // DC_GPS_DUAL_TIER_001: Use relaxed 500m limit for heartbeats
    if (loc.accuracy_m > HEARTBEAT_MAX_ACCURACY_METERS) {
      if (GPS_DEBUG()) console.log(`[DC_GPS] Accuracy ${loc.accuracy_m.toFixed(0)}m exceeds limit, skipping heartbeat`);
      return;
    }

    // Log if accuracy is degraded
    if (loc.accuracy_m > WVV_MAX_ACCURACY_METERS) {
      if (GPS_DEBUG()) console.log(`[DC_GPS_DUAL_TIER] Sending degraded GPS: ${loc.accuracy_m.toFixed(0)}m (indoor/weak signal)`);
    }

    // DC_BATTERY_001: Get current battery level
    const battery = batteryService.getCurrentStatus();
    const batteryPct = battery?.level;

    // DC_WS_001: Broadcast location via WebSocket for real-time updates
    if (websocketService.getConnectionStatus()) {
      websocketService.sendLocationUpdate({
        latitude: loc.latitude,
        longitude: loc.longitude,
        accuracy_m: loc.accuracy_m,
        timestamp: new Date().toISOString(),
        battery_percentage: batteryPct
      });
    }

    try {
      if (GPS_DEBUG()) console.log(`[DC_GPS_DIAGNOSTIC] Sending heartbeat: lat=${loc.latitude.toFixed(6)}, lng=${loc.longitude.toFixed(6)}, acc=${loc.accuracy_m.toFixed(0)}m, battery=${batteryPct ?? 'N/A'}`);
      
      // DC_BATTERY_002: Include battery percentage in heartbeat
      const response = await apiService.sendLocationHeartbeat(
        loc.latitude,
        loc.longitude,
        loc.accuracy_m,
        batteryPct
      );

      if (response.success) {
        if (GPS_DEBUG()) console.log(`[DC_GPS_DIAGNOSTIC] Heartbeat SUCCESS: dc_code=${response.data?.dc_code}, worked_mins=${response.data?.worked_minutes ?? 'N/A'}`);
        authService.updateActivity();
        
        // DC_SESSION_EXTEND_001: Apply extended token to prevent session expiry
        if (response.data?.extended_token) {
          await apiService.setToken(response.data.extended_token);
          if (GPS_DEBUG()) console.log('[DC_SESSION_EXTEND] Session extended via heartbeat');
        }
      } else {
        // DC_GPS_401_001: Stop tracking on 401 to prevent repeated unauthorized flood
        if (response.status === 401) {
          console.warn('[DC_GPS] Heartbeat 401 — session expired, stopping GPS tracking to prevent 401 flood');
          this.stopTracking();
          return;
        }

        console.warn('[DC_GPS] Heartbeat failed:', response.error);
        
        // DC_OFFLINE_001: Queue for offline sync if API fails
        if (this.isOfflineMode) {
          await offlineQueueService.enqueueLocation(loc.latitude, loc.longitude, loc.accuracy_m, undefined, batteryPct);
          if (GPS_DEBUG()) console.log('[DC_GPS] Heartbeat queued for offline sync');
        }
      }
    } catch (error) {
      console.error('[DC_GPS] Heartbeat error:', error);
      
      await offlineQueueService.enqueueLocation(loc.latitude, loc.longitude, loc.accuracy_m, undefined, batteryPct);
      if (GPS_DEBUG()) console.log('[DC_GPS] Heartbeat queued for offline sync');
    }
  }

  startJourneyTracking(journeyId: number): void {
    const wasTracking = this.shouldBeTracking();
    this.activeJourneyId = journeyId;
    
    if (!wasTracking && this.shouldBeTracking()) {
      this.startTracking();
      batteryService.startMonitoring();
    }
    
    if (mobileScheduler.isScheduled(SCHEDULER_TRACKPOINT_ID)) return;

    mobileScheduler.schedule(
      SCHEDULER_TRACKPOINT_ID,
      async () => {
        await this.sendTrackPoint();
      },
      TRACK_POINT_INTERVAL_MS,
      { runImmediately: false, immediateOnResume: true, runInBackground: false }
    );

    if (GPS_DEBUG()) console.log(`[DC_GPS] Journey tracking started for ID: ${journeyId}`);
    this.notifyStatusChange();
  }

  stopJourneyTracking(): void {
    mobileScheduler.cancel(SCHEDULER_TRACKPOINT_ID);
    this.trackPointTimer = null;
    
    const wasJourneyActive = this.activeJourneyId !== null;
    this.activeJourneyId = null;
    
    if (wasJourneyActive && !this.shouldBeTracking()) {
      this.stopTracking();
      batteryService.stopMonitoring();
    }
    
    if (GPS_DEBUG()) console.log('[DC_GPS] Journey tracking stopped');
    this.notifyStatusChange();
  }

  private async sendTrackPoint(): Promise<void> {
    if (!this.currentLocation || !this.activeJourneyId) return;

    const loc = this.currentLocation;
    const journeyId = this.activeJourneyId;

    // WVV Protocol: Only send if accuracy <= 100m for reimbursement
    if (loc.accuracy_m > WVV_MAX_ACCURACY_METERS) {
      if (GPS_DEBUG()) console.log(`[DC_GPS] Track point skipped: accuracy ${loc.accuracy_m.toFixed(0)}m exceeds WVV limit`);
      return;
    }

    // DC_BATTERY_003: Get battery level for journey track points
    const battery = batteryService.getCurrentStatus();
    const batteryPct = battery?.level;

    // DC_WS_001: Broadcast journey track point via WebSocket
    if (websocketService.getConnectionStatus()) {
      websocketService.sendLocationUpdate({
        latitude: loc.latitude,
        longitude: loc.longitude,
        accuracy_m: loc.accuracy_m,
        timestamp: new Date().toISOString(),
        battery_percentage: batteryPct
      });
    }

    try {
      const response = await apiService.addJourneyTrackPoint(journeyId, {
        location: {
          latitude: loc.latitude,
          longitude: loc.longitude,
          accuracy: loc.accuracy_m,
          altitude: loc.altitude ?? undefined,
          speed: loc.speed_kmh ?? undefined,
          heading: loc.heading ?? undefined,
          battery_percentage: batteryPct
        },
        speed_kmh: loc.speed_kmh ?? undefined,
        battery_percentage: batteryPct
      });

      if (response.success) {
        if (GPS_DEBUG()) console.log('[DC_GPS] Track point sent');
        
        if (response.data?.extended_token) {
          await apiService.setToken(response.data.extended_token);
          if (GPS_DEBUG()) console.log('[DC_SESSION_EXTEND] Session extended via journey track point');
        }
      } else {
        if (this.isOfflineMode) {
          await offlineQueueService.enqueueLocation(loc.latitude, loc.longitude, loc.accuracy_m, journeyId, batteryPct);
          if (GPS_DEBUG()) console.log('[DC_GPS] Track point queued for offline sync');
        }
      }
    } catch (error) {
      console.error('[DC_GPS] Track point error:', error);
      
      await offlineQueueService.enqueueLocation(loc.latitude, loc.longitude, loc.accuracy_m, journeyId, batteryPct);
      if (GPS_DEBUG()) console.log('[DC_GPS] Track point queued for offline sync');
    }
  }

  getCurrentLocation(): GpsLocation | null {
    return this.currentLocation;
  }

  isWvvCompliant(accuracy_m: number): boolean {
    return accuracy_m <= WVV_MAX_ACCURACY_METERS;
  }

  getAccuracyQuality(accuracy_m: number): { label: string; color: string } {
    if (accuracy_m <= 50) return { label: 'High', color: '#10b981' };
    if (accuracy_m <= 100) return { label: 'Medium', color: '#3b82f6' };
    if (accuracy_m <= 300) return { label: 'Low', color: '#f59e0b' };
    return { label: 'Weak Signal', color: '#ef4444' };
  }
}

export const gpsService = new GpsService();
