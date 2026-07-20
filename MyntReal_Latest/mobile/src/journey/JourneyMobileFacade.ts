/**
 * Journey Mobile Facade - Bridge between JourneyCore and Mobile UI (DC_JOURNEY_UNIFIED_001)
 * 
 * RULE 1 COMPLIANCE:
 * - Only wires adapters to JourneyEngine
 * - Exposes simple methods to UI
 * - No business logic
 * 
 * This mirrors the Web facade (journey-web-facade.js)
 * 
 * Note: Uses 'any' for journey-core types to avoid TypeScript path issues.
 * The actual journey-core is imported at runtime.
 */

import { MobileGPSAdapter } from './MobileGPSAdapter';
import { MobileStorageAdapter } from './MobileStorageAdapter';
import { MobileAPIAdapter } from './MobileAPIAdapter';
import { MobilePlatformAdapter } from './MobilePlatformAdapter';
import { JourneyEvent, JourneyState } from './types';

let JourneyEngine: any = null;
let JourneyCoreEvents: any = null;

async function loadJourneyCore(): Promise<boolean> {
    try {
        const engineModule = await import('../../../shared/journey-core/dist/engine/journey-engine.js');
        const enumsModule = await import('../../../shared/journey-core/dist/types/enums.js');
        JourneyEngine = engineModule.JourneyEngine;
        JourneyCoreEvents = enumsModule.JourneyEvent;
        return true;
    } catch (error) {
        console.error('[JourneyMobileFacade] Failed to load journey-core:', error);
        return false;
    }
}

export interface JourneyUICallbacks {
    onStarted?: (data: any) => void;
    onStopped?: (data: any) => void;
    onGPSUpdated?: (data: any) => void;
    onHeartbeatSent?: (data: any) => void;
    onHeartbeatFailed?: (data: any) => void;
    onError?: (data: any) => void;
    onInvalidated?: (data: any) => void;
}

export class JourneyMobileFacade {
    private engine: any = null;
    private gpsAdapter: MobileGPSAdapter | null = null;
    private storageAdapter: MobileStorageAdapter | null = null;
    private apiAdapter: MobileAPIAdapter | null = null;
    private platformAdapter: MobilePlatformAdapter | null = null;
    private uiCallbacks: JourneyUICallbacks = {};
    private initialized: boolean = false;

    async initialize(apiBaseUrl: string, callbacks: JourneyUICallbacks = {}): Promise<any> {
        if (this.initialized && this.engine) {
            return this.engine;
        }

        const coreLoaded = await loadJourneyCore();
        if (!coreLoaded || !JourneyEngine) {
            throw new Error('[FATAL] journey-core not available. Cannot initialize journey tracking.');
        }

        this.uiCallbacks = callbacks;

        this.gpsAdapter = new MobileGPSAdapter();
        this.storageAdapter = new MobileStorageAdapter('journey_core_session');
        this.apiAdapter = new MobileAPIAdapter(apiBaseUrl);
        this.platformAdapter = new MobilePlatformAdapter();

        await this.platformAdapter.initialize();

        this.engine = new JourneyEngine(
            this.gpsAdapter,
            this.storageAdapter,
            this.apiAdapter,
            {},
            this.platformAdapter
        );

        const events = JourneyCoreEvents || JourneyEvent;

        this.engine.on(events.STARTED, (data: any) => {
            console.log('[JourneyMobileFacade] Journey started:', data);
            this.uiCallbacks.onStarted?.(data);
        });

        this.engine.on(events.STOPPED, (data: any) => {
            console.log('[JourneyMobileFacade] Journey stopped:', data);
            this.uiCallbacks.onStopped?.(data);
        });

        this.engine.on(events.GPS_UPDATED, (data: any) => {
            this.uiCallbacks.onGPSUpdated?.(data);
        });

        this.engine.on(events.HEARTBEAT_SENT, (data: any) => {
            console.log('[JourneyMobileFacade] Heartbeat sent:', data);
            this.uiCallbacks.onHeartbeatSent?.(data);
        });

        this.engine.on(events.HEARTBEAT_FAILED, (data: any) => {
            console.warn('[JourneyMobileFacade] Heartbeat failed:', data);
            this.uiCallbacks.onHeartbeatFailed?.(data);
        });

        this.engine.on(events.INVALIDATED, (data: any) => {
            console.warn('[JourneyMobileFacade] Journey invalidated:', data);
            this.uiCallbacks.onInvalidated?.(data);
        });

        this.engine.on(events.ERROR, (data: any) => {
            console.error('[JourneyMobileFacade] Error:', data);
            this.uiCallbacks.onError?.(data);
        });

        this.platformAdapter.onAppStateChange((isActive: boolean) => {
            if (isActive) {
                console.log('[JourneyMobileFacade] App foregrounded - GPS tracking continues');
            } else {
                console.log('[JourneyMobileFacade] App backgrounded - GPS tracking in background mode');
            }
        });

        this.initialized = true;
        return this.engine;
    }

    setAuthToken(token: string): void {
        this.apiAdapter?.setAuthToken(token);
    }

    async startJourney(payload: {
        company_id: number;
        transport_mode: string;
        purpose: string;
        destination?: string;
    }): Promise<{ success: boolean; error?: string; journey?: any }> {
        if (!this.engine) {
            return { success: false, error: 'Journey engine not initialized' };
        }

        try {
            const result = await (this.engine as any).start(payload);
            if (result.success) {
                return { success: true, journey: this.engine.getJourney() };
            } else {
                return { success: false, error: result.error };
            }
        } catch (error: any) {
            return { success: false, error: error.message };
        }
    }

    async endJourney(notes?: string): Promise<{ success: boolean; error?: string; summary?: any }> {
        if (!this.engine) {
            return { success: false, error: 'Journey engine not initialized' };
        }

        try {
            const result = await (this.engine as any).end(notes);
            if (result.success) {
                return { success: true };
            } else {
                return { success: false, error: result.error };
            }
        } catch (error: any) {
            return { success: false, error: error.message };
        }
    }

    async attachToExistingJourney(existingJourney: any): Promise<{ success: boolean; error?: string }> {
        if (!this.engine) {
            return { success: false, error: 'Journey engine not initialized' };
        }

        try {
            if (typeof (this.engine as any).attachToJourney === 'function') {
                await (this.engine as any).attachToJourney(existingJourney);
            } else {
                return { success: false, error: 'attachToJourney not available in core' };
            }
            return { success: true };
        } catch (error: any) {
            return { success: false, error: error.message };
        }
    }

    getState(): JourneyState | null {
        return this.engine?.getState() ?? null;
    }

    getJourney(): any {
        return this.engine?.getJourney() ?? null;
    }

    getTotalDistanceKm(): number {
        return this.engine?.getTotalDistanceKm() ?? 0;
    }

    subscribe(event: JourneyEvent, callback: (data: any) => void): void {
        this.engine?.on(event, callback);
    }

    unsubscribe(event: JourneyEvent, callback: (data: any) => void): void {
        this.engine?.off(event, callback);
    }

    async destroy(): Promise<void> {
        if (this.engine) {
            this.engine.destroy();
            this.engine = null;
        }
        if (this.platformAdapter) {
            await this.platformAdapter.destroy();
            this.platformAdapter = null;
        }
        this.gpsAdapter = null;
        this.storageAdapter = null;
        this.apiAdapter = null;
        this.initialized = false;
    }
}

export const journeyMobileFacade = new JourneyMobileFacade();
