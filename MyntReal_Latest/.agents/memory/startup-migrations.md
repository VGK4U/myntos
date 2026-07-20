---
name: Startup migrations — inline in main.py only
description: Where to add new schema migrations so they actually run at startup
---

## Rule
All new schema migrations must be added **inline in `backend/app/main.py`**, right after the `DC-SALES-SO-NUM` block (~line 6586). Do NOT add migrations inside `run_schema_bootstrap()` in `schema_bootstrap.py`.

## Why
`run_schema_bootstrap()` (defined at line ~2160 in `schema_bootstrap.py`) is **never called** from `main.py`'s lifespan startup sequence. The startup sequence calls individual bootstrap functions from `schema_bootstrap.py` by name (e.g. `bootstrap_accounts_default_access`, `bootstrap_withdrawal_duplicate_guard`) OR runs SQL inline. Anything placed inside `run_schema_bootstrap()` silently does nothing.

## How to apply
- Paste a new inline migration block in `main.py` after the last existing migration block.
- Use `SessionLocal()` (already imported from `app.core.database`) — the `engine.begin()` pattern also works.
- Gate idempotency with a `dc_migrations` key check (`SELECT 1 FROM dc_migrations WHERE key='...' LIMIT 1`).
- Log with `print("[DC_TAG] ✅ ...", flush=True)` — uvicorn captures print() reliably.
- Wrap the entire block in `try/except Exception as _e: print(f"[DC_TAG] ⚠️ Non-fatal: {_e}", flush=True)`.
- Verify in logs: grep for your tag in `/tmp/logs/FastAPI_Backend_*.log` after restart.

## Per-entry SAVEPOINT pattern (when looping over rows)
When a migration loops over rows and does multiple SQL ops per row (UPDATE + INSERT), one failing row poisons the whole Postgres transaction via `InFailedSqlTransaction`. Use SAVEPOINTs:

```python
for _row in _rows:
    _db.execute(_txP("SAVEPOINT sp_entry"))
    try:
        # ... UPDATE + INSERT for this row ...
        _db.execute(_txP("RELEASE SAVEPOINT sp_entry"))
    except Exception as _e:
        _db.execute(_txP("ROLLBACK TO SAVEPOINT sp_entry"))
        print(f"[DC_TAG] ⚠️ row {_row.id}: {_e}", flush=True)
```

**Why:** Without SAVEPOINT, the first failing INSERT (e.g. a check constraint violation) aborts the entire transaction and all subsequent rows fail with `InFailedSqlTransaction` even if they would have succeeded.
