export var JourneyState;
(function (JourneyState) {
    JourneyState["IDLE"] = "idle";
    JourneyState["ACTIVE"] = "active";
    JourneyState["PAUSED"] = "paused";
    JourneyState["COMPLETED"] = "completed";
    JourneyState["INVALIDATED"] = "invalidated";
})(JourneyState || (JourneyState = {}));
export var TransportMode;
(function (TransportMode) {
    TransportMode["BIKE"] = "bike";
    TransportMode["CAR"] = "car";
    TransportMode["ELECTRIC_BIKE"] = "electric_bike";
    TransportMode["CART"] = "cart";
    TransportMode["LOCAL_TRANSPORT"] = "local_transport";
    TransportMode["OTHERS"] = "others";
})(TransportMode || (TransportMode = {}));
export var JourneyPurpose;
(function (JourneyPurpose) {
    JourneyPurpose["CLIENT_VISIT"] = "client_visit";
    JourneyPurpose["SITE_INSPECTION"] = "site_inspection";
    JourneyPurpose["MEETING"] = "meeting";
    JourneyPurpose["DELIVERY"] = "delivery";
    JourneyPurpose["COLLECTION"] = "collection";
    JourneyPurpose["OTHER"] = "other";
})(JourneyPurpose || (JourneyPurpose = {}));
export var GPSAccuracyLevel;
(function (GPSAccuracyLevel) {
    GPSAccuracyLevel["HIGH"] = "high";
    GPSAccuracyLevel["MEDIUM"] = "medium";
    GPSAccuracyLevel["LOW"] = "low";
    GPSAccuracyLevel["WEAK_SIGNAL"] = "weak_signal";
})(GPSAccuracyLevel || (GPSAccuracyLevel = {}));
export var JourneyEvent;
(function (JourneyEvent) {
    JourneyEvent["STARTED"] = "journey:started";
    JourneyEvent["STOPPED"] = "journey:stopped";
    JourneyEvent["PAUSED"] = "journey:paused";
    JourneyEvent["RESUMED"] = "journey:resumed";
    JourneyEvent["GPS_UPDATED"] = "gps:updated";
    JourneyEvent["HEARTBEAT_SENT"] = "heartbeat:sent";
    JourneyEvent["HEARTBEAT_FAILED"] = "heartbeat:failed";
    JourneyEvent["INVALIDATED"] = "journey:invalidated";
    JourneyEvent["ERROR"] = "journey:error";
    JourneyEvent["SESSION_RESTORED"] = "session:restored";
})(JourneyEvent || (JourneyEvent = {}));
//# sourceMappingURL=enums.js.map