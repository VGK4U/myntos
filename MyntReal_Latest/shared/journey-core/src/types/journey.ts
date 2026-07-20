import { JourneyState, TransportMode, JourneyPurpose } from './enums.js';
import { TrackPoint } from './track-point.js';

export interface Journey {
  id: number | null;
  company_id: number;
  transport_mode: TransportMode;
  purpose: JourneyPurpose;
  purpose_details: string | null;
  
  state: JourneyState;
  
  start_time: string;
  end_time: string | null;
  
  start_location: TrackPoint;
  end_location: TrackPoint | null;
  
  start_address: string | null;
  end_address: string | null;
  
  track_points: TrackPoint[];
  total_distance_km: number;
  
  session_token: string | null;
  
  invalidation_reason: string | null;
  wvv_compliant_points: number;
  total_points: number;
}

export interface JourneySession {
  journey_id: number | null;
  company_id: number;
  transport_mode: TransportMode;
  purpose: JourneyPurpose;
  purpose_details: string | null;
  state: JourneyState;
  session_token: string | null;
  start_time: string;
  total_distance_m: number;
  last_latitude: number;
  last_longitude: number;
  saved_at: string;
}

export interface StartJourneyInput {
  company_id: number;
  transport_mode: TransportMode;
  purpose: JourneyPurpose;
  purpose_details?: string;
}
