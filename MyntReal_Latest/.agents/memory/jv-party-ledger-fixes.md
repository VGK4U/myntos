---
name: JV Party Ledger Cancel/Edit Fixes
description: How JournalVoucher cancel and edit interact with party_ledger — bugs and their fixes.
---

## Cancel Flow — DC-JV-CANCEL-PL-001
After posting the REV- reversal entry, explicitly mark the ORIGINAL party_ledger row(s)
as source_status='CANCELLED' using a filtered UPDATE (reference_number == jv.voucher_number)
to avoid tagging the REV- row itself.

**Why:** Cancel only added a reversal row; original row stayed CONFIRMED and appeared active in ledger.

**How to apply:** Any future cancel flow that posts a reversal must also mark the original row.

## Edit Flow — DC-JV-EDIT-REBALANCE-001
After deleting old PL rows and re-posting a new one, cascade-recalculate running_balance
for ALL party_ledger rows of every affected party (capture old party name BEFORE delete).

**Why:** stored running_balance on intermediate rows is stale after delete+repost; the new
entry is correct but all entries between original and new are wrong.

## EXTERNAL Party Balance — DC-PARTY-BAL-001
_get_running_balance now accepts optional party_name; when party_id=0, also filters
by party_name to prevent cross-contamination across EXTERNAL parties sharing party_id=0.

## Historical Data Note (back-fill SQL if needed)
UPDATE party_ledger pl SET source_status = 'CANCELLED'
FROM journal_vouchers jv
WHERE pl.reference_type = 'JOURNAL' AND pl.reference_id = jv.id
  AND pl.reference_number = jv.voucher_number AND jv.status = 'CANCELLED'
  AND pl.source_status = 'CONFIRMED';
