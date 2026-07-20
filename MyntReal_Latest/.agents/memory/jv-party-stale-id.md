---
name: JV party_id stale-ID and async race
description: Two bugs that cause party_ledger entries to be posted under the wrong party when creating PAYMENT/RECEIPT/CONTRA vouchers.
---

## Bug 1 — DC-PARTY-LOCK-STALE-002 (backend)

**Rule:** Inside `JournalVoucherService.create`, DC-PARTY-NAME-LOCK-001 looks up `vendor_master` by `party_id` and overrides `_resolved_party_name`. If the vendor name in DB differs from the user-typed `party_name` (stale party_id from a prior session selection), the party_ledger was posted under the wrong party while `jv.party_name` stayed correct (set before the lock ran).

**Fix:** Added name-mismatch check inside the lock block. If `user_name.upper() != db_vendor_name.upper()` AND user supplied a non-empty name → discard the stale `party_id`, keep user's name. Added `DC-JV-PARTY-SYNC-001` to also sync `jv.party_name = _resolved_party_name` after the block so the JV record always matches what gets posted to `party_ledger`.

**How to apply:** Any time party_id comes from the frontend for PAYMENT/RECEIPT/CONTRA, the stale check fires automatically. Rename case (vendor was renamed but party_id is still correct) is safe: names match → canonical DB name used as before.

## Bug 2 — DC-PARTY-ASYNC-RACE-001 (frontend)

**Rule:** `_saveManualParty(name)` is called async when user selects an EXTERNAL party with id=0. Its callback updates `_selectedPartyId = d.id`. If `resetForm()` (which clears `_selectedPartyId = null`) ran between the call and the callback (fast submit → reset → callback returns), the stale ID gets written back into `_selectedPartyId` and poisons the *next* voucher.

**Fix:** Callback now guards with `if (document.getElementById('fvPartyName').value === name)` before writing. If form was reset, `fvPartyName` is empty → guard fails → ID discarded.

## Data repair for existing wrong entries

Re-open the affected voucher in Edit modal and click Save Changes (no field changes needed). The PUT endpoint (`JournalVoucherService.update`) does NOT send `party_id`, so `_resolved_party_id = 0`, DC-PARTY-NAME-LOCK-001 never fires, and the party_ledger entry is deleted+reposted with the correct party_name from `jv.party_name`.
