import { StartJourneyPayload, StartJourneyResponse, HeartbeatPayload, HeartbeatResponse, EndJourneyPayload, EndJourneyResponse, ActiveJourneyResponse } from '../types/api-payloads.js';
export interface JourneyAPIAdapter {
    startJourney(payload: StartJourneyPayload): Promise<StartJourneyResponse>;
    sendHeartbeat(journeyId: number, payload: HeartbeatPayload): Promise<HeartbeatResponse>;
    endJourney(journeyId: number, payload: EndJourneyPayload): Promise<EndJourneyResponse>;
    getActiveJourney(): Promise<ActiveJourneyResponse>;
    getAuthToken(): string | null;
    setAuthToken(token: string): void;
}
export declare const CANONICAL_API_PATHS: {
    readonly START_JOURNEY: "/staff/journeys/start";
    readonly HEARTBEAT: (journeyId: number) => string;
    readonly END_JOURNEY: (journeyId: number) => string;
    readonly GET_ACTIVE: "/staff/journeys/active";
    readonly LIST_MY_JOURNEYS: "/staff/journeys/my";
};
//# sourceMappingURL=api-adapter.d.ts.map