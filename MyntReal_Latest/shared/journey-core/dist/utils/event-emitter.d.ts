import { JourneyEvent } from '../types/enums.js';
import { Logger } from '../adapters/platform-adapter.js';
export type EventCallback = (data: unknown) => void;
export interface EventEmitter {
    on(event: JourneyEvent, callback: EventCallback): void;
    off(event: JourneyEvent, callback: EventCallback): void;
    emit(event: JourneyEvent, data?: unknown): void;
    removeAllListeners(event?: JourneyEvent): void;
}
export declare function createEventEmitter(logger?: Logger): EventEmitter;
//# sourceMappingURL=event-emitter.d.ts.map