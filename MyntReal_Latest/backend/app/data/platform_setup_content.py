"""
DC_PLATFORM_GUIDE_001 (May 2026)

Curated content for the Platform Setup Guide page at
`/staff/platform-setup-guide`. Two kinds of content live here:

  1. SETUP_SECTIONS — the step-by-step tenant-onboarding walkthrough. Edit
     these whenever the operational steps change (new integration, new env
     var, new bootstrap script, etc.).
  2. PLATFORM_CHANGELOG — append-only log of meaningful platform-level
     changes. Add a new entry every time we ship a feature, schema change,
     or operational tweak so the page becomes a single source of truth.

The endpoint at /api/v1/staff/platform-setup-guide composes this curated
content with LIVE data drawn from the menu registry, integration registry,
and DB stats — so the page stays accurate even between manual updates.
"""

# ---------------------------------------------------------------------------
# 1. Tenant setup walkthrough (curated, version-controlled)
# ---------------------------------------------------------------------------
SETUP_SECTIONS = [
    {
        "id": "create-tenant",
        "title": "How to Create a New Tenant",
        "icon": "fas fa-flag-checkered",
        "summary": (
            "Step-by-step, end-to-end walkthrough for onboarding a brand-new "
            "tenant onto the platform. Follow these in order — each step "
            "deep-links to the page where you'll perform the action."
        ),
        "steps": [
            {
                "label": "0. Sign in as VGK4U Supreme",
                "detail": (
                    "Tenant onboarding is restricted to VGK4U Supreme "
                    "administrators only (e.g. MR10001). All actions below "
                    "must be performed from a Supreme login — regular staff "
                    "logins will receive a 403 from the tenant-create API."
                ),
                "links": [{"label": "Open Login", "route": "/login"}],
            },
            {
                "label": "1. Provision the workspace",
                "detail": (
                    "Fork or import this Replit project into the new "
                    "tenant's Replit account. Replit auto-provisions a "
                    "PostgreSQL database and sets the DATABASE_URL secret."
                ),
            },
            {
                "label": "2. Start the workflows",
                "detail": (
                    "Open the Workflows panel and verify FastAPI Backend, "
                    "Frontend Server, and Mobile App Watcher are all green. "
                    "Schema bootstrap, B2B seed, and sidebar sync run "
                    "automatically on every backend startup."
                ),
            },
            {
                "label": "3. Sign in as the first admin",
                "detail": (
                    "Use the seeded supreme admin (or insert a row into "
                    "the `staff` table with is_supreme=true) and sign in. "
                    "Reset the password via the password-reset utility "
                    "if needed."
                ),
                "links": [{"label": "Open Login", "route": "/login"}],
            },
            {
                "label": "4. Add the first company",
                "detail": (
                    "Configuration → Companies. Enter company name, code, "
                    "GST, and address. Mark is_active=true so it appears "
                    "in DAR / Consolidated reports."
                ),
                "links": [{"label": "Open Companies", "route": "/staff/accounts/companies"}],
            },
            {
                "label": "5. Define departments",
                "detail": (
                    "Configuration → Departments. Default seed creates "
                    "Sales, Accounts, Operations, HR — extend as needed "
                    "for the new tenant."
                ),
                "links": [{"label": "Open Departments", "route": "/staff/departments"}],
            },
            {
                "label": "6. Add employees",
                "detail": (
                    "Staff Dashboard → Employees. For each employee set "
                    "department, role, accessible companies (data_companies "
                    "field), and (for admins only) the supreme flag."
                ),
                "links": [
                    {"label": "Open Employees",          "route": "/staff/employees"},
                    {"label": "Open Employee Directory", "route": "/staff/employee-directory"},
                ],
            },
            {
                "label": "7. Configure accounting masters",
                "detail": (
                    "Set up the per-company segments, expense categories, "
                    "pricing config, and HSN catalog. The Tally-28-group "
                    "chart of accounts is seeded automatically."
                ),
                "links": [
                    {"label": "Segments",           "route": "/staff/accounts/segments"},
                    {"label": "Expense Categories", "route": "/staff/accounts/expense-categories"},
                    {"label": "Pricing Config",     "route": "/staff/accounts/pricing"},
                    {"label": "HSN Master",         "route": "/staff/accounts/hsn"},
                ],
            },
            {
                "label": "8. Wire up integrations",
                "detail": (
                    "Add the Google OAuth, Replit Mail, Twilio, and "
                    "(optionally) Stripe integrations via Replit's "
                    "integrations panel. Live presence is shown on the "
                    "Live Inventory tab — green = present, red = missing."
                ),
            },
            {
                "label": "9. Tailor menu access",
                "detail": (
                    "Use Menu Access Control to selectively grant pages "
                    "to each employee / role. Run Sidebar Sync if you've "
                    "edited the menu registry directly so changes "
                    "propagate immediately."
                ),
                "links": [
                    {"label": "Menu Access Control", "route": "/rvz/menu-access-config"},
                    {"label": "Sidebar Sync",        "route": "/staff/sidebar-sync"},
                    {"label": "Page Registry",       "route": "/staff/page-registry"},
                ],
            },
            {
                "label": "10. Smoke test",
                "detail": (
                    "Log out, sign back in as a non-admin staff member, "
                    "and verify the sidebar reflects their access. Open "
                    "DAR to confirm consolidated reporting works across "
                    "the new company."
                ),
                "links": [
                    {"label": "Open DAR",      "route": "/staff/accounts/DAR"},
                    {"label": "Audit Logs",    "route": "/staff/audit-logs"},
                    {"label": "Settings",      "route": "/staff/settings"},
                ],
            },
            {
                "label": "11. Verify in VGK SaaS → All Tenants",
                "detail": (
                    "Open VGK SaaS → All Tenants and confirm the new tenant "
                    "appears alongside the existing legacy set ('Tenant 1')."
                ),
                "links": [
                    {"label": "All Tenants",        "route": "/staff/my-tenant"},
                    {"label": "Platform Clients",   "route": "/staff/b2b-clients"},
                ],
            },
            {
                "label": "12. Publish to production",
                "detail": (
                    "Use Replit's Publish button to deploy. Choose VM "
                    "(single container) so backend + frontend share "
                    "localhost. Add a custom domain via Deployments → "
                    "Settings if needed."
                ),
            },
        ],
    },
    {
        "id": "overview",
        "title": "Platform Overview",
        "icon": "fas fa-sitemap",
        "summary": (
            "MyntReal / VGK4U SFMS is a multi-company B2B SaaS platform "
            "covering accounting (SFMS), inventory, payroll, CRM, service "
            "tickets, member rewards (MNR), VGK4U marketplace, vendor "
            "management, and consolidated reporting. It runs on Replit as "
            "two cooperating workflows."
        ),
        "steps": [
            {
                "label": "Architecture",
                "detail": (
                    "Backend: FastAPI (Python 3.11) on port 8000. "
                    "Frontend: Node.js HTTP server on port 5000 that "
                    "proxies API calls to the backend and serves static "
                    "HTML pages. Database: PostgreSQL (Replit-managed) "
                    "shared by both."
                ),
            },
            {
                "label": "Workflows",
                "detail": (
                    "`FastAPI Backend` runs uvicorn; `Frontend Server` "
                    "runs node server.js; `Mobile App Watcher` builds the "
                    "Vite mobile bundle into frontend/public/mobile."
                ),
            },
            {
                "label": "Tenancy",
                "detail": (
                    "All data is partitioned by `company_id` in the "
                    "`associated_companies` table. Employees see only "
                    "the companies allowed by their `data_companies` "
                    "field — supreme employees (VGK mentor / EA / "
                    "Accounts) get unrestricted access."
                ),
            },
        ],
    },
    {
        "id": "prerequisites",
        "title": "Prerequisites",
        "icon": "fas fa-clipboard-check",
        "summary": "What you need before starting onboarding for a new tenant.",
        "steps": [
            {"label": "Replit account",  "detail": "A Replit workspace with this project forked or imported."},
            {"label": "Database",        "detail": "Replit PostgreSQL provisioned. The DATABASE_URL secret is set automatically by Replit."},
            {"label": "Domain",          "detail": "Default *.replit.app domain works; custom domain optional via Replit Deployments."},
            {"label": "Admin email",     "detail": "An email address to act as the first super-admin / VGK mentor login."},
        ],
    },
    {
        "id": "secrets",
        "title": "Environment Secrets",
        "icon": "fas fa-key",
        "summary": (
            "Secrets are managed via Replit's secret manager. Live status "
            "for each variable is shown on the Inventory tab. Add only "
            "what you need — most integrations are optional."
        ),
        "steps": [
            {"label": "DATABASE_URL",         "detail": "Auto-set by Replit Postgres. Required."},
            {"label": "PROD_DATABASE_URL",    "detail": "Optional — read-only access to production from dev for debugging."},
            {"label": "SESSION_SECRET",       "detail": "Random 32+ char string for staff session tokens."},
            {"label": "GOOGLE_CLIENT_ID / SECRET", "detail": "For Google OAuth login. Configure via Replit Integrations."},
            {"label": "STRIPE_SECRET_KEY",    "detail": "For Stripe payments. Optional; only needed if VGK4U marketplace billing is on."},
            {"label": "TWILIO_*",             "detail": "Account SID / Auth Token / phone number for SMS dispatch via the Twilio integration."},
            {"label": "REPLITMAIL_API_KEY",   "detail": "Auto-managed by Replit Mail integration for transactional email."},
        ],
    },
    {
        "id": "bootstrap",
        "title": "First-Run Bootstrap",
        "icon": "fas fa-rocket",
        "summary": (
            "Schema and seed data are applied automatically on every "
            "backend startup. The seeders are idempotent — safe to "
            "re-run any time."
        ),
        "steps": [
            {"label": "Schema bootstrap", "detail": "`schema_bootstrap.py` creates / updates all tables and columns."},
            {"label": "Sidebar sync",     "detail": "`sidebar_sync_service.sync_menu_registry_sections()` rebuilds the menu registry from code on every startup."},
            {"label": "B2B Phase-1 seed", "detail": "`platform_b2b_seed.py` creates the first associated company, default departments, and template KRAs."},
            {"label": "SFMS seed",        "detail": "`sfms_seed.run_sfms_seed()` provisions the Tally-28-group chart of accounts, HSN catalog, and pricing config per company."},
            {"label": "Restart backend",  "detail": "Use the workflows panel to restart `FastAPI Backend`; the seeders will run and emit `[DC-*]` log lines reporting what they touched."},
        ],
    },
    {
        "id": "first-admin",
        "title": "Create the First Admin",
        "icon": "fas fa-user-shield",
        "summary": "After bootstrap, set up the first super-admin staff so you can log into the staff portal.",
        "steps": [
            {"label": "Open the DB pane",  "detail": "Use the Replit DB pane or any Postgres client connected via DATABASE_URL."},
            {"label": "Insert/edit staff", "detail": "Update the `staff` row created by the seed (or insert one) — set `is_supreme=true` and `data_companies=NULL` so this user sees everything."},
            {"label": "Set the password",  "detail": "Use `/api/v1/admin/password-reset` or the password-reset utility script in `backend/scripts/`."},
            {"label": "Log in",            "detail": "Visit `/login`, enter the email + password. You should land on the staff dashboard with the full sidebar visible."},
        ],
    },
    {
        "id": "companies",
        "title": "Configure Companies & Departments",
        "icon": "fas fa-building",
        "summary": "Each tenant unit you bill / report against is an `associated_company`. Departments and employees are scoped under it.",
        "steps": [
            {"label": "Companies",   "detail": "Configuration → Companies. Add company name, code, GST, address. Mark `is_active=true` so it appears in DAR / Consolidated."},
            {"label": "Departments", "detail": "Configuration → Departments. Default seed creates Sales, Accounts, Operations, HR — extend as needed."},
            {"label": "Employees",   "detail": "Staff Dashboard → Add Employee. Assign department, role, accessible companies, and (optionally) supreme flag."},
            {"label": "KRA / KPI",   "detail": "KRA Management → set monthly targets per role. The Day Planner and Progress page roll these up."},
        ],
    },
    {
        "id": "integrations",
        "title": "Integrations",
        "icon": "fas fa-plug",
        "summary": (
            "All third-party connectors are added via Replit Integrations. "
            "Live status of each is on the Inventory tab — green = connected, "
            "amber = optional and unset, red = required but missing."
        ),
        "steps": [
            {"label": "Google OAuth",      "detail": "For Google sign-in on the staff portal. Add via Replit → Integrations → Google."},
            {"label": "Replit Mail",       "detail": "For transactional email (password resets, alerts). One-click add."},
            {"label": "Twilio",            "detail": "For SMS dispatch (OTPs, lead alerts). Provide SID/token + verified phone number."},
            {"label": "Stripe",            "detail": "Optional — payments for VGK4U marketplace. Add live or test keys."},
            {"label": "Object Storage",    "detail": "For invoice attachments, KYC documents, member uploads."},
        ],
    },
    {
        "id": "modules",
        "title": "Module Activation",
        "icon": "fas fa-toggle-on",
        "summary": (
            "All modules are visible by default to supreme users. To grant "
            "selective access to staff, use Menu Access Control."
        ),
        "steps": [
            {"label": "Menu Access Control", "detail": "Configuration → Menu Access Control. Pick a staff member; toggle which submenus / pages they see."},
            {"label": "Sidebar Sync",        "detail": "Configuration → Sidebar Sync. Use `Run Sync` if you've just edited menu-master.js or the registry — propagates changes immediately."},
            {"label": "Audit log",           "detail": "Configuration → Audit Logs. Tracks every CRUD on accounts/inventory/payroll modules."},
        ],
    },
    {
        "id": "deploy",
        "title": "Production Deployment",
        "icon": "fas fa-cloud-upload-alt",
        "summary": "Use Replit Deployments to publish a stable production environment with TLS, custom domain, and health checks.",
        "steps": [
            {"label": "Pre-flight",     "detail": "Run all four workflows green; resolve any LSP errors; verify `/health` responds 200."},
            {"label": "Publish",        "detail": "Click `Publish` in Replit. Choose VM (single-container) so backend + frontend share localhost — uses `BACKEND_URL=http://127.0.0.1:8000` automatically."},
            {"label": "Smoke test",     "detail": "Hit `<your-app>.replit.app/login`, log in, open DAR, confirm sidebar renders, run a sample report."},
            {"label": "Custom domain",  "detail": "Replit Deployments → Settings → Custom Domain. Add CNAME / A record at your registrar."},
            {"label": "Production DB",  "detail": "Replit assigns a separate prod DB. Use `backend/scripts/migrate_prod_to_dev.py` if you need to mirror prod for debugging."},
        ],
    },
    {
        "id": "operations",
        "title": "Day-to-Day Operations",
        "icon": "fas fa-tools",
        "summary": "Routine tasks an operator performs after the platform is live.",
        "steps": [
            {"label": "Daily Activity Report", "detail": "Accounts → Consolidated → DAR. Default is `All Companies` aggregated; switch tabs for Daily 10-day grid or Period Comparison snapshots."},
            {"label": "Backups",               "detail": "Replit auto-snapshots the DB. Take a manual SQL dump before any destructive migration: `pg_dump $DATABASE_URL > backup.sql`."},
            {"label": "Restarts",              "detail": "Use the workflow panel to restart any of the four workflows. Backend and Frontend each have a self-restart loop."},
            {"label": "Logs",                  "detail": "Inspect `/tmp/logs/<workflow>_*.log` for the latest run. The DC convention prefixes startup messages with `[DC-*]`."},
            {"label": "Schema changes",        "detail": "Add columns through `schema_bootstrap.py` so they apply on every startup. Never run ad-hoc ALTERs on prod."},
        ],
    },
]

# ---------------------------------------------------------------------------
# 2. Append-only changelog. Newest entry first.
# ---------------------------------------------------------------------------
PLATFORM_CHANGELOG = [
    {
        "date": "2026-05-03",
        "tag": "DC_DAR_004",
        "title": "DAR — All Companies default + Period Comparison + color theming",
        "details": [
            "DAR at `/staff/accounts/DAR` now defaults to All Companies (aggregates across every accessible company; bank names prefixed with company code).",
            "New Period Comparison tab with seven snapshot columns: Today, This Week, Last Week, This Month, Last Month, This FY, Overall.",
            "Daily tab grid switched from business-days-only to last 10 calendar days so today's column is always visible.",
            "Section header banners color-coded per category; columns lightly tinted by time period for fast scanning.",
            "DAR menu entry moved from SFMS submenu to Consolidated submenu under Accounts.",
        ],
    },
    {
        "date": "2026-05-03",
        "tag": "DC_PLATFORM_GUIDE_001",
        "title": "Platform Setup Guide",
        "details": [
            "Embedded as a new `Platform Setup` section inside the existing Staff Guide (`/guide`, `/staffguide`, `/staff/day-planner-guide`).",
            "Standalone page at `/staff/platform-setup-guide` retained as a direct deep-link.",
            "Configuration sidebar entry deep-links to `#sec-platform-setup` anchor.",
            "Inventory tab refreshes from DB + environment on every load.",
        ],
    },
    {
        "date": "2026-05-03",
        "tag": "DC_PLATFORM_GUIDE_002",
        "title": "Tenant Creation Walkthrough + Left-Nav Refactor",
        "details": [
            "Added 'How to Create a New Tenant' — an 11-step end-to-end walkthrough with deep-link buttons to `/login`, `/staff/accounts/companies`, `/staff/departments`, `/staff/employees`, `/staff/accounts/segments`, `/staff/accounts/expense-categories`, `/staff/accounts/pricing`, `/staff/accounts/hsn`, `/rvz/menu-access-config`, `/staff/sidebar-sync`, `/staff/page-registry`, `/staff/accounts/DAR`, `/staff/audit-logs`, `/staff/settings`.",
            "Replaced the horizontal sub-tabs with a left-side menu listing every setup section (Tenant Setup group) plus Live Inventory and Update Log (System group).",
            "Mobile (≤768 px): left-nav collapses behind a hamburger toggle; tapping a menu item closes the drawer automatically.",
            "Step model now supports an optional `links` array of `{label, route}` objects rendered as pill buttons.",
            "Standalone page `/staff/platform-setup-guide` rebuilt to match — same left-nav, hamburger, and link buttons.",
        ],
    },
    {
        "date": "2026-05-03",
        "tag": "DC_SAAS_CONSOLE_001",
        "title": "VGK SaaS console (supreme-only)",
        "details": [
            "New top-level sidebar section `VGK SAAS` (audience: VGK4U) — supreme-only, sits above Configuration.",
            "Moved into VGK SaaS: Companies (now 'Tenant Onboarding'), Signup Categories, Lead Sync, Menu Access Control, Page Registry, Sidebar Sync, Audit Logs, Platform Setup Guide.",
            "Wired previously-orphan pages: `/staff/my-tenant` (All Tenants) and `/staff/b2b-clients` (Platform Clients) — both routed by frontend/server.js.",
            "Public Signup Preview link added (read-only deep-link to `/b2b_signup.html`); the public MNR signup flow itself is untouched.",
            "Tenant-create endpoint `POST /staff-accounts/companies` now returns 403 unless `staff_type == 'VGK4U Supreme'`.",
            "All existing `associated_companies` rows are surfaced as 'Tenant 1 — Existing operations' on the All Tenants page; no DB change.",
            "Tenant-creation walkthrough updated: new Step 0 ('Sign in as VGK4U Supreme') and new verify-step linking to All Tenants + Platform Clients.",
        ],
    },
]

# ---------------------------------------------------------------------------
# 3. Optional / required env-var registry — drives the live status panel.
# ---------------------------------------------------------------------------
ENV_VAR_REGISTRY = [
    {"name": "DATABASE_URL",         "required": True,  "purpose": "Primary PostgreSQL connection."},
    {"name": "PROD_DATABASE_URL",    "required": False, "purpose": "Read-only mirror to prod for debugging."},
    {"name": "SESSION_SECRET",       "required": False, "purpose": "Used to sign staff session tokens. Recommended."},
    {"name": "GOOGLE_CLIENT_ID",     "required": False, "purpose": "Google OAuth (staff sign-in)."},
    {"name": "GOOGLE_CLIENT_SECRET", "required": False, "purpose": "Google OAuth (staff sign-in)."},
    {"name": "TWILIO_ACCOUNT_SID",   "required": False, "purpose": "Twilio SMS — required only if SMS dispatch is enabled."},
    {"name": "TWILIO_AUTH_TOKEN",    "required": False, "purpose": "Twilio SMS auth."},
    {"name": "TWILIO_PHONE_NUMBER",  "required": False, "purpose": "Outbound Twilio number."},
    {"name": "STRIPE_SECRET_KEY",    "required": False, "purpose": "Stripe payments — VGK4U marketplace only."},
    {"name": "REPLITMAIL_API_KEY",   "required": False, "purpose": "Replit Mail transactional email."},
]
