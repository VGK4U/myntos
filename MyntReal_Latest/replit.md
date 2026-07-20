# MNR Membership & Business Facilitation Platform

## Overview
The MNR Platform is a comprehensive system designed to manage and scale electric vehicle (EV) networks, as well as integrate distinct Real Estate and Insurance programs. It provides robust capabilities for user and binary tree management, multi-stream income calculation, and a dual-wallet withdrawal system. The platform aims to offer a secure, scalable environment for managing memberships, financial operations, and business processes within the EV market and related financial sectors, fostering growth and operational efficiency.

## User Preferences
Preferred communication style: Simple, everyday language.

**CRITICAL: Web-Mobile Parity Rule**
- ALL changes (features, UI updates, labels, fixes) MUST be applied to BOTH web AND mobile platforms
- No exceptions unless explicitly marked as "Admin-only" or "Desktop bulk operation"

## System Architecture

### Core Architectural Principles
The system utilizes a `company_id` DC Protocol for data segregation and a Zynova Dual-Segment System for Real Estate and Insurance, each with dedicated databases and an audit framework. Security is paramount, incorporating SQL injection/path traversal prevention, secure password hashing, `TrustedHostMiddleware`, and MNR ID validation. Access is restricted to MNR Members and Staff, governed by menu-based controls and a "Write, Verify, Validate" (WVV) protocol for atomic data updates.

### UI/UX Decisions
The frontend is built with vanilla HTML, CSS, JavaScript, and Bootstrap 5, adhering to Mynt Real LLP branding, a dark theme, and WCAG 2.1 AA accessibility standards. It features a unified RVZ Sidebar Menu and role-isolated navigation based on a Zero-Default Access Policy.

### Technical Implementations
The backend is powered by Python FastAPI, SQLAlchemy ORM, and PostgreSQL, employing JWT-based authentication and APScheduler for task automation. Key implementations include a universal upload system, enterprise-grade path traversal protection, a universal GPS service integrated with the WVV Protocol, NDA enforcement middleware, and a dynamic menu registry. FastAPI POST/PUT endpoints explicitly use `Body(...)` for Pydantic models. A unified Journey-Core TypeScript library manages GPS tracking. The mobile application is Capacitor-based (Vite + TypeScript), offering Staff, MNR Member, and Partner portals with multi-portal login, biometric authentication, selfie capture, and offline API queuing. A Tally-style double-entry accounting system (DC_ACCT_LEDGER_001) is implemented. All datetime storage uses IST naive datetimes (Asia/Kolkata, UTC+5:30).

### Feature Specifications
The platform includes comprehensive modules for:
-   **User & Binary Tree Management**: Automatic placement and multi-stream income calculation, including VGK4U specific income.
-   **Wallet System**: Earning, Withdrawable, and Upgrade wallets.
-   **Financial Management**: MNR-SFMS Integration, PO Invoice System, Payment Voucher System (DC-BANK-001/002/003), Ledger Masters Page, Party Ledger Page, Tally-style account-ledger auto-posting, historical posting backfill, and VGK Income Unified Pipeline (DC-VGK-INCOME-UNIFIED-001) with Tally-style JV postings (CGST+SGST 9%+9%), DRAFT→PENDING→RELEASED→PAID state machine, cross-company commission routing (Zynova/MNR/MyntReal), bank/cash payment with UTR, skip-level for EA/super staff, and CRM + solar advance hooks.
-   **Sales & Marketing**: Awards & EV Coupon Systems, Announcements System, Sales Team Reports, CRM Lead Management, CRM Commission System, and VGK Referral Points System.
-   **Staff & Operations**: Role-Based Access Control, Staff Management (authentication, RBAC, NDA, tasking, time, KRA, GPS tracking, payroll), Journey Management System, Call Quality Review System, Auto Dialer, WhatsApp Center, and MyOperator Call Dashboard integration.
-   **Inventory & Service**: Official Partner Order Management System, Master Modules (HSN/SAC codes, vendors, stock items), Invoice & Stock Validation, EV Service Tickets Module, Public Service Ticket Spare Parts Catalog, Spare Parts Lifecycle System, and Sales Invoice System.
-   **Specialized Systems**: Real Estate Marketplace Module (Real Dreams), Signup Categories Module, Universal Engagement System, MNR Points & Bonanza Systems, Dynamic System Guides, KYC Upload & Approval, Catalog PDF System, MNR E-Com Lite, and AI Calling KB Auto-Enrichment Pipeline.
-   **External Integrations**: VGK AI Assistant (using Gemini 2.0 Flash), WhatsApp OTP Forgot Password for all portals, and Meta Template Studio for WhatsApp messaging.
-   **Web/Mobile Parity Features**: Audience-aware endpoints (`audience` query param) for content serving to MNR and VGK4U users, with specific mobile pages for VGK.
-   **Website Management**: Website Asset Manager, WhatsApp Link Tracking, CRM WA Send Log, VGK Gallery, Hub Media Share Buttons, Website Assets Cloud Persistence, and Quill Rich Text Editor for blogs.
-   **Stock System**: Multi-company stock ledger with inter-company margin configuration.

## External Dependencies

### Database
-   PostgreSQL 16
-   Neon PostgreSQL

### Python Packages
-   FastAPI
-   SQLAlchemy
-   psycopg2
-   APScheduler
-   python-jose
-   passlib/bcrypt
-   pandas
-   Werkzeug
-   qrcode[pil]

### Frontend Libraries
-   Bootstrap 5
-   Font Awesome
-   Chart.js
-   PDF.js

### Testing Tools
-   Selenium WebDriver
-   ChromeDriver

### Media Processing
-   ffmpeg
-   Pillow (PIL)

### Third-Party Services
-   Replit
-   Nominatim (OpenStreetMap)
-   Google Gemini 2.0 Flash

## B2B SaaS Layer — Phases 1-5 (Tasks #39–#43, May 2026)

Foundation for converting MyntReal SFMS into a multi-tenant B2B platform.
Default `B2B_ENFORCE=false` ⇒ shadow mode ⇒ existing users see zero change.

**Tables (all under `platform_*` / `b2b_*` namespaces):**
- Phase 1: `platform_clients`, `platform_modules`, `platform_module_dependencies`,
  `platform_plans` + `platform_plan_modules`, `platform_subscriptions` + `platform_subscription_modules`,
  `platform_module_pricing` + `platform_client_module_pricing_override`,
  `platform_audit_log`, `b2b_shadow_log`, `associated_companies.client_id` (nullable FK)
- Phase 4: `platform_invoices`, `platform_invoice_lines`, `platform_payments`

**Migrations (applied idempotently via `dc_migrations` key registry):**
- `add_platform_b2b_20260503.sql`              (Phase 1, key `platform_b2b_phase1_20260503`)
- `add_platform_b2b_phase4_billing_20260503.sql` (Phase 4, key `platform_b2b_phase4_20260503`)

**Code:**
- Models:  `backend/app/models/platform_b2b.py`, `platform_b2b_billing.py`
- Seeder:  `backend/app/services/platform_b2b_seed.py` (auto-runs at startup)
- Hooks:   `backend/app/services/b2b_shadow.py` (decision + log), `b2b_enforce.py` (Phase-3 helpers)
- Billing: `backend/app/services/platform_b2b_billing.py` (invoices, payments, dunning)
- API:     `backend/app/api/v1/endpoints/platform_b2b.py` → `/api/v1/platform-b2b`
  - `/status` — any active staff
  - `/signup` — public (anonymous) self-service tenant sign-up
  - `/me/tenant`, `/my-menu`, `/check-entitlement` — current-user scoped
  - everything else gated by `require_b2b_super_admin` (role_code in {SUPER_ADMIN, B2B_SUPER_ADMIN, CEO, CTO, FOUNDER} OR `hierarchy_level >= 90`)
- UI:      `frontend/staff_b2b_clients.html` (tabbed admin), `staff_my_tenant.html` (self-service), `b2b_signup.html` (public, served at `/b2b-signup`)

**Tests (24/24 passing):**
- Phase 1: `backend/tests/test_b2b_phase1_foundation.py` (8 tests)
- Phase 2: `backend/tests/test_b2b_phase2_admin.py`     (2 tests)
- Phase 3: `backend/tests/test_b2b_phase3_enforce.py`   (5 tests)
- Phase 4: `backend/tests/test_b2b_phase4_billing.py`   (3 tests, e2e invoice→payment cycle)
- Phase 5: `backend/tests/test_b2b_phase5_signup.py`    (6 tests)

**Phase capabilities:**
- **Phase 1 (Foundation, shadow):** 11 tables, MNR-INTERNAL seeded, all 578 menu rows ingested as modules, internal tenant entitled to everything; `is_module_entitled()` always allows + logs.
- **Phase 2 (Admin UX & Pricing):** 17 endpoints (CRUD over clients / modules / module-deps / plans + plan-modules / subscriptions + sub-modules / pricing-overrides / effective-pricing); tabbed admin UI.
- **Phase 3 (Enforcement):** `b2b_required(module_code)` dependency, `filter_menu_by_entitlement` helper, `/my-menu` and `/preview-enforcement` endpoints, per-client `status='suspended'` kill switch, `B2B_ENFORCE` flag controls whether decisions become 403s (default off).
- **Phase 4 (Billing):** invoice generation from effective pricing (monthly + annual w/ "free months"), partial/full payment recording with status transitions (open → partial → paid → overdue), dunning service that flags overdue invoices and suspends clients past `grace_days`.
- **Phase 5 (Self-Service):** public `/api/v1/platform-b2b/signup` endpoint (anonymous) creates trial tenant; `/staff/my-tenant` portal; `/b2b-signup` public page.

**Feature flag:** `B2B_ENFORCE` (default `false`). When `true`, `is_module_entitled` returns the real decision and the `b2b_required` dependency 403s blocked requests. When `false`, all decisions are logged but always allow (shadow mode).

**Cross-phase invariant:** with `B2B_ENFORCE=false` and the internal tenant seeded with `INTERNAL_FULL` (all 578 modules entitled), every existing user/route behaves byte-identically to pre-B2B.

**Phase 5b — deferred, separate task (NOT in scope of #43):**
Tenant-scoped data isolation audit. Today every legacy SFMS query implicitly assumes "MyntReal is the only tenant". Before any external tenant is given live access, every query must be audited and filtered by `associated_companies.client_id` (which Phase 1 added as a nullable FK and back-filled to internal). This is a multi-week mechanical refactor that intentionally lives outside this task series — flipping `B2B_ENFORCE=true` without it would still leak data across tenants.