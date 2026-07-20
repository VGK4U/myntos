import { GPSAccuracyLevel, TransportMode } from '../types/enums.js';
import { TrackPoint, RawGPSPosition } from '../types/track-point.js';

export const WVV_ACCURACY_THRESHOLD_M = 100;
export const HEARTBEAT_ACCURACY_THRESHOLD_M = 500;

export const TRANSPORT_MAX_SPEEDS_KMH: Record<TransportMode, number> = {
  [TransportMode.BIKE]: 40,
  [TransportMode.CAR]: 120,
  [TransportMode.ELECTRIC_BIKE]: 45,
  [TransportMode.CART]: 25,
  [TransportMode.LOCAL_TRANSPORT]: 80,
  [TransportMode.OTHERS]: 100
};

export function getAccuracyLevel(accuracy_m: number): GPSAccuracyLevel {
  if (accuracy_m <= 50) return GPSAccuracyLevel.HIGH;
  if (accuracy_m <= 100) return GPSAccuracyLevel.MEDIUM;
  if (accuracy_m <= 500) return GPSAccuracyLevel.LOW;
  return GPSAccuracyLevel.WEAK_SIGNAL;
}

export function isWVVCompliant(accuracy_m: number): boolean {
  return accuracy_m <= WVV_ACCURACY_THRESHOLD_M;
}

export function isHeartbeatAccuracyValid(accuracy_m: number): boolean {
  return accuracy_m <= HEARTBEAT_ACCURACY_THRESHOLD_M;
}

export function isSpeedValid(speed_kmh: number, transportMode: TransportMode): boolean {
  const maxSpeed = TRANSPORT_MAX_SPEEDS_KMH[transportMode];
  return speed_kmh <= maxSpeed;
}

export function validateTrackPoint(
  point: TrackPoint,
  transportMode: TransportMode
): { valid: boolean; reason: string | null } {
  if (point.accuracy_m > HEARTBEAT_ACCURACY_THRESHOLD_M) {
    return {
      valid: false,
      reason: `Accuracy ${point.accuracy_m}m exceeds maximum ${HEARTBEAT_ACCURACY_THRESHOLD_M}m`
    };
  }
  
  if (point.speed_kmh !== null && point.speed_kmh > TRANSPORT_MAX_SPEEDS_KMH[transportMode]) {
    return {
      valid: false,
      reason: `Speed ${point.speed_kmh}km/h exceeds maximum ${TRANSPORT_MAX_SPEEDS_KMH[transportMode]}km/h for ${transportMode}`
    };
  }
  
  return { valid: true, reason: null };
}

export interface SpeedValidationResult {
  isAnomaly: boolean;
  speedKmh: number;
  maxAllowed: number;
  reason: string | null;
}

export function validateSpeed(
  speedKmh: number | null,
  transportMode: TransportMode
): SpeedValidationResult {
  if (speedKmh === null) {
    return {
      isAnomaly: false,
      speedKmh: 0,
      maxAllowed: TRANSPORT_MAX_SPEEDS_KMH[transportMode],
      reason: null
    };
  }
  
  const maxAllowed = TRANSPORT_MAX_SPEEDS_KMH[transportMode];
  const isAnomaly = speedKmh > maxAllowed;
  
  return {
    isAnomaly,
    speedKmh,
    maxAllowed,
    reason: isAnomaly ? `Speed ${speedKmh}km/h exceeds max ${maxAllowed}km/h` : null
  };
}
