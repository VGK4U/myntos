/**
 * Web Storage Adapter - localStorage wrapper (DC_JOURNEY_UNIFIED_001)
 * 
 * RULE 1 COMPLIANCE:
 * - Only stores/retrieves JourneySession
 * - No business logic
 */

class WebStorageAdapter {
    constructor(storageKey = 'journey_session') {
        this.storageKey = storageKey;
    }
    
    async saveSession(session) {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(session));
        } catch (error) {
            console.warn('[WebStorageAdapter] Save failed:', error);
        }
    }
    
    async loadSession() {
        try {
            const data = localStorage.getItem(this.storageKey);
            if (!data) return null;
            return JSON.parse(data);
        } catch (error) {
            console.warn('[WebStorageAdapter] Load failed:', error);
            return null;
        }
    }
    
    async clearSession() {
        localStorage.removeItem(this.storageKey);
    }
    
    async hasSession() {
        return localStorage.getItem(this.storageKey) !== null;
    }
}

window.WebStorageAdapter = WebStorageAdapter;
