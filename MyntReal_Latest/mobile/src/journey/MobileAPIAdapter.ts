/**
 * Mobile API Adapter - HTTP client for canonical paths (DC_JOURNEY_UNIFIED_001)
 * 
 * RULE 1 COMPLIANCE:
 * - Only handles HTTP requests
 * - Uses canonical /staff/journeys/* paths only
 * - No validation or transformation of business data
 * - Same payloads as Web
 */

import { CapacitorHttp, HttpResponse } from '@capacitor/core';
import type { 
    JourneyAPIAdapter, 
    StartJourneyPayload, 
    HeartbeatPayload, 
    EndJourneyPayload,
    StartJourneyResponse,
    HeartbeatResponse,
    EndJourneyResponse
} from './types';

const CANONICAL_API_PATHS = {
    START_JOURNEY: '/staff/journeys/start',
    HEARTBEAT: (journeyId: number) => `/staff/journeys/${journeyId}/heartbeat`,
    END_JOURNEY: (journeyId: number) => `/staff/journeys/${journeyId}/end`,
    GET_ACTIVE: '/staff/journeys/active',
    LIST_MY_JOURNEYS: '/staff/journeys/my'
};

export class MobileAPIAdapter implements JourneyAPIAdapter {
    private baseUrl: string;
    private authToken: string | null = null;

    constructor(baseUrl: string) {
        this.baseUrl = baseUrl;
    }

    setAuthToken(token: string): void {
        this.authToken = token;
    }

    getAuthToken(): string | null {
        return this.authToken;
    }

    private async _fetch(path: string, options: { method: string; body?: any }): Promise<HttpResponse> {
        const token = this.getAuthToken();
        if (!token) {
            throw new Error('NO_TOKEN');
        }

        const response = await CapacitorHttp.request({
            url: `${this.baseUrl}${path}`,
            method: options.method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            data: options.body
        });

        if (response.status === 401) {
            throw new Error('AUTH_EXPIRED');
        }

        return response;
    }

    async startJourney(payload: StartJourneyPayload): Promise<StartJourneyResponse> {
        try {
            const response = await this._fetch(CANONICAL_API_PATHS.START_JOURNEY, {
                method: 'POST',
                body: payload
            });

            const data = response.data;

            if (response.status >= 200 && response.status < 300) {
                return {
                    success: true,
                    journey_id: data.journey_id || data.id,
                    session_token: data.session_token || null,
                    message: data.message
                };
            } else {
                return {
                    success: false,
                    message: data.detail || data.message || 'Failed to start journey'
                };
            }
        } catch (error: any) {
            return {
                success: false,
                message: error.message
            };
        }
    }

    async sendHeartbeat(journeyId: number, payload: HeartbeatPayload): Promise<HeartbeatResponse> {
        try {
            const response = await this._fetch(CANONICAL_API_PATHS.HEARTBEAT(journeyId), {
                method: 'POST',
                body: payload
            });

            const data = response.data;

            if (response.status >= 200 && response.status < 300) {
                return {
                    success: true,
                    distance_km: data.distance_km || 0,
                    max_speed_kmh: data.max_speed_kmh || 0,
                    reimbursement_amount: data.reimbursement_amount || 0,
                    reimbursable_distance_km: data.reimbursable_distance_km || 0,
                    wvv_compliant: data.wvv_compliant !== false,
                    wvv_accuracy_m: data.wvv_accuracy_m,
                    wvv_reason: data.wvv_reason
                };
            } else {
                return {
                    success: false,
                    message: data.detail || data.message,
                    wvv_error: data.detail && data.detail.includes('WVV')
                };
            }
        } catch (error: any) {
            return {
                success: false,
                message: error.message
            };
        }
    }

    async endJourney(journeyId: number, payload: EndJourneyPayload): Promise<EndJourneyResponse> {
        try {
            const response = await this._fetch(CANONICAL_API_PATHS.END_JOURNEY(journeyId), {
                method: 'POST',
                body: payload
            });

            const data = response.data;

            if (response.status >= 200 && response.status < 300) {
                return {
                    success: true,
                    journey_id: data.journey_id || journeyId,
                    status: data.status || 'completed',
                    total_distance_km: data.total_distance_km || 0,
                    message: data.message
                };
            } else {
                return {
                    success: false,
                    message: data.detail || data.message || 'Failed to end journey'
                };
            }
        } catch (error: any) {
            return {
                success: false,
                message: error.message
            };
        }
    }

    async getActiveJourney(): Promise<any> {
        try {
            const response = await this._fetch(CANONICAL_API_PATHS.GET_ACTIVE, {
                method: 'GET'
            });

            if (response.status >= 200 && response.status < 300) {
                return response.data;
            }
            return null;
        } catch (error) {
            return null;
        }
    }
}
