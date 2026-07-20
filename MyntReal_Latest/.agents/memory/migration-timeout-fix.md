---
name: DC-MIGRATION-TIMEOUT-001 — migration session statement_timeout fix
description: Why statement_timeout must NOT be set at engine connect_args level; where it should live instead.
---

# DC-MIGRATION-TIMEOUT-001 — Migration session statement_timeout

## The rule
Never set `statement_timeout` in `connect_args` / `options` on the SQLAlchemy engine. Apply it inside `get_db()` only.

## Why
Both Helium and Neon engines previously had `"-c statement_timeout=25000"` in `connect_args`. This applies the timeout to **every** connection from the pool — including the raw `engine.connect()` and direct `SessionLocal()` calls used by startup migrations.

When the backend restarts under any DB pressure (Neon cold start, local postgres lock contention, two processes starting simultaneously), the migration key-check `SELECT 1 FROM dc_migrations WHERE key=...` can take >25s waiting for a lock, causing `QueryCanceled: canceling statement due to statement timeout`. With 23+ migrations each timing out at 25s, startup hangs for 10–15 minutes.

## How to apply
- `database.py`: `connect_args` must NOT contain `options: -c statement_timeout=...` for either Helium or Neon engines.
- `get_db()` (the FastAPI dependency used by ALL API endpoints): execute `SET statement_timeout = 25000` as the first statement — this preserves 25s query protection for all API requests.
- Startup migrations that call `engine.connect()` or `SessionLocal()` directly bypass `get_db()` → they inherit no timeout → they can wait as long as needed.
- The pattern `conn.execute(text("SET statement_timeout = 0"))` that already exists in many migration blocks is now redundant but harmless — leave it.
