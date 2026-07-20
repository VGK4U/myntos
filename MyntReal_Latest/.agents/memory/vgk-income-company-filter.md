---
name: VGK income company_id cross-filter bug
description: vgk_cash_income_entries and vgk_wallet_transactions store the LEAD's company_id, not the partner's — member API must never filter by partner.company_id.
---

## Rule
When querying `vgk_cash_income_entries` or `vgk_wallet_transactions` for a member's own view, filter by `partner_id` only. Never add `company_id = current_member.company_id`.

**Why:** Income entries and wallet transactions are created with the **lead's** `company_id` (e.g. company_id=3 for VGK4U SAAS leads), not the partner's own company_id (e.g. company_id=1 for MyntReal). A Solar lead completed under company_id=3 creates VCI entries with company_id=3; the partner (Kalla Nookunidu, company_id=1) would see zero entries if the API filtered by their own company_id.

**How to apply:**
- `/member/cash-income`: ORM query + summary SQL → `WHERE partner_id = :pid` only (no `company_id`).
- `/member/wallet`: wallet transaction history → filter by `partner_id` only.
- The existing `DC-FIX-ADV-WALLET-EARNED-001` comment in the file already documents this pattern for the `earned_total` query; the Jun 2026 fix (`DC-FIX-COMPANY-FILTER-001`) extended it to the entry list, summary, and wallet history.
- Staff-facing endpoints (e.g. `/staff/vgk/cash-income/drafts`) that filter by `company_id` are correct — staff always work within one company context.
