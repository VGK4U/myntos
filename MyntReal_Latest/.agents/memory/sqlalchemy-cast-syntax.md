---
name: SQLAlchemy text() double-colon cast
description: Using :param::type (PG shorthand cast) inside text() causes SyntaxError — use CAST(:param AS TYPE) instead.
---

## Rule

Never write `:param::type` inside SQLAlchemy `text()` queries. The `text()` parser sees the second `:` as the start of a new bind parameter name and raises:

```
psycopg2.errors.SyntaxError: syntax error at or near ":"
```

## Safe alternatives

| Wrong | Right |
|---|---|
| `:start::date` | `CAST(:start AS DATE)` |
| `(:end + INTERVAL '1 day' * :grace)::date` | `CAST(:end AS DATE) + CAST(:grace \|\| ' days' AS INTERVAL)` |
| `:val::numeric` | `CAST(:val AS NUMERIC)` |

**Why:** SQLAlchemy's `text()` bind-param scanner is regex-based; it stops at `:name` patterns but the double-colon trips it up.

**How to apply:** Any time you add a `::` cast to a raw SQL string wrapped in `text()`, convert it to `CAST(... AS ...)` form before committing.
