import { TransportMode, JourneyPurpose } from './enums.js';

export interface StartJourneyPayload {
  company_id: number;
  transport_mode: TransportMode;
  purpose: JourneyPurpose;
  purpose_details: string | null;
  start_latitude: number;
  start_longitude: number;
  start_accuracy_m: number;
  start_timestamp: string;
}

export interface StartJourneyResponse {
  success: boolean;
  journey_id: number;
  session_token: string;
  message?: string;
}

export interface HeartbeatPayload {
  latitude: number;
  longitude: number;
  accuracy_m: number;
  timestamp: string;
  speed_kmh: number | null;
  distance_from_last_m: number;
  total_distance_m: number;
  is_wvv_compliant: boolean;
  altitude_m: number | null;
  heading: number | null;
  battery_pct: number | null;
}

export interface HeartbeatResponse {
  success: boolean;
  message?: string;
}

export interface EndJourneyPayload {
  end_latitude: number;
  end_longitude: number;
  end_accuracy_m: number;
  end_timestamp: string;
  total_distance_km: number;
  wvv_compliant_points: number;
  total_points: number;
  track_summary: TrackSummary;
}

export interface TrackSummary {
  total_points: number;
  wvv_compliant_count: number;
  average_accuracy_m: number;
  max_speed_kmh: number;
  duration_minutes: number;
}

export interface EndJourneyResponse {
  success: boolean;
  journey_id: number;
  status: string;
  total_distance_km: number;
  message?: string;
}

export interface ActiveJourneyResponse {
  has_active_journey: boolean;
  journey: {
    id: number;
    company_id: number;
    transport_mode: TransportMode;
    purpose: JourneyPurpose;
    start_time: string;
    start_latitude: number;
    start_longitude: number;
    total_distance_km: number;
    session_token: string;
  } | null;
}
