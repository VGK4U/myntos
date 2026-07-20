/**
 * Mobile GPS Adapter - Thin translator only (DC_JOURNEY_UNIFIED_001)
 * 
 * RULE 1 COMPLIANCE:
 * - Only translates Capacitor Geolocation → core RawGPSPosition
 * - Does NOT compute distance
 * - Does NOT compute speed
 * - Does NOT decide validity
 * - Does NOT block journey transitions
 */

import { Geolocation, Position, PositionOptions } from '@capacitor/geolocation';
import type { GPSAdapter, GPSAdapterCallbacks, RawGPSPosition } from './types';

export class MobileGPSAdapter implements GPSAdapter {
    private watcherId: string | null = null;
    private callbacks: GPSAdapterCallbacks | null = null;
    private _isWatching: boolean = false;

    async startWatching(callbacks: GPSAdapterCallbacks): Promise<boolean> {
        this.callbacks = callbacks;

        try {
            const permission = await this.checkPermission();
            if (permission !== 'granted') {
                const granted = await this.requestPermission();
                if (!granted) {
                    callbacks.onPermissionDenied();
                    return false;
                }
            }

            const options: PositionOptions = {
                enableHighAccuracy: true,
                timeout: 30000,
                maximumAge: 0
            };

            this.watcherId = await Geolocation.watchPosition(options, (position, err) => {
                if (err) {
                    this.callbacks?.onError({
                        code: err.code || 0,
                        message: err.message || 'Unknown GPS error'
                    });
                    return;
                }

                if (position) {
                    const rawPosition: RawGPSPosition = {
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                        accuracy: position.coords.accuracy ?? 999,
                        altitude: position.coords.altitude,
                        speed: position.coords.speed,
                        heading: position.coords.heading,
                        timestamp: position.timestamp
                    };
                    this.callbacks?.onPositionUpdate(rawPosition);
                }
            });

            this._isWatching = true;
            return true;
        } catch (error: any) {
            callbacks.onError({
                code: 0,
                message: error.message || 'Failed to start GPS watching'
            });
            return false;
        }
    }

    stopWatching(): void {
        if (this.watcherId !== null) {
            Geolocation.clearWatch({ id: this.watcherId });
            this.watcherId = null;
        }
        this._isWatching = false;
    }

    async getCurrentPosition(): Promise<RawGPSPosition | null> {
        try {
            const position: Position = await Geolocation.getCurrentPosition({
                enableHighAccuracy: true,
                timeout: 30000
            });

            return {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
                accuracy: position.coords.accuracy ?? 999,
                altitude: position.coords.altitude,
                speed: position.coords.speed,
                heading: position.coords.heading,
                timestamp: position.timestamp
            };
        } catch (error) {
            return null;
        }
    }

    isWatching(): boolean {
        return this._isWatching;
    }

    async checkPermission(): Promise<'granted' | 'denied' | 'prompt'> {
        try {
            const status = await Geolocation.checkPermissions();
            if (status.location === 'granted') return 'granted';
            if (status.location === 'denied') return 'denied';
            return 'prompt';
        } catch (error) {
            return 'prompt';
        }
    }

    async requestPermission(): Promise<boolean> {
        try {
            const status = await Geolocation.requestPermissions();
            return status.location === 'granted';
        } catch (error) {
            return false;
        }
    }
}
