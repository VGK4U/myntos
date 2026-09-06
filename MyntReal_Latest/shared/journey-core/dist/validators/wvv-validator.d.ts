import { GPSAccuracyLevel, TransportMode } from '../types/enums.js';
import { TrackPoint } from '../types/track-point.js';
export declare const WVV_ACCURACY_THRESHOLD_M = 100;
export declare const HEARTBEAT_ACCURACY_THRESHOLD_M = 500;
export declare const TRANSPORT_MAX_SPEEDS_KMH: Record<TransportMode, number>;
export declare function getAccuracyLevel(accuracy_m: number): GPSAccuracyLevel;
export declare function isWVVCompliant(accuracy_m: number): boolean;
export declare function isHeartbeatAccuracyValid(accuracy_m: number): boolean;
export declare function isSpeedValid(speed_kmh: number, transportMode: TransportMode): boolean;
export declare function validateTrackPoint(point: TrackPoint, transportMode: TransportMode): {
    valid: boolean;
    reason: string | null;
};
export interface SpeedValidationResult {
    isAnomaly: boolean;
    speedKmh: number;
    maxAllowed: number;
    reason: string | null;
}
export declare function validateSpeed(speedKmh: number | null, transportMode: TransportMode): SpeedValidationResult;
//# sourceMappingURL=wvv-validator.d.ts.map