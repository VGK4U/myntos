import {
  StartJourneyPayload,
  StartJourneyResponse,
  HeartbeatPayload,
  HeartbeatResponse,
  EndJourneyPayload,
  EndJourneyResponse,
  ActiveJourneyResponse
} from '../types/api-payloads.js';

export interface JourneyAPIAdapter {
  startJourney(payload: StartJourneyPayload): Promise<StartJourneyResponse>;
  
  sendHeartbeat(journeyId: number, payload: HeartbeatPayload): Promise<HeartbeatResponse>;
  
  endJourney(journeyId: number, payload: EndJourneyPayload): Promise<EndJourneyResponse>;
  
  getActiveJourney(): Promise<ActiveJourneyResponse>;
  
  getAuthToken(): string | null;
  
  setAuthToken(token: string): void;
}

export const CANONICAL_API_PATHS = {
  START_JOURNEY: '/staff/journeys/start',
  HEARTBEAT: (journeyId: number) => `/staff/journeys/${journeyId}/heartbeat`,
  END_JOURNEY: (journeyId: number) => `/staff/journeys/${journeyId}/end`,
  GET_ACTIVE: '/staff/journeys/active',
  LIST_MY_JOURNEYS: '/staff/journeys/my'
} as const;
