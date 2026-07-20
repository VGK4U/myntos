---
name: Bonanza date-only rule
description: Bonanza start/end dates must always be midnight; queries need ::date cast; solar uses all 4 category IDs.
---

## Rules

1. **Storage**: `start_date` and `end_date` on the `bonanza` table must always be midnight (00:00:00). The `create_bonanza` and `edit_bonanza` endpoints both call `.replace(hour=0, minute=0, second=0, microsecond=0)` before writing.

2. **Frontend input**: `mStartDate` / `mEndDate` are `type="date"` inputs. `_toISO()` appends `T00:00:00` (never uses `new Date().toISOString()` which would apply timezone shift). `_toLocalDatetimeValue()` returns `YYYY-MM-DD` only.

3. **SQL window queries**: `first_payment_received_date` is a DATE column; bonanza start/end are timestamps. Always cast: `>= :start::date` and `<= (:end + INTERVAL '1 day' * :grace)::date`. Applies to both member tracking and `_count_solar_advances_for_bonanza`.

4. **Multi-company solar**: When `bonanza.segment_id` is any of `_SOLAR_CAT_IDS = (6, 19, 36, 48)`, expand the SQL filter to `category_id = ANY(:seg_list)` with all 4 IDs — not just the bonanza's segment_id. Otherwise leads from other companies' solar categories are invisible.

**Why:** Bonanza 55 was created with `start_date = 2026-07-01 14:18:00`. Because `first_payment_received_date` is a DATE (`2026-07-01 00:00:00`), the comparison `DATE < TIMESTAMP 14:18` silently dropped same-day leads. Also, segment_id=6 is only MyntReal Solar; the other 3 companies use 19, 36, 48.

**How to apply:** Any new bonanza endpoint that uses start/end for range filtering must cast to `::date`. DB already corrected (41 rows) via `DATE_TRUNC`.
