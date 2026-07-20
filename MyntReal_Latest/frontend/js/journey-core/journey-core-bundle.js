/**
 * Journey Core Bundle for Web (DC_JOURNEY_UNIFIED_001)
 * 
 * Browser-compatible implementation of the unified journey tracking core.
 * This is a direct port of /shared/journey-core/ for browser use.
 * 
 * ALL MATH AND VALIDATION LIVES HERE - adapters are dumb pipes.
 */

(function(window) {
    'use strict';
    
    const JourneyState = {
        IDLE: 'idle',
        ACTIVE: 'active',
        PAUSED: 'paused',
        COMPLETED: 'completed',
        INVALIDATED: 'invalidated'
    };
    
    const TransportMode = {
        BIKE: 'bike',
        CAR: 'car',
        ELECTRIC_BIKE: 'electric_bike',
        CART: 'cart',
        LOCAL_TRANSPORT: 'local_transport',
        OTHERS: 'others'
    };
    
    const JourneyPurpose = {
        CLIENT_VISIT: 'client_visit',
        SITE_INSPECTION: 'site_inspection',
        MEETING: 'meeting',
        DELIVERY: 'delivery',
        COLLECTION: 'collection',
        OTHER: 'other'
    };
    
    const JourneyEvent = {
        STARTED: 'journey:started',
        STOPPED: 'journey:stopped',
        PAUSED: 'journey:paused',
        RESUMED: 'journey:resumed',
        GPS_UPDATED: 'gps:updated',
        HEARTBEAT_SENT: 'heartbeat:sent',
        HEARTBEAT_FAILED: 'heartbeat:failed',
        INVALIDATED: 'journey:invalidated',
        ERROR: 'journey:error',
        SESSION_RESTORED: 'session:restored'
    };
    
    const WVV_ACCURACY_THRESHOLD_M = 100;
    const HEARTBEAT_ACCURACY_THRESHOLD_M = 500;
    
    const TRANSPORT_MAX_SPEEDS_KMH = {
        [TransportMode.BIKE]: 40,
        [TransportMode.CAR]: 120,
        [TransportMode.ELECTRIC_BIKE]: 45,
        [TransportMode.CART]: 25,
        [TransportMode.LOCAL_TRANSPORT]: 80,
        [TransportMode.OTHERS]: 100
    };
    
    function toRadians(degrees) {
        return degrees * (Math.PI / 180);
    }
    
    function calculateHaversineDistance(lat1, lon1, lat2, lon2) {
        const EARTH_RADIUS_M = 6371000;
        const dLat = toRadians(lat2 - lat1);
        const dLon = toRadians(lon2 - lon1);
        
        const a = 
            Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(toRadians(lat1)) * Math.cos(toRadians(lat2)) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
        
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        
        return EARTH_RADIUS_M * c;
    }
    
    function calculateSpeed(lat1, lon1, timestamp1, lat2, lon2, timestamp2) {
        const distance_m = calculateHaversineDistance(lat1, lon1, lat2, lon2);
        
        const time1 = new Date(timestamp1).getTime();
        const time2 = new Date(timestamp2).getTime();
        const time_diff_hours = (time2 - time1) / (1000 * 60 * 60);
        
        if (time_diff_hours <= 0) return null;
        
        const distance_km = distance_m / 1000;
        return distance_km / time_diff_hours;
    }
    
    function metersToKilometers(meters) {
        return meters / 1000;
    }
    
    function getAccuracyLevel(accuracy_m) {
        if (accuracy_m <= 50) return 'high';
        if (accuracy_m <= 100) return 'medium';
        if (accuracy_m <= 500) return 'low';
        return 'weak_signal';
    }
    
    function isWVVCompliant(accuracy_m) {
        return accuracy_m <= WVV_ACCURACY_THRESHOLD_M;
    }
    
    function isHeartbeatAccuracyValid(accuracy_m) {
        return accuracy_m <= HEARTBEAT_ACCURACY_THRESHOLD_M;
    }
    
    function buildTrackPoint(rawPosition, previousPoint, totalDistanceSoFar, batteryPct) {
        const timestamp = new Date(rawPosition.timestamp).toISOString();
        const accuracy_m = rawPosition.accuracy;
        const accuracy_level = getAccuracyLevel(accuracy_m);
        const is_wvv_compliant = isWVVCompliant(accuracy_m);
        
        let distance_from_last_m = 0;
        let speed_kmh = null;
        
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
            accuracy_m: accuracy_m,
            timestamp: timestamp,
            speed_kmh: speed_kmh,
            distance_from_last_m: distance_from_last_m,
            total_distance_m: total_distance_m,
            altitude_m: rawPosition.altitude,
            heading: rawPosition.heading,
            battery_pct: batteryPct,
            is_wvv_compliant: is_wvv_compliant,
            validation_reason: validation_reason,
            accuracy_level: accuracy_level
        };
    }
    
    function shouldInvalidateJourney(trackPoints, transportMode) {
        if (trackPoints.length < 3) {
            return { shouldInvalidate: false, reason: null };
        }
        
        let consecutiveSpeedViolations = 0;
        const maxSpeedKmh = TRANSPORT_MAX_SPEEDS_KMH[transportMode] || 100;
        
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
        
        const compliantCount = trackPoints.filter(p => p.is_wvv_compliant).length;
        const wvvRatio = compliantCount / trackPoints.length;
        
        if (trackPoints.length >= 10 && wvvRatio < 0.3) {
            return {
                shouldInvalidate: true,
                reason: `WVV compliance ratio ${(wvvRatio * 100).toFixed(1)}% below minimum 30%`
            };
        }
        
        return { shouldInvalidate: false, reason: null };
    }
    
    function createEventEmitter(logger) {
        const listeners = new Map();
        const log = logger || { error: () => {} };
        
        return {
            on(event, callback) {
                if (!listeners.has(event)) {
                    listeners.set(event, new Set());
                }
                listeners.get(event).add(callback);
            },
            
            off(event, callback) {
                const eventListeners = listeners.get(event);
                if (eventListeners) {
                    eventListeners.delete(callback);
                }
            },
            
            emit(event, data) {
                const eventListeners = listeners.get(event);
                if (eventListeners) {
                    eventListeners.forEach(callback => {
                        try {
                            callback(data);
                        } catch (error) {
                            log.error(`Error in event listener for ${event}:`, error);
                        }
                    });
                }
            },
            
            removeAllListeners(event) {
                if (event) {
                    listeners.delete(event);
                } else {
                    listeners.clear();
                }
            }
        };
    }
    
    const DEFAULT_CONFIG = {
        heartbeatIntervalMs: 15000,
        sessionSaveIntervalMs: 60000,
        minDistanceForHeartbeatM: 0
    };
    
    class JourneyEngine {
        constructor(gpsAdapter, storageAdapter, apiAdapter, config = {}, platform = {}) {
            this._state = JourneyState.IDLE;
            this._journey = null;
            this._trackPoints = [];
            this._totalDistanceM = 0;
            
            this._gpsAdapter = gpsAdapter;
            this._storageAdapter = storageAdapter;
            this._apiAdapter = apiAdapter;
            this._config = { ...DEFAULT_CONFIG, ...config };
            
            this._logger = platform.logger || { log: () => {}, warn: () => {}, error: () => {} };
            this._timer = platform.timer || { setInterval: () => null, clearInterval: () => {} };
            
            this._emitter = createEventEmitter(this._logger);
            this._heartbeatInterval = null;
            this._sessionSaveInterval = null;
            this._lastHeartbeatTime = null;
        }
        
        on(event, callback) {
            this._emitter.on(event, callback);
        }
        
        off(event, callback) {
            this._emitter.off(event, callback);
        }
        
        getState() {
            return this._state;
        }
        
        getJourney() {
            return this._journey;
        }
        
        getTrackPoints() {
            return [...this._trackPoints];
        }
        
        getTotalDistanceKm() {
            return metersToKilometers(this._totalDistanceM);
        }
        
        async initialize() {
            const hasSession = await this._storageAdapter.hasSession();
            if (hasSession) {
                await this._restoreSession();
            }
        }
        
        async _restoreSession() {
            try {
                const session = await this._storageAdapter.loadSession();
                if (!session) return;
                
                const savedAt = new Date(session.saved_at);
                const now = new Date();
                const hoursSinceSave = (now.getTime() - savedAt.getTime()) / (1000 * 60 * 60);
                
                if (hoursSinceSave > 24) {
                    this._logger.warn('Session expired (>24 hours old)');
                    await this._storageAdapter.clearSession();
                    return;
                }
                
                const activeJourneyResponse = await this._apiAdapter.getActiveJourney();
                if (!activeJourneyResponse.has_active_journey || !activeJourneyResponse.journey) {
                    await this._storageAdapter.clearSession();
                    return;
                }
                
                const serverJourney = activeJourneyResponse.journey;
                
                this._journey = {
                    id: serverJourney.id,
                    company_id: serverJourney.company_id,
                    transport_mode: serverJourney.transport_mode,
                    purpose: serverJourney.purpose,
                    purpose_details: session.purpose_details,
                    state: JourneyState.ACTIVE,
                    start_time: serverJourney.start_time,
                    end_time: null,
                    start_location: {
                        latitude: serverJourney.start_latitude,
                        longitude: serverJourney.start_longitude,
                        accuracy_m: 0,
                        timestamp: serverJourney.start_time,
                        speed_kmh: null,
                        distance_from_last_m: 0,
                        total_distance_m: 0,
                        altitude_m: null,
                        heading: null,
                        battery_pct: null,
                        is_wvv_compliant: true,
                        validation_reason: null,
                        accuracy_level: 'high'
                    },
                    end_location: null,
                    start_address: null,
                    end_address: null,
                    track_points: [],
                    total_distance_km: serverJourney.total_distance_km,
                    session_token: serverJourney.session_token,
                    invalidation_reason: null,
                    wvv_compliant_points: 0,
                    total_points: 0
                };
                
                this._totalDistanceM = serverJourney.total_distance_km * 1000;
                this._state = JourneyState.ACTIVE;
                
                await this._startGPSTracking();
                this._startIntervals();
                
                this._emitter.emit(JourneyEvent.SESSION_RESTORED, { journey: this._journey });
                
            } catch (error) {
                this._logger.error('Failed to restore session:', error);
                await this._storageAdapter.clearSession();
            }
        }
        
        async start(input) {
            if (this._state !== JourneyState.IDLE) {
                return { success: false, error: `Cannot start journey in state: ${this._state}` };
            }
            
            if (!input.company_id || typeof input.company_id !== 'number') {
                return { success: false, error: 'company_id must be a positive number' };
            }
            
            try {
                const position = await this._gpsAdapter.getCurrentPosition();
                if (!position) {
                    return { success: false, error: 'Unable to get GPS position' };
                }
                
                if (!isHeartbeatAccuracyValid(position.accuracy)) {
                    return { success: false, error: `GPS accuracy ${position.accuracy}m too low (max 500m)` };
                }
                
                const batteryPct = this._config.batteryProvider ? this._config.batteryProvider() : null;
                const startPoint = buildTrackPoint(position, null, 0, batteryPct);
                
                const payload = {
                    company_id: input.company_id,
                    transport_mode: input.transport_mode,
                    purpose: input.purpose,
                    purpose_details: input.purpose_details || null,
                    start_latitude: startPoint.latitude,
                    start_longitude: startPoint.longitude,
                    start_accuracy_m: startPoint.accuracy_m,
                    start_timestamp: startPoint.timestamp
                };
                
                const response = await this._apiAdapter.startJourney(payload);
                
                if (!response.success) {
                    return { success: false, error: response.message || 'Failed to start journey' };
                }
                
                this._journey = {
                    id: response.journey_id,
                    company_id: input.company_id,
                    transport_mode: input.transport_mode,
                    purpose: input.purpose,
                    purpose_details: input.purpose_details || null,
                    state: JourneyState.ACTIVE,
                    start_time: startPoint.timestamp,
                    end_time: null,
                    start_location: startPoint,
                    end_location: null,
                    start_address: null,
                    end_address: null,
                    track_points: [startPoint],
                    total_distance_km: 0,
                    session_token: response.session_token,
                    invalidation_reason: null,
                    wvv_compliant_points: startPoint.is_wvv_compliant ? 1 : 0,
                    total_points: 1
                };
                
                this._trackPoints = [startPoint];
                this._totalDistanceM = 0;
                this._state = JourneyState.ACTIVE;
                
                await this._saveSession();
                await this._startGPSTracking();
                this._startIntervals();
                
                this._emitter.emit(JourneyEvent.STARTED, { journey: this._journey });
                
                return { success: true };
                
            } catch (error) {
                const errorMessage = error instanceof Error ? error.message : 'Unknown error';
                this._emitter.emit(JourneyEvent.ERROR, { error: errorMessage });
                return { success: false, error: errorMessage };
            }
        }
        
        async stop() {
            if (this._state !== JourneyState.ACTIVE && this._state !== JourneyState.PAUSED) {
                return { success: false, error: `Cannot stop journey in state: ${this._state}` };
            }
            
            if (!this._journey || !this._journey.id) {
                return { success: false, error: 'No active journey' };
            }
            
            try {
                this._stopIntervals();
                this._gpsAdapter.stopWatching();
                
                const position = await this._gpsAdapter.getCurrentPosition();
                let endPoint;
                
                if (position) {
                    const batteryPct = this._config.batteryProvider ? this._config.batteryProvider() : null;
                    const lastPoint = this._trackPoints[this._trackPoints.length - 1] || null;
                    
                    endPoint = buildTrackPoint(position, lastPoint, this._totalDistanceM, batteryPct);
                    
                    this._trackPoints.push(endPoint);
                    this._totalDistanceM = endPoint.total_distance_m;
                } else {
                    endPoint = this._trackPoints[this._trackPoints.length - 1];
                }
                
                const wvvCompliantCount = this._trackPoints.filter(p => p.is_wvv_compliant).length;
                const avgAccuracy = this._trackPoints.reduce((sum, p) => sum + p.accuracy_m, 0) / this._trackPoints.length;
                const maxSpeed = Math.max(...this._trackPoints.map(p => p.speed_kmh || 0));
                
                const startTime = new Date(this._journey.start_time).getTime();
                const endTime = new Date(endPoint.timestamp).getTime();
                const durationMinutes = (endTime - startTime) / (1000 * 60);
                
                const trackSummary = {
                    total_points: this._trackPoints.length,
                    wvv_compliant_count: wvvCompliantCount,
                    average_accuracy_m: Math.round(avgAccuracy),
                    max_speed_kmh: Math.round(maxSpeed),
                    duration_minutes: Math.round(durationMinutes)
                };
                
                const payload = {
                    end_latitude: endPoint.latitude,
                    end_longitude: endPoint.longitude,
                    end_accuracy_m: endPoint.accuracy_m,
                    end_timestamp: endPoint.timestamp,
                    total_distance_km: metersToKilometers(this._totalDistanceM),
                    wvv_compliant_points: wvvCompliantCount,
                    total_points: this._trackPoints.length,
                    track_summary: trackSummary
                };
                
                const response = await this._apiAdapter.endJourney(this._journey.id, payload);
                
                if (!response.success) {
                    await this._startGPSTracking();
                    this._startIntervals();
                    return { success: false, error: response.message || 'Failed to end journey' };
                }
                
                this._journey.state = JourneyState.COMPLETED;
                this._journey.end_time = endPoint.timestamp;
                this._journey.end_location = endPoint;
                this._journey.total_distance_km = response.total_distance_km;
                this._journey.wvv_compliant_points = wvvCompliantCount;
                this._journey.total_points = this._trackPoints.length;
                
                await this._storageAdapter.clearSession();
                
                this._emitter.emit(JourneyEvent.STOPPED, { journey: this._journey });
                
                this._state = JourneyState.COMPLETED;
                this._resetState();
                
                return { success: true };
                
            } catch (error) {
                const errorMessage = error instanceof Error ? error.message : 'Unknown error';
                this._emitter.emit(JourneyEvent.ERROR, { error: errorMessage });
                return { success: false, error: errorMessage };
            }
        }
        
        async attachToJourney(existingJourney) {
            if (this._state === JourneyState.ACTIVE) {
                return { success: false, error: 'Journey already active' };
            }
            
            this._journey = {
                id: existingJourney.id,
                company_id: existingJourney.company_id,
                transport_mode: existingJourney.transport_mode || 'bike',
                purpose: existingJourney.purpose || 'other',
                start_time: existingJourney.start_time || new Date().toISOString(),
                start_latitude: existingJourney.start_latitude,
                start_longitude: existingJourney.start_longitude,
                state: JourneyState.ACTIVE,
                total_distance_km: existingJourney.total_distance_km || 0,
                wvv_compliant_points: 0,
                total_points: 0
            };
            
            this._state = JourneyState.ACTIVE;
            this._totalDistanceM = (existingJourney.total_distance_km || 0) * 1000;
            this._trackPoints = [];
            
            await this._startGPSTracking();
            this._startIntervals();
            
            this._logger.info(`Attached to existing journey: ${existingJourney.id}`);
            this._emitter.emit(JourneyEvent.STARTED, { journey: this._journey });
            
            return { success: true, journey_id: existingJourney.id };
        }
        
        async pause() {
            if (this._state !== JourneyState.ACTIVE) {
                return { success: false, error: `Cannot pause journey in state: ${this._state}` };
            }
            
            this._stopIntervals();
            this._gpsAdapter.stopWatching();
            
            this._state = JourneyState.PAUSED;
            if (this._journey) {
                this._journey.state = JourneyState.PAUSED;
            }
            
            await this._saveSession();
            
            this._emitter.emit(JourneyEvent.PAUSED, { journey: this._journey });
            
            return { success: true };
        }
        
        async resume() {
            if (this._state !== JourneyState.PAUSED) {
                return { success: false, error: `Cannot resume journey in state: ${this._state}` };
            }
            
            this._state = JourneyState.ACTIVE;
            if (this._journey) {
                this._journey.state = JourneyState.ACTIVE;
            }
            
            await this._startGPSTracking();
            this._startIntervals();
            await this._saveSession();
            
            this._emitter.emit(JourneyEvent.RESUMED, { journey: this._journey });
            
            return { success: true };
        }
        
        async _startGPSTracking() {
            const callbacks = {
                onPositionUpdate: (position) => this._handleGPSUpdate(position),
                onError: (error) => this._handleGPSError(error),
                onPermissionDenied: () => this._handlePermissionDenied()
            };
            
            await this._gpsAdapter.startWatching(callbacks);
        }
        
        _handleGPSUpdate(position) {
            if (this._state !== JourneyState.ACTIVE) return;
            
            if (!isHeartbeatAccuracyValid(position.accuracy)) {
                this._logger.warn(`GPS accuracy ${position.accuracy}m exceeds threshold, skipping`);
                return;
            }
            
            const batteryPct = this._config.batteryProvider ? this._config.batteryProvider() : null;
            const lastPoint = this._trackPoints[this._trackPoints.length - 1] || null;
            
            const newPoint = buildTrackPoint(position, lastPoint, this._totalDistanceM, batteryPct);
            
            this._trackPoints.push(newPoint);
            this._totalDistanceM = newPoint.total_distance_m;
            
            if (this._journey) {
                this._journey.track_points = [...this._trackPoints];
                this._journey.total_distance_km = metersToKilometers(this._totalDistanceM);
                this._journey.total_points = this._trackPoints.length;
                if (newPoint.is_wvv_compliant) {
                    this._journey.wvv_compliant_points++;
                }
                
                const invalidation = shouldInvalidateJourney(this._trackPoints, this._journey.transport_mode);
                if (invalidation.shouldInvalidate) {
                    this._invalidateJourney(invalidation.reason);
                    return;
                }
            }
            
            this._emitter.emit(JourneyEvent.GPS_UPDATED, { 
                point: newPoint,
                totalDistanceKm: metersToKilometers(this._totalDistanceM)
            });
        }
        
        _handleGPSError(error) {
            this._logger.error('GPS Error:', error);
            this._emitter.emit(JourneyEvent.ERROR, { error: error.message });
        }
        
        _handlePermissionDenied() {
            this._emitter.emit(JourneyEvent.ERROR, { error: 'GPS permission denied' });
        }
        
        _startIntervals() {
            this._heartbeatInterval = this._timer.setInterval(
                () => this._sendHeartbeat(),
                this._config.heartbeatIntervalMs
            );
            
            this._sessionSaveInterval = this._timer.setInterval(
                () => this._saveSession(),
                this._config.sessionSaveIntervalMs
            );
        }
        
        _stopIntervals() {
            if (this._heartbeatInterval) {
                this._timer.clearInterval(this._heartbeatInterval);
                this._heartbeatInterval = null;
            }
            if (this._sessionSaveInterval) {
                this._timer.clearInterval(this._sessionSaveInterval);
                this._sessionSaveInterval = null;
            }
        }
        
        async _sendHeartbeat() {
            if (this._state !== JourneyState.ACTIVE || !this._journey || !this._journey.id) return;
            
            const lastPoint = this._trackPoints[this._trackPoints.length - 1];
            if (!lastPoint) return;
            
            if (this._lastHeartbeatTime) {
                const lastHeartbeatPoint = this._trackPoints.find(
                    p => new Date(p.timestamp).getTime() === this._lastHeartbeatTime
                );
                if (lastHeartbeatPoint) {
                    const distanceSinceLastHeartbeat = lastPoint.total_distance_m - lastHeartbeatPoint.total_distance_m;
                    if (distanceSinceLastHeartbeat < this._config.minDistanceForHeartbeatM) {
                        return;
                    }
                }
            }
            
            const payload = {
                latitude: lastPoint.latitude,
                longitude: lastPoint.longitude,
                accuracy_m: lastPoint.accuracy_m,
                timestamp: lastPoint.timestamp,
                speed_kmh: lastPoint.speed_kmh,
                distance_from_last_m: lastPoint.distance_from_last_m,
                total_distance_m: lastPoint.total_distance_m,
                is_wvv_compliant: lastPoint.is_wvv_compliant,
                altitude_m: lastPoint.altitude_m,
                heading: lastPoint.heading,
                battery_pct: lastPoint.battery_pct
            };
            
            try {
                const response = await this._apiAdapter.sendHeartbeat(this._journey.id, payload);
                this._lastHeartbeatTime = new Date(lastPoint.timestamp).getTime();
                this._emitter.emit(JourneyEvent.HEARTBEAT_SENT, { point: lastPoint, response: response || {} });
            } catch (error) {
                this._logger.error('Heartbeat failed:', error);
                this._emitter.emit(JourneyEvent.HEARTBEAT_FAILED, { error, point: lastPoint });
            }
        }
        
        async _saveSession() {
            if (!this._journey) return;
            
            const lastPoint = this._trackPoints[this._trackPoints.length - 1];
            
            const session = {
                journey_id: this._journey.id,
                company_id: this._journey.company_id,
                transport_mode: this._journey.transport_mode,
                purpose: this._journey.purpose,
                purpose_details: this._journey.purpose_details,
                state: this._state,
                session_token: this._journey.session_token,
                start_time: this._journey.start_time,
                total_distance_m: this._totalDistanceM,
                last_latitude: lastPoint ? lastPoint.latitude : 0,
                last_longitude: lastPoint ? lastPoint.longitude : 0,
                saved_at: new Date().toISOString()
            };
            
            await this._storageAdapter.saveSession(session);
        }
        
        _invalidateJourney(reason) {
            this._stopIntervals();
            this._gpsAdapter.stopWatching();
            
            this._state = JourneyState.INVALIDATED;
            if (this._journey) {
                this._journey.state = JourneyState.INVALIDATED;
                this._journey.invalidation_reason = reason;
            }
            
            this._storageAdapter.clearSession();
            
            this._emitter.emit(JourneyEvent.INVALIDATED, { 
                journey: this._journey,
                reason 
            });
        }
        
        _resetState() {
            this._state = JourneyState.IDLE;
            this._journey = null;
            this._trackPoints = [];
            this._totalDistanceM = 0;
            this._lastHeartbeatTime = null;
        }
        
        destroy() {
            this._stopIntervals();
            this._gpsAdapter.stopWatching();
            this._emitter.removeAllListeners();
        }
    }
    
    window.JourneyCore = {
        JourneyState,
        TransportMode,
        JourneyPurpose,
        JourneyEvent,
        JourneyEngine,
        WVV_ACCURACY_THRESHOLD_M,
        HEARTBEAT_ACCURACY_THRESHOLD_M,
        TRANSPORT_MAX_SPEEDS_KMH,
        calculateHaversineDistance,
        isWVVCompliant,
        isHeartbeatAccuracyValid,
        metersToKilometers
    };
    
})(window);
