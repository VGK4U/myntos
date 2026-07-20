/**
 * Web API Adapter - HTTP client for canonical paths (DC_JOURNEY_UNIFIED_001)
 * 
 * RULE 1 COMPLIANCE:
 * - Only handles HTTP requests
 * - Uses canonical /staff/journeys/* paths only
 * - No validation or transformation of business data
 */

const CANONICAL_API_PATHS = {
    START_JOURNEY: '/staff/journeys/start',
    HEARTBEAT: (journeyId) => `/staff/journeys/${journeyId}/heartbeat`,
    END_JOURNEY: (journeyId) => `/staff/journeys/${journeyId}/end`,
    GET_ACTIVE: '/staff/journeys/active',
    LIST_MY_JOURNEYS: '/staff/journeys/my'
};

class WebAPIAdapter {
    constructor(baseUrl = '/api/v1') {
        this.baseUrl = baseUrl;
        this.authToken = null;
    }
    
    getAuthToken() {
        return this.authToken || localStorage.getItem('staff_token');
    }
    
    setAuthToken(token) {
        this.authToken = token;
    }
    
    async _fetch(path, options = {}) {
        const token = this.getAuthToken();
        if (!token) {
            throw new Error('NO_TOKEN');
        }
        
        const response = await fetch(`${this.baseUrl}${path}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
                ...options.headers
            }
        });
        
        if (response.status === 401) {
            throw new Error('AUTH_EXPIRED');
        }
        
        return response;
    }
    
    async startJourney(payload) {
        try {
            const response = await this._fetch(CANONICAL_API_PATHS.START_JOURNEY, {
                method: 'POST',
                body: JSON.stringify(payload)
            });
            
            const data = await response.json();
            
            if (response.ok) {
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
        } catch (error) {
            return {
                success: false,
                message: error.message
            };
        }
    }
    
    async sendHeartbeat(journeyId, payload) {
        try {
            const response = await this._fetch(CANONICAL_API_PATHS.HEARTBEAT(journeyId), {
                method: 'POST',
                body: JSON.stringify(payload)
            });
            
            const data = await response.json();
            
            if (response.ok) {
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
        } catch (error) {
            return {
                success: false,
                message: error.message
            };
        }
    }
    
    async endJourney(journeyId, payload) {
        try {
            const response = await this._fetch(CANONICAL_API_PATHS.END_JOURNEY(journeyId), {
                method: 'POST',
                body: JSON.stringify(payload)
            });
            
            const data = await response.json();
            
            if (response.ok) {
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
        } catch (error) {
            return {
                success: false,
                message: error.message
            };
        }
    }
    
    async getActiveJourney() {
        try {
            const response = await this._fetch(CANONICAL_API_PATHS.GET_ACTIVE);
            
            if (response.ok) {
                const data = await response.json();
                
                if (data.journey) {
                    return {
                        has_active_journey: true,
                        journey: {
                            id: data.journey.id,
                            company_id: data.journey.company_id,
                            transport_mode: data.journey.transport_mode,
                            purpose: data.journey.purpose,
                            start_time: data.journey.start_time,
                            start_latitude: data.journey.start_latitude,
                            start_longitude: data.journey.start_longitude,
                            total_distance_km: data.journey.total_distance_km || 0,
                            session_token: data.journey.session_token || null
                        }
                    };
                } else {
                    return {
                        has_active_journey: false,
                        journey: null
                    };
                }
            } else {
                return {
                    has_active_journey: false,
                    journey: null
                };
            }
        } catch (error) {
            return {
                has_active_journey: false,
                journey: null
            };
        }
    }
}

window.WebAPIAdapter = WebAPIAdapter;
window.CANONICAL_API_PATHS = CANONICAL_API_PATHS;
