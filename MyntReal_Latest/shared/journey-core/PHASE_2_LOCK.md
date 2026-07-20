# PHASE 2 LOCK — WEB AUTHORITY CONFIRMED

**Date Locked:** January 23, 2026

## Verification Checklist

- [x] Web journey tracking depends exclusively on journey-core
- [x] No journey math exists outside journey-core (legacy functions throw fatal errors)
- [x] Canonical `/staff/journeys/*` APIs enforced
- [x] Attendance GPS untouched (separate system)
- [x] Zero visible UI change
- [x] Heartbeat interval owned by core (15 seconds)
- [x] Distance threshold owned by core (0 meters)

## DO NOT:

- Add fallback logic to legacy GPS functions
- Add journey math in UI/frontend code
- Change heartbeat timing in platform-specific code
- Bypass journey-core for journey tracking

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      journey-core                           │
│  /shared/journey-core/                                      │
│  - JourneyEngine (state machine, heartbeats, math)         │
│  - Validators (WVV, speed, accuracy)                       │
│  - TrackPoint builder                                       │
│  - Geo utilities (haversine, distance)                     │
└─────────────────────────────────────────────────────────────┘
              │                           │
              ▼                           ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│     Web Adapters        │   │   Mobile Adapters       │
│  /frontend/js/journey-  │   │   (Phase 3)             │
│  core/                  │   │                         │
│  - WebGPSAdapter        │   │   - MobileGPSAdapter    │
│  - WebStorageAdapter    │   │   - MobileStorageAdapter│
│  - WebAPIAdapter        │   │   - MobileAPIAdapter    │
│  - WebPlatformAdapter   │   │   - MobilePlatformAdapter│
│  - JourneyWebFacade     │   │                         │
└─────────────────────────┘   └─────────────────────────┘
```

## Files Modified

- `frontend/js/gps-service.js` - Journey math functions throw fatal errors
- `frontend/staff_my_journeys.html` - Uses journey-core only (no fallback)
- `frontend/js/journey-core/*` - Web adapters (thin translators)
- `shared/journey-core/src/engine/journey-engine.ts` - Core with 15s heartbeat

## Next Allowed Work

**Phase 3:** Mobile adapters only

The mobile app (`/mobile/`) will implement:
- MobileGPSAdapter (Capacitor geolocation)
- MobileStorageAdapter (Capacitor preferences)
- MobileAPIAdapter (Capacitor HTTP)
- MobilePlatformAdapter (background tasks, native timers)

No changes to journey-core or web adapters allowed until Phase 3 is complete.
