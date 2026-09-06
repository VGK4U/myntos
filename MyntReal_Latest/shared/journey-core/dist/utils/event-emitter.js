import { noopLogger } from '../adapters/platform-adapter.js';
export function createEventEmitter(logger = noopLogger) {
    const listeners = new Map();
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
                    }
                    catch (error) {
                        logger.error(`Error in event listener for ${event}:`, error);
                    }
                });
            }
        },
        removeAllListeners(event) {
            if (event) {
                listeners.delete(event);
            }
            else {
                listeners.clear();
            }
        }
    };
}
//# sourceMappingURL=event-emitter.js.map