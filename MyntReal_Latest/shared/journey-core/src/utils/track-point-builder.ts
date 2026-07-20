import { TrackPoint, RawGPSPosition, TrackPointBuilderInput } from '../types/track-point.js';
import { GPSAccuracyLevel } from '../types/enums.js';
import { calculateHaversineDistance, calculateSpeed } from './geo-utils.js';
import { getAccuracyLevel, isWVVCompliant } from '../validators/wvv-validator.js';

export function buildTrackPoint(input: TrackPointBuilderInput): TrackPoint {
  const { rawPosition, previousPoint, totalDistanceSoFar, batteryPct } = input;
  
  const timestamp = new Date(rawPosition.timestamp).toISOString();
  const accuracy_m = rawPosition.accuracy;
  const accuracy_level = getAccuracyLevel(accuracy_m);
  const is_wvv_compliant = isWVVCompliant(accuracy_m);
  
  let distance_from_last_m = 0;
  let speed_kmh: number | null = null;
  
  if (previousPoint) {
    distance_from_last_m = calculateHaversineDistance(
      previousPoint.latitude,
      previousPoint.longitude,
      rawPosition.latitude,
      rawPosition.longitude
    );
    
    speed_kmh = calculateSpeed(
      previousPoint.latitude,
      previousPoint.longitude,
      previousPoint.timestamp,
      rawPosition.latitude,
      rawPosition.longitude,
      timestamp
    );
    
    if (rawPosition.speed !== null && rawPosition.speed >= 0) {
      const hardwareSpeedKmh = rawPosition.speed * 3.6;
      if (speed_kmh !== null) {
        speed_kmh = (speed_kmh + hardwareSpeedKmh) / 2;
      } else {
        speed_kmh = hardwareSpeedKmh;
      }
    }
  }
  
  const total_distance_m = totalDistanceSoFar + distance_from_last_m;
  
  const validation_reason = is_wvv_compliant 
    ? null 
    : `Accuracy ${accuracy_m}m exceeds WVV threshold 100m`;
  
  return {
    latitude: rawPosition.latitude,
    longitude: rawPosition.longitude,
    accuracy_m,
    timestamp,
    speed_kmh,
    distance_from_last_m,
    total_distance_m,
    altitude_m: rawPosition.altitude,
    heading: rawPosition.heading,
    battery_pct: batteryPct,
    is_wvv_compliant,
    validation_reason,
    accuracy_level
  };
}

export function createStartTrackPoint(
  rawPosition: RawGPSPosition,
  batteryPct: number | null
): TrackPoint {
  return buildTrackPoint({
    rawPosition,
    previousPoint: null,
    totalDistanceSoFar: 0,
    batteryPct
  });
}
