/**
 * Mobile Platform Adapter - Timers, Logging, AppState (DC_JOURNEY_UNIFIED_001)
 * 
 * RULE 1 COMPLIANCE:
 * - Only provides platform abstractions
 * - No business decisions
 * - Timers, logging, and app state signals only
 */

import { App, AppState } from '@capacitor/app';
import type { PlatformAdapter, Logger, TimerProvider, TimerHandle } from './types';

export class MobileLogger implements Logger {
    private prefix: string;

    constructor(prefix: string = '[JourneyCore]') {
        this.prefix = prefix;
    }

    log(...args: any[]): void {
        console.log(this.prefix, ...args);
    }

    warn(...args: any[]): void {
        console.warn(this.prefix, ...args);
    }

    error(...args: any[]): void {
        console.error(this.prefix, ...args);
    }
}

export class MobileTimerProvider implements TimerProvider {
    setInterval(callback: () => void, intervalMs: number): TimerHandle {
        const id = setInterval(callback, intervalMs);
        return id as unknown as TimerHandle;
    }

    clearInterval(handle: TimerHandle): void {
        clearInterval(handle as unknown as number);
    }
}

export interface AppStateCallback {
    (isActive: boolean): void;
}

export class MobilePlatformAdapter implements PlatformAdapter {
    public logger: Logger;
    public timer: TimerProvider;
    private appStateListeners: AppStateCallback[] = [];
    private appStateListenerHandle: any = null;

    constructor() {
        this.logger = new MobileLogger();
        this.timer = new MobileTimerProvider();
    }

    async initialize(): Promise<void> {
        this.appStateListenerHandle = await App.addListener('appStateChange', (state: AppState) => {
            const isActive = state.isActive;
            this.logger.log('App state changed:', isActive ? 'foreground' : 'background');
            this.appStateListeners.forEach(cb => cb(isActive));
        });
    }

    onAppStateChange(callback: AppStateCallback): void {
        this.appStateListeners.push(callback);
    }

    removeAppStateListener(callback: AppStateCallback): void {
        const index = this.appStateListeners.indexOf(callback);
        if (index > -1) {
            this.appStateListeners.splice(index, 1);
        }
    }

    async destroy(): Promise<void> {
        if (this.appStateListenerHandle) {
            await this.appStateListenerHandle.remove();
            this.appStateListenerHandle = null;
        }
        this.appStateListeners = [];
    }
}
