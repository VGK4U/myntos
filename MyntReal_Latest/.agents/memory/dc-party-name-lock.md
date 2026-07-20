---
name: DC-PARTY-NAME-LOCK-001 guard scope
description: The party name lock must only fire for VENDOR/EXTERNAL party types
---

**Rule:** DC-PARTY-NAME-LOCK-001 (which looks up a party_id in VendorMaster to lock the party name) must be guarded with `if party_type in ('VENDOR', 'EXTERNAL'):` before it runs.

**Why:** Without this guard, a StaffEmployee with `id=N` can accidentally match a VendorMaster row with `id=N`, causing the staff payment JV to write VENDOR party_ledger entries attributed to a completely different vendor (e.g. staff id=28 matched vendor VISAKHA OFFSET PRINT id=28). This silently mis-posts the ledger entry.

**How to apply:** In `staff_accounts_service.py`, the DC-PARTY-NAME-LOCK-001 block must always check `party_type in ('VENDOR', 'EXTERNAL')` as a precondition. Also normalise `_resolved_party_type` via `_PT_NORM` early in `_add_party()`.
