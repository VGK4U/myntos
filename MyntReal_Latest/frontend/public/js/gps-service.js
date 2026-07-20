/**
 * Universal GPS Service (DC_GPS_CENTRALIZATION_001)
 * Single source of truth for GPS and battery tracking across all systems
 * Used by: Attendance, Journey, Drift Detection, Location Trackers
 * 
 * Lifecycle:
 * - start() called on successful clock-in
 * - stop() called on successful clock-out
 * - subscribe() for systems to listen for updates
 * 
 * WVV Protocol Integration (Dec 1, 2025):
 * - GPS accuracy validation (≤100m for reimbursable journeys)
 * - Journey track point collection support
 * - Speed anomaly detection
 * - Route validation helpers
 */

class GpsService {
    constructor() {
        // Core state
        this.watcherId = null;
        this.currentLocation = null;
        this.batteryPercentage = null;
        this.isTracking = false;
        this.lastUpdateTime = null;
        
        // Pub/sub system
        this.subscribers = [];
        
        // Battery monitoring
        this.batteryManager = null;
        
        // DC compliance logging
        this.dcLogs = [];
        
        // WVV Protocol: Journey tracking state
        this.journeyTrackPoints = [];
        this.journeyStartTime = null;
        this.isJourneyActive = false;
        
        // WVV Protocol: Validation thresholds
        this.WVV_MAX_ACCURACY_METERS = 100;  // Strict limit for journey reimbursement
        this.HEARTBEAT_MAX_ACCURACY_METERS = 500;  // Relaxed limit for location tracking (DC_GPS_DUAL_TIER_001)
        this.WVV_MAX_SPEED_BIKE = 80;
        this.WVV_MAX_SPEED_CAR = 180;
        
        // DC_BATTERY_001: Backend heartbeat for location tracker (Dec 04, 2025)
        this.backendHeartbeatInterval = null;
        this.HEARTBEAT_INTERVAL_MS = 30000; // 30 seconds
        
        // DC_VISIBILITY_001: Page visibility tracking (Jan 13, 2026)
        this.isPageVisible = true;
        this.visibilityWarningShown = false;
        this.tabHiddenSince = null;
        
        // DC_RESUME_001: Tracking state persistence (Jan 13, 2026)
        this.TRACKING_STATE_KEY = 'gps_tracking_state';
        
        // Initialize page visibility and close handlers
        this.initPageVisibilityHandler();
        this.initBeforeUnloadHandler();
    }
    
    /**
     * START: Called on successful clock-in
     * DC_LIFECYCLE_MANAGEMENT_001: Single start point
     */
    async start(source = 'attendance') {
        if (this.isTracking) {
            console.log(`[DC_GPS_001] GPS already tracking (requested by ${source})`);
            return;
        }
        
        console.log(`[DC_GPS_001] Starting GPS service from: ${source}`);
        this.isTracking = true;
        
        if (!navigator.geolocation) {
            this.notifySubscribers('gps:error', { message: 'Geolocation not supported' });
            return;
        }
        
        this.startWatching();
        await this.initBatteryTracking();
        this.startBackendHeartbeat();
        this.notifySubscribers('gps:started', { source });
    }
    
    /**
     * STOP: Called on successful clock-out
     * DC_LIFECYCLE_MANAGEMENT_001: Single stop point
     */
    stop(source = 'attendance') {
        console.log(`[DC_GPS_001] Stopping GPS service from: ${source}`);
        
        if (this.watcherId !== null) {
            navigator.geolocation.clearWatch(this.watcherId);
            this.watcherId = null;
        }
        
        if (this.batteryManager) {
            this.batteryManager.onlevelchange = null;
            this.batteryManager.onchargingtimechange = null;
            this.batteryManager = null;
        }
        
        this.stopBackendHeartbeat();
        
        this.isTracking = false;
        this.notifySubscribers('gps:stopped', { source });
    }
    
    /**
     * DC_BATTERY_001: Start backend location heartbeat (Dec 04, 2025)
     * Sends GPS + battery to /location/update every 30 seconds
     */
    startBackendHeartbeat() {
        if (this.backendHeartbeatInterval) {
            console.log('[DC_BATTERY_001] Backend heartbeat already running');
            return;
        }
        
        console.log('[DC_BATTERY_001] Starting backend location heartbeat (30s interval)');
        
        this.sendBackendHeartbeat();
        
        this.backendHeartbeatInterval = setInterval(() => {
            this.sendBackendHeartbeat();
        }, this.HEARTBEAT_INTERVAL_MS);
    }
    
    /**
     * DC_BATTERY_001: Stop backend location heartbeat
     */
    stopBackendHeartbeat() {
        if (this.backendHeartbeatInterval) {
            clearInterval(this.backendHeartbeatInterval);
            this.backendHeartbeatInterval = null;
            console.log('[DC_BATTERY_001] Backend heartbeat stopped');
        }
    }
    
    /**
     * DC_BATTERY_001: Send location update to backend
     * Includes battery_percentage for location tracker display
     */
    async sendBackendHeartbeat() {
        if (!this.currentLocation) {
            console.log('[DC_BATTERY_001] No GPS location yet, skipping backend heartbeat');
            return;
        }
        
        const token = localStorage.getItem('staff_token');
        if (!token) {
            console.log('[DC_BATTERY_001] No staff token, skipping backend heartbeat');
            return;
        }
        
        const loc = this.currentLocation;
        
        // DC_GPS_DUAL_TIER_001: Use relaxed 500m limit for heartbeats (location tracking)
        // WVV 100m limit is only for journey reimbursement validation
        // Note: accuracy_m of 0 is valid (means very high precision from GPS)
        if (loc.accuracy_m === null || loc.accuracy_m === undefined || loc.accuracy_m > this.HEARTBEAT_MAX_ACCURACY_METERS) {
            console.log(`[DC_BATTERY_001] GPS accuracy ${loc.accuracy_m}m exceeds tracking limit (${this.HEARTBEAT_MAX_ACCURACY_METERS}m), skipping`);
            return;
        }
        
        // Log if accuracy is degraded (indoor/weak signal)
        const isLowAccuracy = loc.accuracy_m > this.WVV_MAX_ACCURACY_METERS;
        if (isLowAccuracy) {
            console.log(`[DC_GPS_DUAL_TIER] Sending degraded GPS: accuracy=${loc.accuracy_m.toFixed(0)}m (indoor/weak signal)`);
        }
        
        // DC_GPS_BODY_FIX_001: Send as JSON body instead of query params
        const bodyData = {
            latitude: loc.latitude,
            longitude: loc.longitude,
            accuracy_m: loc.accuracy_m,
            source: 'heartbeat'
        };
        
        if (loc.altitude !== null && loc.altitude !== undefined) {
            bodyData.altitude = loc.altitude;
        }
        if (loc.speed_kmh !== null && loc.speed_kmh !== undefined) {
            bodyData.speed_kmh = loc.speed_kmh;
        }
        if (loc.heading !== null && loc.heading !== undefined) {
            bodyData.heading = loc.heading;
        }
        if (this.batteryPercentage !== null && this.batteryPercentage !== undefined) {
            bodyData.battery_percentage = this.batteryPercentage;
        }
        
        try {
            const API_BASE = window.API_BASE || '/api/v1';
            const url = `${API_BASE}/staff/attendance/location/update`;
            
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(bodyData)
            });
            
            if (response.ok) {
                const data = await response.json();
                console.log(`[DC_BATTERY_001] Backend heartbeat sent - DC: ${data.dc_code}, Battery: ${this.batteryPercentage}%`);
            } else if (response.status === 401) {
                // DC_GPS_AUTH_001: Token expired — stop heartbeat immediately to avoid 401 flood
                // Emit session-expired event so UI can prompt re-login
                console.warn('[DC_GPS_AUTH_001] Heartbeat 401 — token expired. Stopping heartbeat until re-auth.');
                this.stopBackendHeartbeat();
                // Notify subscribers so the page can show a re-login prompt
                this.notifySubscribers('gps:auth_expired', { status: 401 });
                // Also dispatch a DOM event for any listener that handles session expiry globally
                try {
                    window.dispatchEvent(new CustomEvent('staff:session_expired', { detail: { source: 'gps_heartbeat' } }));
                } catch (e) {}
            } else {
                const errorText = await response.text();
                console.warn(`[DC_BATTERY_001] Backend heartbeat failed (${response.status}):`, errorText);
            }
        } catch (error) {
            console.error('[DC_BATTERY_001] Backend heartbeat error:', error.message);
        }
    }
    
    /**
     * Internal: Start GPS watcher
     * DC_DATA_CAPTURE_001: Single watcher instance
     */
    startWatching() {
        this.watcherId = navigator.geolocation.watchPosition(
            (position) => {
                // DC_LOCATION_UPDATE_001: Capture all GPS data
                this.currentLocation = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy_m: position.coords.accuracy,
                    altitude: position.coords.altitude,
                    speed_kmh: position.coords.speed ? position.coords.speed * 3.6 : null,
                    heading: position.coords.heading
                };
                
                this.lastUpdateTime = new Date();
                
                // Notify all subscribers immediately
                this.notifySubscribers('gps:updated', {
                    location: this.currentLocation,
                    battery: this.batteryPercentage,
                    timestamp: this.lastUpdateTime
                });
            },
            (error) => {
                console.error('[DC_GPS_ERROR] GPS error:', error);
                this.notifySubscribers('gps:error', { error: error.message });
            },
            {
                enableHighAccuracy: true,
                timeout: 30000,
                maximumAge: 0
            }
        );
    }
    
    /**
     * Battery tracking
     * DC_BATTERY_INTEGRATION_001: Continuous battery monitoring
     */
    async initBatteryTracking() {
        if (!navigator.getBattery) {
            console.log('[DC_BATTERY_001] Battery API not available');
            return;
        }
        
        try {
            this.batteryManager = await navigator.getBattery();
            
            // Initial battery level
            this.batteryPercentage = Math.round(this.batteryManager.level * 100);
            this.notifySubscribers('battery:updated', this.batteryPercentage);
            
            // Listen for changes
            this.batteryManager.onlevelchange = () => {
                this.batteryPercentage = Math.round(this.batteryManager.level * 100);
                console.log(`[DC_BATTERY_001] Battery: ${this.batteryPercentage}%`);
                this.notifySubscribers('battery:updated', this.batteryPercentage);
            };
            
            this.batteryManager.onchargingtimechange = () => {
                this.notifySubscribers('battery:charging_changed', {
                    isCharging: this.batteryManager.charging,
                    chargingTime: this.batteryManager.chargingTime
                });
            };
        } catch (error) {
            console.log('[DC_BATTERY_001] Battery tracking unavailable:', error.message);
        }
    }
    
    /**
     * GET: Complete location with battery info
     * DC_DATA_STRUCTURE_001: Standard response format
     */
    getLocation() {
        if (!this.currentLocation) return null;
        
        return {
            ...this.currentLocation,
            battery_percentage: this.batteryPercentage,
            is_tracking: this.isTracking,
            last_update: this.lastUpdateTime,
            timestamp: new Date().toISOString()
        };
    }
    
    /**
     * GET: Only GPS coordinates
     * Useful for distance calculations
     */
    getCoordinates() {
        if (!this.currentLocation) return null;
        
        return {
            lat: this.currentLocation.latitude,
            lng: this.currentLocation.longitude,
            accuracy: this.currentLocation.accuracy_m,
            altitude: this.currentLocation.altitude,
            speed_kmh: this.currentLocation.speed_kmh,
            heading: this.currentLocation.heading
        };
    }
    
    /**
     * GET: Only battery percentage
     */
    getBattery() {
        return this.batteryPercentage;
    }
    
    /**
     * GET: Tracking status
     */
    isActive() {
        return this.isTracking;
    }
    
    /**
     * GET: Last update time
     */
    getLastUpdateTime() {
        return this.lastUpdateTime;
    }
    
    /**
     * SUBSCRIBE: Register for GPS/battery updates
     * DC_EVENT_SYSTEM_001: Pub/sub pattern
     * 
     * Events:
     * - gps:started - tracking initiated
     * - gps:updated - new GPS data available
     * - gps:stopped - tracking ended
     * - gps:error - GPS error occurred
     * - battery:updated - battery level changed
     * - battery:charging_changed - charging state changed
     */
    subscribe(handler) {
        if (typeof handler !== 'function') {
            console.error('[DC_GPS_001] Subscribe handler must be a function');
            return () => {};
        }
        
        this.subscribers.push(handler);
        console.log(`[DC_GPS_001] Subscriber added (total: ${this.subscribers.length})`);
        
        // Return unsubscribe function
        return () => {
            this.subscribers = this.subscribers.filter(h => h !== handler);
            console.log(`[DC_GPS_001] Subscriber removed (total: ${this.subscribers.length})`);
        };
    }
    
    /**
     * Internal: Notify all subscribers
     * DC_EVENT_SYSTEM_001: Broadcast pattern
     */
    notifySubscribers(event, data) {
        console.log(`[DC_GPS_EVENT] ${event}:`, data);
        
        this.subscribers.forEach((handler, index) => {
            try {
                handler({
                    event,
                    data,
                    timestamp: new Date(),
                    source: 'GpsService'
                });
            } catch (error) {
                console.error(`[DC_GPS_001] Error in subscriber ${index}:`, error);
            }
        });
    }
    
    /**
     * DEBUG: Get current state
     */
    getState() {
        return {
            isTracking: this.isTracking,
            location: this.currentLocation,
            battery: this.batteryPercentage,
            lastUpdate: this.lastUpdateTime,
            subscriberCount: this.subscribers.length,
            isJourneyActive: this.isJourneyActive,
            journeyPointCount: this.journeyTrackPoints.length
        };
    }
    
    /**
     * WVV PROTOCOL: Start journey tracking mode
     * DC_JOURNEY_GPS_001: Dedicated journey tracking
     */
    startJourneyTracking() {
        console.log('[WVV_JOURNEY_GPS] Starting journey GPS tracking mode');
        this.isJourneyActive = true;
        this.journeyStartTime = new Date();
        this.journeyTrackPoints = [];
        
        if (this.currentLocation) {
            this.addJourneyTrackPoint(this.currentLocation);
        }
        
        this.notifySubscribers('journey:started', {
            startTime: this.journeyStartTime,
            location: this.currentLocation
        });
    }
    
    /**
     * WVV PROTOCOL: Stop journey tracking mode
     * DC_JOURNEY_GPS_001: Complete journey GPS capture
     */
    stopJourneyTracking() {
        console.log('[WVV_JOURNEY_GPS] Stopping journey GPS tracking mode');
        
        const journeyData = {
            startTime: this.journeyStartTime,
            endTime: new Date(),
            trackPoints: [...this.journeyTrackPoints],
            totalPoints: this.journeyTrackPoints.length
        };
        
        this.isJourneyActive = false;
        this.journeyStartTime = null;
        this.journeyTrackPoints = [];
        
        this.notifySubscribers('journey:stopped', journeyData);
        
        return journeyData;
    }
    
    /**
     * WVV PROTOCOL: Add track point during journey
     * DC_JOURNEY_GPS_002: Continuous GPS capture
     */
    addJourneyTrackPoint(location) {
        if (!this.isJourneyActive) return;
        
        const trackPoint = {
            latitude: location.latitude,
            longitude: location.longitude,
            accuracy_m: location.accuracy_m,
            altitude: location.altitude,
            speed_kmh: location.speed_kmh,
            heading: location.heading,
            timestamp: new Date().toISOString(),
            battery: this.batteryPercentage
        };
        
        this.journeyTrackPoints.push(trackPoint);
        console.log(`[WVV_JOURNEY_GPS] Track point added: ${this.journeyTrackPoints.length} total`);
        
        return trackPoint;
    }
    
    /**
     * WVV PROTOCOL: Validate GPS accuracy
     * DC_WVV_VALIDATION_001: Accuracy threshold check
     */
    validateWvvAccuracy(location = null) {
        const loc = location || this.currentLocation;
        if (!loc) {
            return { isValid: false, reason: 'No GPS location available' };
        }
        
        if (!loc.accuracy_m) {
            return { isValid: false, reason: 'GPS accuracy data not available' };
        }
        
        if (loc.accuracy_m > this.WVV_MAX_ACCURACY_METERS) {
            return {
                isValid: false,
                reason: `GPS accuracy ${loc.accuracy_m.toFixed(0)}m exceeds WVV limit of ${this.WVV_MAX_ACCURACY_METERS}m`
            };
        }
        
        return { isValid: true, accuracy_m: loc.accuracy_m };
    }
    
    /**
     * WVV PROTOCOL: Validate speed for transport mode
     * DC_WVV_VALIDATION_002: Speed anomaly detection
     */
    validateWvvSpeed(speed_kmh, transportMode = 'bike') {
        const maxSpeeds = {
            bike: this.WVV_MAX_SPEED_BIKE,
            electric_bike: 45,
            car: this.WVV_MAX_SPEED_CAR,
            cart: 40,
            local_transport: 100,
            others: 60
        };
        
        const maxSpeed = maxSpeeds[transportMode] || 60;
        
        if (speed_kmh > maxSpeed) {
            return {
                isValid: false,
                reason: `Speed ${speed_kmh.toFixed(0)} km/h exceeds max ${maxSpeed} km/h for ${transportMode}`,
                anomaly: true
            };
        }
        
        return { isValid: true, speed_kmh, maxAllowed: maxSpeed };
    }
    
    /**
     * WVV PROTOCOL: Get journey track points for validation
     * DC_JOURNEY_GPS_003: Track point export
     */
    getJourneyTrackPoints() {
        return [...this.journeyTrackPoints];
    }
    
    /**
     * WVV PROTOCOL: Calculate journey distance from track points
     * DC_JOURNEY_GPS_004: Distance calculation
     */
    calculateJourneyDistance() {
        if (this.journeyTrackPoints.length < 2) return 0;
        
        let totalDistance = 0;
        for (let i = 1; i < this.journeyTrackPoints.length; i++) {
            const prev = this.journeyTrackPoints[i - 1];
            const curr = this.journeyTrackPoints[i];
            totalDistance += this.haversineDistance(
                prev.latitude, prev.longitude,
                curr.latitude, curr.longitude
            );
        }
        
        return Math.round(totalDistance * 100) / 100; // km with 2 decimals
    }
    
    /**
     * Calculate distance between two GPS coordinates
     * DC_GPS_MATH_001: Haversine formula
     */
    haversineDistance(lat1, lon1, lat2, lon2) {
        const R = 6371; // Earth's radius in km
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                  Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                  Math.sin(dLon / 2) * Math.sin(dLon / 2);
        return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    }
    
    /**
     * DC_VISIBILITY_001: Page visibility detection (Jan 13, 2026)
     * Warns staff when they minimize/switch tabs while GPS is active
     */
    initPageVisibilityHandler() {
        document.addEventListener('visibilitychange', () => {
            if (!this.isTracking) return;
            
            if (document.hidden) {
                this.isPageVisible = false;
                this.tabHiddenSince = new Date();
                console.log('[DC_VISIBILITY_001] Tab hidden - GPS tracking may be affected');
                
                this.notifySubscribers('visibility:hidden', {
                    hiddenAt: this.tabHiddenSince
                });
                
                if (!this.visibilityWarningShown) {
                    this.showVisibilityWarning();
                }
                
                this.reportTrackingGap('tab_hidden');
            } else {
                const wasHiddenFor = this.tabHiddenSince ? 
                    Math.round((new Date() - this.tabHiddenSince) / 1000) : 0;
                
                console.log(`[DC_VISIBILITY_001] Tab visible again (hidden for ${wasHiddenFor}s)`);
                
                this.isPageVisible = true;
                this.visibilityWarningShown = false;
                this.tabHiddenSince = null;
                
                this.notifySubscribers('visibility:visible', {
                    hiddenDurationSeconds: wasHiddenFor
                });
                
                if (wasHiddenFor > 60) {
                    this.reportTrackingGap('tab_restored', wasHiddenFor);
                }
            }
        });
    }
    
    /**
     * DC_VISIBILITY_002: Beforeunload warning (Jan 13, 2026)
     * Warns staff when they try to close browser while GPS is active
     */
    initBeforeUnloadHandler() {
        window.addEventListener('beforeunload', (event) => {
            if (this.isTracking) {
                this.saveTrackingState();
                this.reportTrackingGap('browser_closing');
                
                const message = 'GPS tracking is active. Closing this page will stop location tracking. Are you sure?';
                event.preventDefault();
                event.returnValue = message;
                return message;
            }
        });
        
        window.addEventListener('pagehide', () => {
            if (this.isTracking) {
                this.saveTrackingState();
                this.reportTrackingGap('page_unload');
            }
        });
    }
    
    /**
     * DC_VISIBILITY_003: Show visibility warning notification
     */
    showVisibilityWarning() {
        this.visibilityWarningShown = true;
        
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('GPS Tracking Warning', {
                body: 'Please keep this tab open for accurate location tracking.',
                icon: '/images/logo.png',
                tag: 'gps-visibility-warning',
                requireInteraction: true
            });
        }
        
        if (document.getElementById('gps-visibility-toast')) return;
        
        const toast = document.createElement('div');
        toast.id = 'gps-visibility-toast';
        toast.className = 'position-fixed top-0 start-50 translate-middle-x mt-3 p-3 bg-warning text-dark rounded shadow-lg';
        toast.style.cssText = 'z-index: 9999; max-width: 90%; animation: fadeIn 0.3s;';
        toast.innerHTML = `
            <div class="d-flex align-items-center gap-2">
                <i class="fas fa-exclamation-triangle fa-lg"></i>
                <div>
                    <strong>GPS Tracking Warning</strong><br>
                    <small>Keep this tab open for accurate location tracking</small>
                </div>
                <button type="button" class="btn-close ms-2" onclick="this.parentElement.parentElement.remove()"></button>
            </div>
        `;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            if (toast.parentElement) toast.remove();
        }, 10000);
    }
    
    /**
     * DC_VISIBILITY_004: Report tracking gap to backend (Jan 13, 2026)
     * Records when tracking was interrupted for gap detection
     * DC: Include token in body since sendBeacon can't use Auth headers
     */
    async reportTrackingGap(reason, durationSeconds = null) {
        const token = localStorage.getItem('staff_token');
        if (!token) return;
        
        try {
            const API_BASE = window.API_BASE || '/api/v1';
            const body = {
                reason: reason,
                timestamp: new Date().toISOString(),
                token: token,
                last_known_location: this.currentLocation ? {
                    latitude: this.currentLocation.latitude,
                    longitude: this.currentLocation.longitude,
                    accuracy_m: this.currentLocation.accuracy_m
                } : null
            };
            
            if (durationSeconds !== null) {
                body.gap_duration_seconds = durationSeconds;
            }
            
            navigator.sendBeacon(
                `${API_BASE}/staff/attendance/tracking-gap`,
                new Blob([JSON.stringify(body)], { type: 'application/json' })
            );
            
            console.log(`[DC_VISIBILITY_004] Tracking gap reported: ${reason}`);
        } catch (error) {
            console.error('[DC_VISIBILITY_004] Failed to report tracking gap:', error);
        }
    }
    
    /**
     * DC_VISIBILITY_005: Request notification permission
     */
    async requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            const permission = await Notification.requestPermission();
            console.log(`[DC_VISIBILITY_005] Notification permission: ${permission}`);
            return permission === 'granted';
        }
        return Notification.permission === 'granted';
    }
    
    /**
     * DC_RESUME_001: Save tracking state before page closes (Jan 13, 2026)
     * Persists minimal tracking flag for resume prompt on page load
     * DC Security: No location data stored - backend is source of truth
     */
    saveTrackingState() {
        if (!this.isTracking) {
            localStorage.removeItem(this.TRACKING_STATE_KEY);
            return;
        }
        
        // DC Security: Only store flags, not location data
        const state = {
            isTracking: true,
            isJourneyActive: this.isJourneyActive,
            savedAt: new Date().toISOString()
        };
        
        localStorage.setItem(this.TRACKING_STATE_KEY, JSON.stringify(state));
        console.log('[DC_RESUME_001] Tracking flag saved');
    }
    
    /**
     * DC_RESUME_002: Check for interrupted tracking session (Jan 13, 2026)
     * Returns saved state if tracking was interrupted
     */
    checkForInterruptedSession() {
        try {
            const savedState = localStorage.getItem(this.TRACKING_STATE_KEY);
            if (!savedState) return null;
            
            const state = JSON.parse(savedState);
            const savedAt = new Date(state.savedAt);
            const now = new Date();
            const hoursSinceSave = (now - savedAt) / (1000 * 60 * 60);
            
            // Only consider sessions from last 12 hours
            if (hoursSinceSave > 12) {
                console.log('[DC_RESUME_002] Saved session too old, clearing');
                localStorage.removeItem(this.TRACKING_STATE_KEY);
                return null;
            }
            
            console.log('[DC_RESUME_002] Found interrupted session:', state);
            return state;
        } catch (error) {
            console.error('[DC_RESUME_002] Error checking interrupted session:', error);
            return null;
        }
    }
    
    /**
     * DC_RESUME_003: Clear saved tracking state (Jan 13, 2026)
     */
    clearTrackingState() {
        localStorage.removeItem(this.TRACKING_STATE_KEY);
        console.log('[DC_RESUME_003] Tracking state cleared');
    }
    
    /**
     * DC_RESUME_004: Show resume tracking prompt (Jan 13, 2026)
     * Displays modal asking staff to resume or end their session
     * DC: Modal stays open during async operations and handles errors
     */
    showResumePrompt(sessionData, onResume, onEnd) {
        if (document.getElementById('gps-resume-modal')) return;
        
        const hasJourney = sessionData.active_journey;
        const gapDuration = sessionData.gap_duration_minutes || 0;
        const gapText = gapDuration < 60 ? 
            `${Math.round(gapDuration)} minutes` : 
            `${Math.round(gapDuration / 60)} hours`;
        
        const modal = document.createElement('div');
        modal.id = 'gps-resume-modal';
        modal.className = 'position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center';
        modal.style.cssText = 'z-index: 10000; background: rgba(0,0,0,0.7);';
        
        modal.innerHTML = `
            <div class="bg-dark text-white rounded-3 p-4 mx-3" style="max-width: 400px; border: 2px solid #ffc107;">
                <div class="text-center mb-3">
                    <i class="fas fa-location-crosshairs fa-3x text-warning mb-2"></i>
                    <h5 class="mb-1">Resume GPS Tracking?</h5>
                </div>
                <div class="text-center mb-3">
                    <p class="mb-2">Tracking was paused for ~${gapText}.</p>
                    ${hasJourney ? `<p class="text-warning mb-2"><i class="fas fa-route"></i> Active journey: ${hasJourney.purpose || 'In Progress'}</p>` : ''}
                    <small class="text-muted">Resume to continue capturing your location</small>
                </div>
                <div id="resume-error-msg" class="alert alert-danger d-none mb-2"></div>
                <div class="d-grid gap-2">
                    <button id="resume-tracking-btn" class="btn btn-warning btn-lg">
                        <i class="fas fa-play"></i> Resume Tracking
                    </button>
                    <button id="end-tracking-btn" class="btn btn-outline-light">
                        <i class="fas fa-stop"></i> ${hasJourney ? 'End Journey Here' : 'Clock Out'}
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        const resumeBtn = document.getElementById('resume-tracking-btn');
        const endBtn = document.getElementById('end-tracking-btn');
        const errorMsg = document.getElementById('resume-error-msg');
        
        const setLoading = (loading, btn) => {
            btn.disabled = loading;
            resumeBtn.disabled = loading;
            endBtn.disabled = loading;
            if (loading) {
                btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Please wait...';
            }
        };
        
        const showError = (msg) => {
            errorMsg.textContent = msg;
            errorMsg.classList.remove('d-none');
        };
        
        resumeBtn.addEventListener('click', async () => {
            setLoading(true, resumeBtn);
            errorMsg.classList.add('d-none');
            
            try {
                if (onResume) await onResume(sessionData);
                modal.remove();
            } catch (error) {
                console.error('[DC_RESUME] Resume failed:', error);
                showError('Failed to resume. Please try again.');
                setLoading(false, resumeBtn);
                resumeBtn.innerHTML = '<i class="fas fa-play"></i> Resume Tracking';
            }
        });
        
        endBtn.addEventListener('click', async () => {
            setLoading(true, endBtn);
            errorMsg.classList.add('d-none');
            
            try {
                if (onEnd) await onEnd(sessionData);
                modal.remove();
            } catch (error) {
                console.error('[DC_RESUME] End session failed:', error);
                showError('Failed to end session. Please try again.');
                setLoading(false, endBtn);
                endBtn.innerHTML = `<i class="fas fa-stop"></i> ${hasJourney ? 'End Journey Here' : 'Clock Out'}`;
            }
        });
    }
    
    /**
     * DC_RESUME_005: Format time ago string
     */
    formatTimeAgo(date) {
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / (1000 * 60));
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        
        if (diffMins < 1) return 'just now';
        if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
        if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
        return `${Math.floor(diffHours / 24)} day${Math.floor(diffHours / 24) > 1 ? 's' : ''} ago`;
    }
    
    /**
     * DC_RESUME_006: Auto-check and prompt on page load (Jan 13, 2026)
     * Call this from attendance page to check for interrupted sessions
     * Backend is source of truth - local flag just triggers the check
     */
    async checkAndPromptResume(onResume, onEnd) {
        const savedState = this.checkForInterruptedSession();
        if (!savedState) return false;
        
        // Verify with backend if session is still active
        const token = localStorage.getItem('staff_token');
        if (!token) {
            this.clearTrackingState();
            return false;
        }
        
        try {
            const API_BASE = window.API_BASE || '/api/v1';
            const response = await fetch(`${API_BASE}/staff/attendance/check-active-session`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            if (response.ok) {
                const data = await response.json();
                
                if (data.has_active_session) {
                    // Use backend data for prompt (source of truth)
                    this.showResumePrompt(data, onResume, onEnd);
                    return true;
                } else {
                    // Session ended on backend, clear local state
                    this.clearTrackingState();
                    return false;
                }
            }
        } catch (error) {
            console.error('[DC_RESUME_006] Error checking active session:', error);
        }
        
        // If backend check fails, clear state and don't show stale prompt
        this.clearTrackingState();
        return false;
    }
}

// Global singleton instance
const gpsService = new GpsService();

console.log('[DC_GPS_001] Universal GPS Service initialized (WVV Protocol Enhanced)');
