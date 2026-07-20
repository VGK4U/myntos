import { JourneyEvent } from '../types/enums.js';
import { Logger, noopLogger } from '../adapters/platform-adapter.js';

export type EventCallback = (data: unknown) => void;

export interface EventEmitter {
  on(event: JourneyEvent, callback: EventCallback): void;
  off(event: JourneyEvent, callback: EventCallback): void;
  emit(event: JourneyEvent, data?: unknown): void;
  removeAllListeners(event?: JourneyEvent): void;
}

export function createEventEmitter(logger: Logger = noopLogger): EventEmitter {
  const listeners: Map<JourneyEvent, Set<EventCallback>> = new Map();
  
  return {
    on(event: JourneyEvent, callback: EventCallback): void {
      if (!listeners.has(event)) {
        listeners.set(event, new Set());
      }
      listeners.get(event)!.add(callback);
    },
    
    off(event: JourneyEvent, callback: EventCallback): void {
      const eventListeners = listeners.get(event);
      if (eventListeners) {
        eventListeners.delete(callback);
      }
    },
    
    emit(event: JourneyEvent, data?: unknown): void {
      const eventListeners = listeners.get(event);
      if (eventListeners) {
        eventListeners.forEach(callback => {
          try {
            callback(data);
          } catch (error) {
            logger.error(`Error in event listener for ${event}:`, error);
          }
        });
      }
    },
    
    removeAllListeners(event?: JourneyEvent): void {
      if (event) {
        listeners.delete(event);
      } else {
        listeners.clear();
      }
    }
  };
}
