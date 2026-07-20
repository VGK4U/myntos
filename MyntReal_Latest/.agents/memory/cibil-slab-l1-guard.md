---
name: CIBIL advance slab bonus level guard
description: release_advance() handles both L1 (₹1,000) and L2 (₹500) CIBIL advances; slab bonus must only fire for L1.
---

## Rule
In `vgk_solar_advance.py`, `release_advance(db, lead_id, released_by_id, _level=1)`:
- CIBIL path (line ~848): `apply_slab_bonus_if_active(...)` must be guarded by `if _level == 1`.
- DVR path (line ~443): already had this guard.

**Why:** L2 partners also get CIBIL advances (₹500). Without the guard, every L2 advance release also triggered the ₹3,000 Solar Bonanza, wrongly crediting the senior partner.

**How to apply:** Any future function that calls `apply_slab_bonus_if_active` must always verify it is operating on an L1 advance before calling it.

**Data cleanup:** dc_slab_l1_only_cleanup_20260707 — cancelled 8 wrong SLAB_BONUS entries (₹24,000), reversed wallet for 1 partner (Geetharam, ₹2,700).
