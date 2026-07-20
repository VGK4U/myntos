import { Journey, JourneySession, StartJourneyInput } from '../types/journey.js';
import { JourneyState, TransportMode, JourneyPurpose } from '../types/enums.js';
import { TrackPoint } from '../types/track-point.js';
import { WVV_ACCURACY_THRESHOLD_M, TRANSPORT_MAX_SPEEDS_KMH } from './wvv-validator.js';

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

export function validateStartInput(input: StartJourneyInput): ValidationResult {
  const errors: string[] = [];
  
  if (!input.company_id || typeof input.company_id !== 'number' || input.company_id <= 0) {
    errors.push('company_id must be a positive number');
  }
  
  if (!Object.values(TransportMode).includes(input.transport_mode)) {
    errors.push(`transport_mode must be one of: ${Object.values(TransportMode).join(', ')}`);
  }
  
  if (!Object.values(JourneyPurpose).includes(input.purpose)) {
    errors.push(`purpose must be one of: ${Object.values(JourneyPurpose).join(', ')}`);
  }
  
  return {
    valid: errors.length === 0,
    errors
  };
}

export function validateJourneyForEnd(journey: Journey): ValidationResult {
  const errors: string[] = [];
  
  if (journey.state !== JourneyState.ACTIVE && journey.state !== JourneyState.PAUSED) {
    errors.push(`Cannot end journey in state: ${journey.state}`);
  }
  
  if (journey.track_points.length < 2) {
    errors.push('Journey must have at least 2 track points');
  }
  
  return {
    valid: errors.length === 0,
    errors
  };
}

export function calculateWVVComplianceRatio(trackPoints: TrackPoint[]): number {
  if (trackPoints.length === 0) return 0;
  
  const compliantCount = trackPoints.filter(p => p.is_wvv_compliant).length;
  return compliantCount / trackPoints.length;
}

export function shouldInvalidateJourney(
  trackPoints: TrackPoint[],
  transportMode: TransportMode
): { shouldInvalidate: boolean; reason: string | null } {
  if (trackPoints.length < 3) {
    return { shouldInvalidate: false, reason: null };
  }
  
  let consecutiveSpeedViolations = 0;
  const maxSpeedKmh = TRANSPORT_MAX_SPEEDS_KMH[transportMode];
  
  for (const point of trackPoints) {
    if (point.speed_kmh !== null && point.speed_kmh > maxSpeedKmh * 1.5) {
      consecutiveSpeedViolations++;
      if (consecutiveSpeedViolations >= 5) {
        return {
          shouldInvalidate: true,
          reason: `5+ consecutive speed violations (>150% of max ${maxSpeedKmh}km/h)`
        };
      }
    } else {
      consecutiveSpeedViolations = 0;
    }
  }
  
  const wvvRatio = calculateWVVComplianceRatio(trackPoints);
  if (trackPoints.length >= 10 && wvvRatio < 0.3) {
    return {
      shouldInvalidate: true,
      reason: `WVV compliance ratio ${(wvvRatio * 100).toFixed(1)}% below minimum 30%`
    };
  }
  
  return { shouldInvalidate: false, reason: null };
}

export function validateSessionIntegrity(session: JourneySession): ValidationResult {
  const errors: string[] = [];
  
  if (!session.journey_id && session.state !== JourneyState.IDLE) {
    errors.push('Active session must have journey_id');
  }
  
  if (!session.session_token && session.state === JourneyState.ACTIVE) {
    errors.push('Active session must have session_token');
  }
  
  const savedAt = new Date(session.saved_at);
  const now = new Date();
  const hoursSinceSave = (now.getTime() - savedAt.getTime()) / (1000 * 60 * 60);
  
  if (hoursSinceSave > 24) {
    errors.push('Session expired (>24 hours old)');
  }
  
  return {
    valid: errors.length === 0,
    errors
  };
}
