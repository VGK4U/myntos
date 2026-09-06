import { Journey, JourneySession, StartJourneyInput } from '../types/journey.js';
import { TransportMode } from '../types/enums.js';
import { TrackPoint } from '../types/track-point.js';
export interface ValidationResult {
    valid: boolean;
    errors: string[];
}
export declare function validateStartInput(input: StartJourneyInput): ValidationResult;
export declare function validateJourneyForEnd(journey: Journey): ValidationResult;
export declare function calculateWVVComplianceRatio(trackPoints: TrackPoint[]): number;
export declare function shouldInvalidateJourney(trackPoints: TrackPoint[], transportMode: TransportMode): {
    shouldInvalidate: boolean;
    reason: string | null;
};
export declare function validateSessionIntegrity(session: JourneySession): ValidationResult;
//# sourceMappingURL=journey-validator.d.ts.map