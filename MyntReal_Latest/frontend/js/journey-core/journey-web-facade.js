/**
 * Journey Web Facade (DC_JOURNEY_UNIFIED_001)
 * 
 * Bridges the JourneyCore engine with the existing staff_my_journeys.html UI.
 * 
 * RULE 2 COMPLIANCE: UI becomes "dumb" - this facade handles:
 * - Engine lifecycle management
 * - Event subscription/forwarding
 * - Graceful error handling for rejections
 * 
 * RULE 4 COMPLIANCE: Zero visible behavior change
 * - Same button handlers exposed
 * - Same flows maintained
 * - Same warnings displayed
 */

(function(window) {
    'use strict';
    
    const JourneyCore = window.JourneyCore;
    const WebGPSAdapter = window.WebGPSAdapter;
    const WebStorageAdapter = window.WebStorageAdapter;
    const WebAPIAdapter = window.WebAPIAdapter;
    const WebPlatformAdapter = window.WebPlatformAdapter;
    
    let engineInstance = null;
    let uiCallbacks = {};
    let batteryManager = null;
    let batteryPercentage = null;
    
    async function initBattery() {
        if (!navigator.getBattery) return;
        try {
            batteryManager = await navigator.getBattery();
            batteryPercentage = Math.round(batteryManager.level * 100);
            batteryManager.onlevelchange = () => {
                batteryPercentage = Math.round(batteryManager.level * 100);
            };
        } catch (e) {
            console.warn('[JourneyWebFacade] Battery API unavailable');
        }
    }
    
    function getBatteryPercentage() {
        return batteryPercentage;
    }
    
    function createEngine(apiBaseUrl) {
        if (engineInstance) {
            engineInstance.destroy();
        }
        
        const gpsAdapter = new WebGPSAdapter();
        const storageAdapter = new WebStorageAdapter('journey_core_session');
        const apiAdapter = new WebAPIAdapter(apiBaseUrl || '/api/v1');
        
        engineInstance = new JourneyCore.JourneyEngine(
            gpsAdapter,
            storageAdapter,
            apiAdapter,
            {
                heartbeatIntervalMs: 15000,
                sessionSaveIntervalMs: 60000,
                minDistanceForHeartbeatM: 0,
                batteryProvider: getBatteryPercentage
            },
            WebPlatformAdapter
        );
        
        engineInstance.on(JourneyCore.JourneyEvent.STARTED, (data) => {
            console.log('[JourneyWebFacade] Journey started:', data);
            if (uiCallbacks.onStarted) uiCallbacks.onStarted(data);
        });
        
        engineInstance.on(JourneyCore.JourneyEvent.STOPPED, (data) => {
            console.log('[JourneyWebFacade] Journey stopped:', data);
            if (uiCallbacks.onStopped) uiCallbacks.onStopped(data);
        });
        
        engineInstance.on(JourneyCore.JourneyEvent.GPS_UPDATED, (data) => {
            if (uiCallbacks.onGPSUpdated) uiCallbacks.onGPSUpdated(data);
        });
        
        engineInstance.on(JourneyCore.JourneyEvent.HEARTBEAT_SENT, (data) => {
            if (uiCallbacks.onHeartbeatSent) uiCallbacks.onHeartbeatSent(data);
        });
        
        engineInstance.on(JourneyCore.JourneyEvent.HEARTBEAT_FAILED, (data) => {
            console.warn('[JourneyWebFacade] Heartbeat failed:', data);
            if (uiCallbacks.onHeartbeatFailed) uiCallbacks.onHeartbeatFailed(data);
        });
        
        engineInstance.on(JourneyCore.JourneyEvent.INVALIDATED, (data) => {
            console.warn('[JourneyWebFacade] Journey invalidated:', data);
            if (uiCallbacks.onInvalidated) uiCallbacks.onInvalidated(data);
        });
        
        engineInstance.on(JourneyCore.JourneyEvent.ERROR, (data) => {
            console.error('[JourneyWebFacade] Journey error:', data);
            if (uiCallbacks.onError) uiCallbacks.onError(data);
        });
        
        engineInstance.on(JourneyCore.JourneyEvent.SESSION_RESTORED, (data) => {
            console.log('[JourneyWebFacade] Session restored:', data);
            if (uiCallbacks.onSessionRestored) uiCallbacks.onSessionRestored(data);
        });
        
        return engineInstance;
    }
    
    async function initialize(apiBaseUrl, callbacks) {
        await initBattery();
        uiCallbacks = callbacks || {};
        const engine = createEngine(apiBaseUrl);
        await engine.initialize();
        return engine;
    }
    
    async function startJourney(input) {
        if (!engineInstance) {
            return { success: false, error: 'Engine not initialized' };
        }
        
        const result = await engineInstance.start({
            company_id: input.company_id,
            transport_mode: input.transport_mode,
            purpose: input.purpose,
            purpose_details: input.purpose_details
        });
        
        return result;
    }
    
    async function stopJourney() {
        if (!engineInstance) {
            return { success: false, error: 'Engine not initialized' };
        }
        
        return await engineInstance.stop();
    }
    
    async function pauseJourney() {
        if (!engineInstance) {
            return { success: false, error: 'Engine not initialized' };
        }
        
        return await engineInstance.pause();
    }
    
    async function resumeJourney() {
        if (!engineInstance) {
            return { success: false, error: 'Engine not initialized' };
        }
        
        return await engineInstance.resume();
    }
    
    async function attachToExistingJourney(journey) {
        if (!engineInstance) {
            return { success: false, error: 'Engine not initialized' };
        }
        
        if (engineInstance.attachToJourney) {
            return await engineInstance.attachToJourney(journey);
        }
        
        return { success: false, error: 'attachToJourney not supported by engine' };
    }
    
    function getState() {
        if (!engineInstance) return JourneyCore.JourneyState.IDLE;
        return engineInstance.getState();
    }
    
    function getJourney() {
        if (!engineInstance) return null;
        return engineInstance.getJourney();
    }
    
    function getTrackPoints() {
        if (!engineInstance) return [];
        return engineInstance.getTrackPoints();
    }
    
    function getTotalDistanceKm() {
        if (!engineInstance) return 0;
        return engineInstance.getTotalDistanceKm();
    }
    
    function destroy() {
        if (engineInstance) {
            engineInstance.destroy();
            engineInstance = null;
        }
        uiCallbacks = {};
    }
    
    function isActive() {
        return engineInstance && 
            (engineInstance.getState() === JourneyCore.JourneyState.ACTIVE ||
             engineInstance.getState() === JourneyCore.JourneyState.PAUSED);
    }
    
    window.JourneyWebFacade = {
        initialize,
        startJourney,
        stopJourney,
        pauseJourney,
        resumeJourney,
        attachToExistingJourney,
        getState,
        getJourney,
        getTrackPoints,
        getTotalDistanceKm,
        destroy,
        isActive,
        getBatteryPercentage,
        
        JourneyState: JourneyCore.JourneyState,
        TransportMode: JourneyCore.TransportMode,
        JourneyPurpose: JourneyCore.JourneyPurpose,
        JourneyEvent: JourneyCore.JourneyEvent
    };
    
})(window);
