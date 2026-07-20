/**
 * Web GPS Adapter - Thin translator only (DC_JOURNEY_UNIFIED_001)
 * 
 * RULE 1 COMPLIANCE:
 * - Only translates navigator.geolocation → core RawGPSPosition
 * - Does NOT compute distance
 * - Does NOT compute speed
 * - Does NOT decide validity
 * - Does NOT block journey transitions
 */

class WebGPSAdapter {
    constructor() {
        this.watcherId = null;
        this.callbacks = null;
    }
    
    async startWatching(callbacks) {
        if (!navigator.geolocation) {
            callbacks.onError({ code: 0, message: 'Geolocation not supported' });
            return false;
        }
        
        this.callbacks = callbacks;
        
        this.watcherId = navigator.geolocation.watchPosition(
            (position) => {
                const rawPosition = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy,
                    altitude: position.coords.altitude,
                    speed: position.coords.speed,
                    heading: position.coords.heading,
                    timestamp: position.timestamp
                };
                this.callbacks.onPositionUpdate(rawPosition);
            },
            (error) => {
                if (error.code === error.PERMISSION_DENIED) {
                    this.callbacks.onPermissionDenied();
                } else {
                    this.callbacks.onError({
                        code: error.code,
                        message: error.message
                    });
                }
            },
            {
                enableHighAccuracy: true,
                timeout: 30000,
                maximumAge: 0
            }
        );
        
        return true;
    }
    
    stopWatching() {
        if (this.watcherId !== null) {
            navigator.geolocation.clearWatch(this.watcherId);
            this.watcherId = null;
        }
    }
    
    async getCurrentPosition() {
        return new Promise((resolve) => {
            if (!navigator.geolocation) {
                resolve(null);
                return;
            }
            
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    resolve({
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                        accuracy: position.coords.accuracy,
                        altitude: position.coords.altitude,
                        speed: position.coords.speed,
                        heading: position.coords.heading,
                        timestamp: position.timestamp
                    });
                },
                () => {
                    resolve(null);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 30000,
                    maximumAge: 0
                }
            );
        });
    }
    
    isWatching() {
        return this.watcherId !== null;
    }
    
    async checkPermission() {
        if (!navigator.permissions) {
            return 'prompt';
        }
        
        try {
            const result = await navigator.permissions.query({ name: 'geolocation' });
            return result.state;
        } catch {
            return 'prompt';
        }
    }
    
    async requestPermission() {
        return new Promise((resolve) => {
            navigator.geolocation.getCurrentPosition(
                () => resolve(true),
                () => resolve(false),
                { enableHighAccuracy: true, timeout: 10000 }
            );
        });
    }
}

window.WebGPSAdapter = WebGPSAdapter;
