---
name: Startup migration fast-skip cache
description: _applied_keys preload pattern in _startup_worker; why _sa_text alias is required
---

## Rule
Use `from sqlalchemy import text as _sa_text` (NOT bare `text`) for the `_applied_keys` preload and `_mig_done()` inside `_startup_worker()`.

**Why:** Python's scoping rules treat any variable that is *assigned* anywhere in a function as local for the *entire* function. `_startup_worker()` contains many `from sqlalchemy import text` statements in later migration blocks, making `text` a local variable throughout. The preload code runs *before* those assignments → `text("SELECT …")` raises `UnboundLocalError: cannot access local variable 'text' where it is not associated with a value`. The `_sa_text` / `_sa_text2` aliases avoid this collision entirely.

**How to apply:**
- Preload (function body): `from sqlalchemy import text as _sa_text` then `_kc.execute(_sa_text(…))`
- `_mig_done()` helper (nested function): `from sqlalchemy import text as _sa_text2` inside the try block

## Pattern (what is in main.py as of 2026-07-11)

```python
from sqlalchemy import text as _sa_text
_applied_keys: set = set()
try:
    with engine.connect() as _kc:
        _applied_keys = {r[0] for r in _kc.execute(_sa_text("SELECT key FROM dc_migrations")).fetchall()}
    print(f"[DC-STARTUP] ✅ Migration key cache: {len(_applied_keys)} keys preloaded (fast-skip active)", flush=True)
except Exception as _ke:
    print(f"[DC-STARTUP] ⚠️ Key cache load skipped: {_ke}", flush=True)

def _mig_done(key: str) -> None:
    try:
        from sqlalchemy import text as _sa_text2
        with engine.begin() as _mc:
            _mc.execute(_sa_text2("INSERT INTO dc_migrations(key) VALUES(:k) ON CONFLICT DO NOTHING"), {"k": key})
        _applied_keys.add(key)
    except Exception:
        pass
```

Every guarded block then uses: `if 'DC-KEY-NAME' not in _applied_keys:`
After successful DDL: `_mig_done('DC-KEY-NAME')`
In the else branch: `print("⏭️ … already applied")`

## Performance impact (verified 2026-07-11)
- Before: 114+ individual SELECT round-trips to dc_migrations + 200+ per-SQL connections
- After: 1 SELECT preload → 147 keys cached → 55 blocks show ⏭️ and are entirely skipped
- Production startup target: ~7 min → <2 min

## When adding new migration blocks
Always wrap with `if 'DC-NEW-KEY' not in _applied_keys:` guard and call `_mig_done('DC-NEW-KEY')` on success. Do NOT add guards to blocks that intentionally re-run every boot (e.g., DC-BILLING-RECALC, DC_INVOICE_PAYMODE_001, DC_CASHFLOW_001 — these check current state, not one-time migrations).
