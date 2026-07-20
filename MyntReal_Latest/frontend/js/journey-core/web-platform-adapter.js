/**
 * Web Platform Adapter - Console and Timer (DC_JOURNEY_UNIFIED_001)
 * 
 * Provides platform-specific implementations for:
 * - Logger (console)
 * - TimerProvider (setInterval/clearInterval)
 */

const WebLogger = {
    log(message, ...args) {
        console.log(`[JourneyCore] ${message}`, ...args);
    },
    warn(message, ...args) {
        console.warn(`[JourneyCore] ${message}`, ...args);
    },
    error(message, ...args) {
        console.error(`[JourneyCore] ${message}`, ...args);
    }
};

const WebTimer = {
    setInterval(callback, ms) {
        return window.setInterval(callback, ms);
    },
    clearInterval(handle) {
        window.clearInterval(handle);
    }
};

const WebPlatformAdapter = {
    logger: WebLogger,
    timer: WebTimer
};

window.WebPlatformAdapter = WebPlatformAdapter;
window.WebLogger = WebLogger;
window.WebTimer = WebTimer;
