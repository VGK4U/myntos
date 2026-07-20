# PHASE 3 LOCK — MOBILE ADAPTERS ONLY

**Date Locked:** January 23, 2026

## Verification Checklist

- [x] Mobile uses journey-core exclusively
- [x] No business logic in mobile adapters
- [x] No UI redesign
- [x] Background GPS delegated to platform adapter
- [x] Same events as Web
- [x] Same WVV/DC behavior (inherited from core)
- [x] Same API payloads as Web

## Mobile Adapters Created

| Adapter | File | Purpose |
|---------|------|---------|
| MobileGPSAdapter | `MobileGPSAdapter.ts` | Capacitor Geolocation → RawGPSPosition |
| MobileStorageAdapter | `MobileStorageAdapter.ts` | Capacitor Preferences for session |
| MobileAPIAdapter | `MobileAPIAdapter.ts` | CapacitorHttp for canonical APIs |
| MobilePlatformAdapter | `MobilePlatformAdapter.ts` | Timers, logging, AppState |
| JourneyMobileFacade | `JourneyMobileFacade.ts` | UI bridge (mirrors Web) |

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
│  (Phase 2 - LOCKED)     │   │   (Phase 3 - LOCKED)    │
│                         │   │                         │
│  - WebGPSAdapter        │   │   - MobileGPSAdapter    │
│  - WebStorageAdapter    │   │   - MobileStorageAdapter│
│  - WebAPIAdapter        │   │   - MobileAPIAdapter    │
│  - WebPlatformAdapter   │   │   - MobilePlatformAdapter│
│  - JourneyWebFacade     │   │   - JourneyMobileFacade │
└─────────────────────────┘   └─────────────────────────┘
```

## DO NOT:

- Add journey math in mobile code
- Add WVV validation in adapters
- Add business logic to any adapter
- Change heartbeat timing in mobile
- Add fallback logic if core fails
- Modify attendance tracking

## Kill Test

To verify journey-core authority:
1. Comment out journey-core import in `JourneyMobileFacade.ts`
2. Build mobile app
3. Expected: Build fails or journey cannot start
4. If journey still starts → Phase 3 FAILED

## Next Phase

**Phase 4:** Parity testing only
- Verify Web and Mobile produce identical journey data
- Verify same heartbeat payloads
- Verify same WVV compliance results
- No code changes in Phase 4
