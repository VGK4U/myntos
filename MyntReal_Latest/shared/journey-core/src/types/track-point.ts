import { GPSAccuracyLevel } from './enums.js';

export interface TrackPoint {
  latitude: number;
  longitude: number;
  accuracy_m: number;
  timestamp: string;
  
  speed_kmh: number | null;
  distance_from_last_m: number;
  total_distance_m: number;
  
  altitude_m: number | null;
  heading: number | null;
  battery_pct: number | null;
  
  is_wvv_compliant: boolean;
  validation_reason: string | null;
  accuracy_level: GPSAccuracyLevel;
}

export interface RawGPSPosition {
  latitude: number;
  longitude: number;
  accuracy: number;
  altitude: number | null;
  speed: number | null;
  heading: number | null;
  timestamp: number;
}

export interface TrackPointBuilderInput {
  rawPosition: RawGPSPosition;
  previousPoint: TrackPoint | null;
  totalDistanceSoFar: number;
  batteryPct: number | null;
}
