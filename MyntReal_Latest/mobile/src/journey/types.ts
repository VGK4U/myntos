/**
 * Journey Core Types for Mobile (DC_JOURNEY_UNIFIED_001)
 * 
 * These types mirror the shared journey-core types for TypeScript compatibility.
 */

export interface RawGPSPosition {
    latitude: number;
    longitude: number;
    accuracy: number;
    altitude: number | null;
    speed: number | null;
    heading: number | null;
    timestamp: number;
}

export interface GPSError {
    code: number;
    message: string;
}

export interface GPSAdapterCallbacks {
    onPositionUpdate: (position: RawGPSPosition) => void;
    onError: (error: GPSError) => void;
    onPermissionDenied: () => void;
}

export interface GPSAdapter {
    startWatching(callbacks: GPSAdapterCallbacks): Promise<boolean>;
    stopWatching(): void;
    getCurrentPosition(): Promise<RawGPSPosition | null>;
    isWatching(): boolean;
    checkPermission(): Promise<'granted' | 'denied' | 'prompt'>;
    requestPermission(): Promise<boolean>;
}

export interface JourneySession {
    journeyId: number;
    startedAt: number;
    trackPoints: any[];
    totalDistanceM: number;
    lastPosition: RawGPSPosition | null;
}

export interface StorageAdapter {
    saveSession(session: JourneySession): Promise<void>;
    loadSession(): Promise<JourneySession | null>;
    clearSession(): Promise<void>;
    hasSession(): Promise<boolean>;
}

export interface StartJourneyPayload {
    company_id: number;
    transport_mode: string;
    purpose: string;
    destination?: string;
    start_location: {
        latitude: number;
        longitude: number;
        accuracy_m: number;
    };
}

export interface HeartbeatPayload {
    track_points: Array<{
        latitude: number;
        longitude: number;
        accuracy_m: number;
        timestamp: string;
        speed_kmh?: number;
        heading?: number;
        battery_percentage?: number;
    }>;
    battery_percentage?: number;
}

export interface EndJourneyPayload {
    end_location: {
        latitude: number;
        longitude: number;
        accuracy_m: number;
    };
    notes?: string;
}

export interface StartJourneyResponse {
    success: boolean;
    journey_id?: number;
    session_token?: string | null;
    message?: string;
}

export interface HeartbeatResponse {
    success: boolean;
    distance_km?: number;
    max_speed_kmh?: number;
    reimbursement_amount?: number;
    reimbursable_distance_km?: number;
    wvv_compliant?: boolean;
    wvv_accuracy_m?: number;
    wvv_reason?: string;
    message?: string;
    wvv_error?: boolean;
}

export interface EndJourneyResponse {
    success: boolean;
    journey_id?: number;
    status?: string;
    total_distance_km?: number;
    message?: string;
}

export interface JourneyAPIAdapter {
    setAuthToken(token: string): void;
    getAuthToken(): string | null;
    startJourney(payload: StartJourneyPayload): Promise<StartJourneyResponse>;
    sendHeartbeat(journeyId: number, payload: HeartbeatPayload): Promise<HeartbeatResponse>;
    endJourney(journeyId: number, payload: EndJourneyPayload): Promise<EndJourneyResponse>;
    getActiveJourney(): Promise<any>;
}

export type TimerHandle = any;

export interface Logger {
    log(...args: any[]): void;
    warn(...args: any[]): void;
    error(...args: any[]): void;
}

export interface TimerProvider {
    setInterval(callback: () => void, intervalMs: number): TimerHandle;
    clearInterval(handle: TimerHandle): void;
}

export interface PlatformAdapter {
    logger: Logger;
    timer: TimerProvider;
}

export enum JourneyState {
    IDLE = 'idle',
    ACTIVE = 'active',
    PAUSED = 'paused',
    COMPLETED = 'completed',
    INVALIDATED = 'invalidated'
}

export enum JourneyEvent {
    STARTED = 'journey:started',
    STOPPED = 'journey:stopped',
    PAUSED = 'journey:paused',
    RESUMED = 'journey:resumed',
    GPS_UPDATED = 'gps:updated',
    HEARTBEAT_SENT = 'heartbeat:sent',
    HEARTBEAT_FAILED = 'heartbeat:failed',
    INVALIDATED = 'journey:invalidated',
    ERROR = 'journey:error',
    SESSION_RESTORED = 'session:restored'
}
