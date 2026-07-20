/**
 * Mobile Storage Adapter - Capacitor Preferences wrapper (DC_JOURNEY_UNIFIED_001)
 * 
 * RULE 1 COMPLIANCE:
 * - Only stores/retrieves JourneySession
 * - No business logic
 */

import { Preferences } from '@capacitor/preferences';
import type { StorageAdapter, JourneySession } from './types';

export class MobileStorageAdapter implements StorageAdapter {
    private storageKey: string;

    constructor(storageKey: string = 'journey_session') {
        this.storageKey = storageKey;
    }

    async saveSession(session: JourneySession): Promise<void> {
        try {
            await Preferences.set({
                key: this.storageKey,
                value: JSON.stringify(session)
            });
        } catch (error) {
            console.warn('[MobileStorageAdapter] Save failed:', error);
        }
    }

    async loadSession(): Promise<JourneySession | null> {
        try {
            const { value } = await Preferences.get({ key: this.storageKey });
            if (!value) return null;
            return JSON.parse(value);
        } catch (error) {
            console.warn('[MobileStorageAdapter] Load failed:', error);
            return null;
        }
    }

    async clearSession(): Promise<void> {
        await Preferences.remove({ key: this.storageKey });
    }

    async hasSession(): Promise<boolean> {
        const { value } = await Preferences.get({ key: this.storageKey });
        return value !== null;
    }
}
