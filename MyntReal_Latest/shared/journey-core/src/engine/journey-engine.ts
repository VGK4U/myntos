import { Journey, JourneySession, StartJourneyInput } from '../types/journey.js';
import { TrackPoint, RawGPSPosition } from '../types/track-point.js';
import { JourneyState, JourneyEvent } from '../types/enums.js';
import { GPSAdapter, GPSAdapterCallbacks, GPSError } from '../adapters/gps-adapter.js';
import { StorageAdapter } from '../adapters/storage-adapter.js';
import { JourneyAPIAdapter } from '../adapters/api-adapter.js';
import { PlatformAdapter, Logger, TimerProvider, TimerHandle, noopLogger, noopTimer } from '../adapters/platform-adapter.js';
import { StartJourneyPayload, HeartbeatPayload, EndJourneyPayload, TrackSummary } from '../types/api-payloads.js';
import { EventEmitter, createEventEmitter } from '../utils/event-emitter.js';
import { buildTrackPoint, createStartTrackPoint } from '../utils/track-point-builder.js';
import { metersToKilometers } from '../utils/geo-utils.js';
import { validateStartInput, shouldInvalidateJourney, validateSessionIntegrity } from '../validators/journey-validator.js';
import { isHeartbeatAccuracyValid } from '../validators/wvv-validator.js';

export interface JourneyEngineConfig {
  heartbeatIntervalMs: number;
  sessionSaveIntervalMs: number;
  minDistanceForHeartbeatM: number;
  batteryProvider?: () => number | null;
}

const DEFAULT_CONFIG: JourneyEngineConfig = {
  heartbeatIntervalMs: 15000,
  sessionSaveIntervalMs: 60000,
  minDistanceForHeartbeatM: 0
};

export interface JourneyEngineState {
  journey: Journey | null;
  state: JourneyState;
  isGPSWatching: boolean;
  lastHeartbeatTime: number | null;
  pendingTrackPoints: TrackPoint[];
}

export class JourneyEngine {
  private state: JourneyState = JourneyState.IDLE;
  private journey: Journey | null = null;
  private trackPoints: TrackPoint[] = [];
  private totalDistanceM: number = 0;
  
  private gpsAdapter: GPSAdapter;
  private storageAdapter: StorageAdapter;
  private apiAdapter: JourneyAPIAdapter;
  private config: JourneyEngineConfig;
  
  private logger: Logger;
  private timer: TimerProvider;
  
  private emitter: EventEmitter;
  private heartbeatInterval: TimerHandle | null = null;
  private sessionSaveInterval: TimerHandle | null = null;
  private lastHeartbeatTime: number | null = null;
  
  constructor(
    gpsAdapter: GPSAdapter,
    storageAdapter: StorageAdapter,
    apiAdapter: JourneyAPIAdapter,
    config: Partial<JourneyEngineConfig> = {},
    platform?: Partial<PlatformAdapter>
  ) {
    this.gpsAdapter = gpsAdapter;
    this.storageAdapter = storageAdapter;
    this.apiAdapter = apiAdapter;
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.logger = platform?.logger ?? noopLogger;
    this.timer = platform?.timer ?? noopTimer;
    this.emitter = createEventEmitter();
  }
  
  on(event: JourneyEvent, callback: (data: unknown) => void): void {
    this.emitter.on(event, callback);
  }
  
  off(event: JourneyEvent, callback: (data: unknown) => void): void {
    this.emitter.off(event, callback);
  }
  
  getState(): JourneyState {
    return this.state;
  }
  
  getJourney(): Journey | null {
    return this.journey;
  }
  
  getTrackPoints(): TrackPoint[] {
    return [...this.trackPoints];
  }
  
  getTotalDistanceKm(): number {
    return metersToKilometers(this.totalDistanceM);
  }
  
  async initialize(): Promise<void> {
    const hasSession = await this.storageAdapter.hasSession();
    if (hasSession) {
      await this.restoreSession();
    }
  }
  
  private async restoreSession(): Promise<void> {
    try {
      const session = await this.storageAdapter.loadSession();
      if (!session) return;
      
      const validation = validateSessionIntegrity(session);
      if (!validation.valid) {
        this.logger.warn('Session invalid:', validation.errors);
        await this.storageAdapter.clearSession();
        return;
      }
      
      const activeJourneyResponse = await this.apiAdapter.getActiveJourney();
      if (!activeJourneyResponse.has_active_journey || !activeJourneyResponse.journey) {
        await this.storageAdapter.clearSession();
        return;
      }
      
      const serverJourney = activeJourneyResponse.journey;
      
      this.journey = {
        id: serverJourney.id,
        company_id: serverJourney.company_id,
        transport_mode: serverJourney.transport_mode,
        purpose: serverJourney.purpose,
        purpose_details: session.purpose_details,
        state: JourneyState.ACTIVE,
        start_time: serverJourney.start_time,
        end_time: null,
        start_location: {
          latitude: serverJourney.start_latitude,
          longitude: serverJourney.start_longitude,
          accuracy_m: 0,
          timestamp: serverJourney.start_time,
          speed_kmh: null,
          distance_from_last_m: 0,
          total_distance_m: 0,
          altitude_m: null,
          heading: null,
          battery_pct: null,
          is_wvv_compliant: true,
          validation_reason: null,
          accuracy_level: 'high' as any
        },
        end_location: null,
        start_address: null,
        end_address: null,
        track_points: [],
        total_distance_km: serverJourney.total_distance_km,
        session_token: serverJourney.session_token,
        invalidation_reason: null,
        wvv_compliant_points: 0,
        total_points: 0
      };
      
      this.totalDistanceM = serverJourney.total_distance_km * 1000;
      this.state = JourneyState.ACTIVE;
      
      await this.startGPSTracking();
      this.startIntervals();
      
      this.emitter.emit(JourneyEvent.SESSION_RESTORED, { journey: this.journey });
      
    } catch (error) {
      this.logger.error('Failed to restore session:', error);
      await this.storageAdapter.clearSession();
    }
  }
  
  async start(input: StartJourneyInput): Promise<{ success: boolean; error?: string }> {
    if (this.state !== JourneyState.IDLE) {
      return { success: false, error: `Cannot start journey in state: ${this.state}` };
    }
    
    const validation = validateStartInput(input);
    if (!validation.valid) {
      return { success: false, error: validation.errors.join(', ') };
    }
    
    try {
      const position = await this.gpsAdapter.getCurrentPosition();
      if (!position) {
        return { success: false, error: 'Unable to get GPS position' };
      }
      
      if (!isHeartbeatAccuracyValid(position.accuracy)) {
        return { success: false, error: `GPS accuracy ${position.accuracy}m too low (max 500m)` };
      }
      
      const batteryPct = this.config.batteryProvider?.() ?? null;
      const startPoint = createStartTrackPoint(position, batteryPct);
      
      const payload: StartJourneyPayload = {
        company_id: input.company_id,
        transport_mode: input.transport_mode,
        purpose: input.purpose,
        purpose_details: input.purpose_details ?? null,
        start_latitude: startPoint.latitude,
        start_longitude: startPoint.longitude,
        start_accuracy_m: startPoint.accuracy_m,
        start_timestamp: startPoint.timestamp
      };
      
      const response = await this.apiAdapter.startJourney(payload);
      
      if (!response.success) {
        return { success: false, error: response.message || 'Failed to start journey' };
      }
      
      this.journey = {
        id: response.journey_id,
        company_id: input.company_id,
        transport_mode: input.transport_mode,
        purpose: input.purpose,
        purpose_details: input.purpose_details ?? null,
        state: JourneyState.ACTIVE,
        start_time: startPoint.timestamp,
        end_time: null,
        start_location: startPoint,
        end_location: null,
        start_address: null,
        end_address: null,
        track_points: [startPoint],
        total_distance_km: 0,
        session_token: response.session_token,
        invalidation_reason: null,
        wvv_compliant_points: startPoint.is_wvv_compliant ? 1 : 0,
        total_points: 1
      };
      
      this.trackPoints = [startPoint];
      this.totalDistanceM = 0;
      this.state = JourneyState.ACTIVE;
      
      await this.saveSession();
      await this.startGPSTracking();
      this.startIntervals();
      
      this.emitter.emit(JourneyEvent.STARTED, { journey: this.journey });
      
      return { success: true };
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      this.emitter.emit(JourneyEvent.ERROR, { error: errorMessage });
      return { success: false, error: errorMessage };
    }
  }
  
  async stop(): Promise<{ success: boolean; error?: string }> {
    if (this.state !== JourneyState.ACTIVE && this.state !== JourneyState.PAUSED) {
      return { success: false, error: `Cannot stop journey in state: ${this.state}` };
    }
    
    if (!this.journey || !this.journey.id) {
      return { success: false, error: 'No active journey' };
    }
    
    try {
      this.stopIntervals();
      this.gpsAdapter.stopWatching();
      
      const position = await this.gpsAdapter.getCurrentPosition();
      let endPoint: TrackPoint;
      
      if (position) {
        const batteryPct = this.config.batteryProvider?.() ?? null;
        const lastPoint = this.trackPoints[this.trackPoints.length - 1] ?? null;
        
        endPoint = buildTrackPoint({
          rawPosition: position,
          previousPoint: lastPoint,
          totalDistanceSoFar: this.totalDistanceM,
          batteryPct
        });
        
        this.trackPoints.push(endPoint);
        this.totalDistanceM = endPoint.total_distance_m;
      } else {
        endPoint = this.trackPoints[this.trackPoints.length - 1];
      }
      
      const wvvCompliantCount = this.trackPoints.filter(p => p.is_wvv_compliant).length;
      const avgAccuracy = this.trackPoints.reduce((sum, p) => sum + p.accuracy_m, 0) / this.trackPoints.length;
      const maxSpeed = Math.max(...this.trackPoints.map(p => p.speed_kmh ?? 0));
      
      const startTime = new Date(this.journey.start_time).getTime();
      const endTime = new Date(endPoint.timestamp).getTime();
      const durationMinutes = (endTime - startTime) / (1000 * 60);
      
      const trackSummary: TrackSummary = {
        total_points: this.trackPoints.length,
        wvv_compliant_count: wvvCompliantCount,
        average_accuracy_m: Math.round(avgAccuracy),
        max_speed_kmh: Math.round(maxSpeed),
        duration_minutes: Math.round(durationMinutes)
      };
      
      const payload: EndJourneyPayload = {
        end_latitude: endPoint.latitude,
        end_longitude: endPoint.longitude,
        end_accuracy_m: endPoint.accuracy_m,
        end_timestamp: endPoint.timestamp,
        total_distance_km: metersToKilometers(this.totalDistanceM),
        wvv_compliant_points: wvvCompliantCount,
        total_points: this.trackPoints.length,
        track_summary: trackSummary
      };
      
      const response = await this.apiAdapter.endJourney(this.journey.id, payload);
      
      if (!response.success) {
        await this.startGPSTracking();
        this.startIntervals();
        return { success: false, error: response.message || 'Failed to end journey' };
      }
      
      this.journey.state = JourneyState.COMPLETED;
      this.journey.end_time = endPoint.timestamp;
      this.journey.end_location = endPoint;
      this.journey.total_distance_km = response.total_distance_km;
      this.journey.wvv_compliant_points = wvvCompliantCount;
      this.journey.total_points = this.trackPoints.length;
      
      await this.storageAdapter.clearSession();
      
      this.emitter.emit(JourneyEvent.STOPPED, { journey: this.journey });
      
      this.state = JourneyState.COMPLETED;
      this.resetState();
      
      return { success: true };
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      this.emitter.emit(JourneyEvent.ERROR, { error: errorMessage });
      return { success: false, error: errorMessage };
    }
  }
  
  async pause(): Promise<{ success: boolean; error?: string }> {
    if (this.state !== JourneyState.ACTIVE) {
      return { success: false, error: `Cannot pause journey in state: ${this.state}` };
    }
    
    this.stopIntervals();
    this.gpsAdapter.stopWatching();
    
    this.state = JourneyState.PAUSED;
    if (this.journey) {
      this.journey.state = JourneyState.PAUSED;
    }
    
    await this.saveSession();
    
    this.emitter.emit(JourneyEvent.PAUSED, { journey: this.journey });
    
    return { success: true };
  }
  
  async resume(): Promise<{ success: boolean; error?: string }> {
    if (this.state !== JourneyState.PAUSED) {
      return { success: false, error: `Cannot resume journey in state: ${this.state}` };
    }
    
    this.state = JourneyState.ACTIVE;
    if (this.journey) {
      this.journey.state = JourneyState.ACTIVE;
    }
    
    await this.startGPSTracking();
    this.startIntervals();
    await this.saveSession();
    
    this.emitter.emit(JourneyEvent.RESUMED, { journey: this.journey });
    
    return { success: true };
  }
  
  private async startGPSTracking(): Promise<void> {
    const callbacks: GPSAdapterCallbacks = {
      onPositionUpdate: (position) => this.handleGPSUpdate(position),
      onError: (error) => this.handleGPSError(error),
      onPermissionDenied: () => this.handlePermissionDenied()
    };
    
    await this.gpsAdapter.startWatching(callbacks);
  }
  
  private handleGPSUpdate(position: RawGPSPosition): void {
    if (this.state !== JourneyState.ACTIVE) return;
    
    if (!isHeartbeatAccuracyValid(position.accuracy)) {
      this.logger.warn(`GPS accuracy ${position.accuracy}m exceeds threshold, skipping`);
      return;
    }
    
    const batteryPct = this.config.batteryProvider?.() ?? null;
    const lastPoint = this.trackPoints[this.trackPoints.length - 1] ?? null;
    
    const newPoint = buildTrackPoint({
      rawPosition: position,
      previousPoint: lastPoint,
      totalDistanceSoFar: this.totalDistanceM,
      batteryPct
    });
    
    this.trackPoints.push(newPoint);
    this.totalDistanceM = newPoint.total_distance_m;
    
    if (this.journey) {
      this.journey.track_points = [...this.trackPoints];
      this.journey.total_distance_km = metersToKilometers(this.totalDistanceM);
      this.journey.total_points = this.trackPoints.length;
      if (newPoint.is_wvv_compliant) {
        this.journey.wvv_compliant_points++;
      }
      
      const invalidation = shouldInvalidateJourney(this.trackPoints, this.journey.transport_mode);
      if (invalidation.shouldInvalidate) {
        this.invalidateJourney(invalidation.reason!);
        return;
      }
    }
    
    this.emitter.emit(JourneyEvent.GPS_UPDATED, { 
      point: newPoint,
      totalDistanceKm: metersToKilometers(this.totalDistanceM)
    });
  }
  
  private handleGPSError(error: GPSError): void {
    this.logger.error('GPS Error:', error);
    this.emitter.emit(JourneyEvent.ERROR, { error: error.message });
  }
  
  private handlePermissionDenied(): void {
    this.emitter.emit(JourneyEvent.ERROR, { error: 'GPS permission denied' });
  }
  
  private startIntervals(): void {
    this.heartbeatInterval = this.timer.setInterval(
      () => this.sendHeartbeat(),
      this.config.heartbeatIntervalMs
    );
    
    this.sessionSaveInterval = this.timer.setInterval(
      () => this.saveSession(),
      this.config.sessionSaveIntervalMs
    );
  }
  
  private stopIntervals(): void {
    if (this.heartbeatInterval) {
      this.timer.clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
    if (this.sessionSaveInterval) {
      this.timer.clearInterval(this.sessionSaveInterval);
      this.sessionSaveInterval = null;
    }
  }
  
  private async sendHeartbeat(): Promise<void> {
    if (this.state !== JourneyState.ACTIVE || !this.journey?.id) return;
    
    const lastPoint = this.trackPoints[this.trackPoints.length - 1];
    if (!lastPoint) return;
    
    if (this.lastHeartbeatTime) {
      const lastHeartbeatPoint = this.trackPoints.find(
        p => new Date(p.timestamp).getTime() === this.lastHeartbeatTime
      );
      if (lastHeartbeatPoint) {
        const distanceSinceLastHeartbeat = lastPoint.total_distance_m - lastHeartbeatPoint.total_distance_m;
        if (distanceSinceLastHeartbeat < this.config.minDistanceForHeartbeatM) {
          return;
        }
      }
    }
    
    const payload: HeartbeatPayload = {
      latitude: lastPoint.latitude,
      longitude: lastPoint.longitude,
      accuracy_m: lastPoint.accuracy_m,
      timestamp: lastPoint.timestamp,
      speed_kmh: lastPoint.speed_kmh,
      distance_from_last_m: lastPoint.distance_from_last_m,
      total_distance_m: lastPoint.total_distance_m,
      is_wvv_compliant: lastPoint.is_wvv_compliant,
      altitude_m: lastPoint.altitude_m,
      heading: lastPoint.heading,
      battery_pct: lastPoint.battery_pct
    };
    
    try {
      await this.apiAdapter.sendHeartbeat(this.journey.id, payload);
      this.lastHeartbeatTime = new Date(lastPoint.timestamp).getTime();
      this.emitter.emit(JourneyEvent.HEARTBEAT_SENT, { point: lastPoint });
    } catch (error) {
      this.logger.error('Heartbeat failed:', error);
      this.emitter.emit(JourneyEvent.HEARTBEAT_FAILED, { error });
    }
  }
  
  private async saveSession(): Promise<void> {
    if (!this.journey) return;
    
    const lastPoint = this.trackPoints[this.trackPoints.length - 1];
    
    const session: JourneySession = {
      journey_id: this.journey.id,
      company_id: this.journey.company_id,
      transport_mode: this.journey.transport_mode,
      purpose: this.journey.purpose,
      purpose_details: this.journey.purpose_details,
      state: this.state,
      session_token: this.journey.session_token,
      start_time: this.journey.start_time,
      total_distance_m: this.totalDistanceM,
      last_latitude: lastPoint?.latitude ?? 0,
      last_longitude: lastPoint?.longitude ?? 0,
      saved_at: new Date().toISOString()
    };
    
    await this.storageAdapter.saveSession(session);
  }
  
  private invalidateJourney(reason: string): void {
    this.stopIntervals();
    this.gpsAdapter.stopWatching();
    
    this.state = JourneyState.INVALIDATED;
    if (this.journey) {
      this.journey.state = JourneyState.INVALIDATED;
      this.journey.invalidation_reason = reason;
    }
    
    this.storageAdapter.clearSession();
    
    this.emitter.emit(JourneyEvent.INVALIDATED, { 
      journey: this.journey,
      reason 
    });
  }
  
  private resetState(): void {
    this.state = JourneyState.IDLE;
    this.journey = null;
    this.trackPoints = [];
    this.totalDistanceM = 0;
    this.lastHeartbeatTime = null;
  }
  
  destroy(): void {
    this.stopIntervals();
    this.gpsAdapter.stopWatching();
    this.emitter.removeAllListeners();
  }
}
