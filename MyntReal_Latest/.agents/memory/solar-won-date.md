---
name: Solar won date bucketing
description: Which date field to use when bucketing "Won" leads into monthly/weekly trend columns — differs by lead type.
---

## Rule (DC-SOLAR-WON-DATE-001)

When computing **Won count / Win Value / Win Received** for trend tables:

| Lead type | Date used |
|---|---|
| Solar lead (`solar_pipeline_status IS NOT NULL`) | `submit_date` — the bank/govt application submission date (manually entered in Solar Leads master) |
| All other leads (EV B2B, ETC, normal CRM) | `actual_close_date` (cast to Date) |
| Fallback (both null) | `COALESCE(submit_date, created_at::date)` — the general trend date |

**Why:** Solar "won" is defined operationally as the moment the application is submitted (visible in the "Submit Date" column of the Solar Leads master table), not when the CRM status was flipped to Won. Using actual_close_date for solar caused dev/prod discrepancies.

**How to apply:** In any trend/breakdown query that buckets won leads by date, build the won-date expression as:
```python
_is_solar = CRMLead.solar_pipeline_status.isnot(None)
_won_dt = _f.coalesce(
    _sa_case((_is_solar, CRMLead.submit_date), else_=_sa_cast(CRMLead.actual_close_date, _sa_Date)),
    _trend_date_fallback,
)
```

Currently applied in: monthly trend Q2 and weekly trend Q2 inside `lead_analytics` endpoint (`crm.py`).
