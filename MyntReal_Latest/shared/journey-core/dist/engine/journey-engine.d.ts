import { Journey, StartJourneyInput } from '../types/journey.js';
import { TrackPoint } from '../types/track-point.js';
import { JourneyState, JourneyEvent } from '../types/enums.js';
import { GPSAdapter } from '../adapters/gps-adapter.js';
import { StorageAdapter } from '../adapters/storage-adapter.js';
import { JourneyAPIAdapter } from '../adapters/api-adapter.js';
import { PlatformAdapter } from '../adapters/platform-adapter.js';
export interface JourneyEngineConfig {
    heartbeatIntervalMs: number;
    sessionSaveIntervalMs: number;
    minDistanceForHeartbeatM: number;
    batteryProvider?: () => number | null;
}
export interface JourneyEngineState {
    journey: Journey | null;
    state: JourneyState;
    isGPSWatching: boolean;
    lastHeartbeatTime: number | null;
    pendingTrackPoints: TrackPoint[];
}
export declare class JourneyEngine {
    private state;
    private journey;
    private trackPoints;
    private totalDistanceM;
    private gpsAdapter;
    private storageAdapter;
    private apiAdapter;
    private config;
    private logger;
    private timer;
    private emitter;
    private heartbeatInterval;
    private sessionSaveInterval;
    private lastHeartbeatTime;
    constructor(gpsAdapter: GPSAdapter, storageAdapter: StorageAdapter, apiAdapter: JourneyAPIAdapter, config?: Partial<JourneyEngineConfig>, platform?: Partial<PlatformAdapter>);
    on(event: JourneyEvent, callback: (data: unknown) => void): void;
    off(event: JourneyEvent, callback: (data: unknown) => void): void;
    getState(): JourneyState;
    getJourney(): Journey | null;
    getTrackPoints(): TrackPoint[];
    getTotalDistanceKm(): number;
    initialize(): Promise<void>;
    private restoreSession;
    start(input: StartJourneyInput): Promise<{
        success: boolean;
        error?: string;
    }>;
    stop(): Promise<{
        success: boolean;
        error?: string;
    }>;
    pause(): Promise<{
        success: boolean;
        error?: string;
    }>;
    resume(): Promise<{
        success: boolean;
        error?: string;
    }>;
    private startGPSTracking;
    private handleGPSUpdate;
    private handleGPSError;
    private handlePermissionDenied;
    private startIntervals;
    private stopIntervals;
    private sendHeartbeat;
    private saveSession;
    private invalidateJourney;
    private resetState;
    destroy(): void;
}
//# sourceMappingURL=journey-engine.d.ts.map