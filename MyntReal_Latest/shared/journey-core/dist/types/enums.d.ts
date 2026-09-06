export declare enum JourneyState {
    IDLE = "idle",
    ACTIVE = "active",
    PAUSED = "paused",
    COMPLETED = "completed",
    INVALIDATED = "invalidated"
}
export declare enum TransportMode {
    BIKE = "bike",
    CAR = "car",
    ELECTRIC_BIKE = "electric_bike",
    CART = "cart",
    LOCAL_TRANSPORT = "local_transport",
    OTHERS = "others"
}
export declare enum JourneyPurpose {
    CLIENT_VISIT = "client_visit",
    SITE_INSPECTION = "site_inspection",
    MEETING = "meeting",
    DELIVERY = "delivery",
    COLLECTION = "collection",
    OTHER = "other"
}
export declare enum GPSAccuracyLevel {
    HIGH = "high",
    MEDIUM = "medium",
    LOW = "low",
    WEAK_SIGNAL = "weak_signal"
}
export declare enum JourneyEvent {
    STARTED = "journey:started",
    STOPPED = "journey:stopped",
    PAUSED = "journey:paused",
    RESUMED = "journey:resumed",
    GPS_UPDATED = "gps:updated",
    HEARTBEAT_SENT = "heartbeat:sent",
    HEARTBEAT_FAILED = "heartbeat:failed",
    INVALIDATED = "journey:invalidated",
    ERROR = "journey:error",
    SESSION_RESTORED = "session:restored"
}
//# sourceMappingURL=enums.d.ts.map