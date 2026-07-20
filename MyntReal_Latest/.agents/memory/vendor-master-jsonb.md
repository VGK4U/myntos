---
name: vendor_master applicable_companies JSONB
description: applicable_companies is JSONB not integer[], correct SQLAlchemy operator for company filtering
---

The `vendor_master.applicable_companies` column is stored as **JSONB** (PostgreSQL), not a native integer array.

**Rule:** Never use `cast([company_id], ARRAY(Integer))` or `.contains([company_id])` with an integer array cast. This causes `operator does not exist: jsonb @> integer[]`.

**How to apply:** Use JSONB containment operator:
- SQLAlchemy: `VendorMaster.applicable_companies.op('@>')(func.to_jsonb(company_id))`
- Raw SQL: `applicable_companies @> to_jsonb(:company_id)` or `applicable_companies @> to_jsonb(pl.company_id)`

**Why:** The column stores arrays like `[3, 4]` as JSONB. Checking if a company_id integer is in that array requires JSONB containment semantics — `'[3,4]'::jsonb @> '4'::jsonb` returns true.
