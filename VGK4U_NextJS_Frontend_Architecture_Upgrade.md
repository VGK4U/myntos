# VGK4U — Next.js Frontend Architecture Upgrade, 100% Functional Parity & Premium Enterprise CRM UX

## ROLE

Act as the principal software architect, senior frontend architect, backend integration architect, UX/UI architect, DevOps engineer, QA engineer, security engineer, and migration specialist responsible for the VGK4U frontend modernization.

Treat this as a large-scale enterprise CRM modernization, not a normal frontend rewrite.

You have the complete application context, source code, backend, database structure, current frontend, existing Next.js work, integrations, configuration, deployment setup, and related project files.

Use actual application evidence for every decision.

**Do not hallucinate, guess, or invent behavior.**

If something is unknown, investigate it first. If it still cannot be established, explicitly tell me and ask me.

---

# 1. CURRENT APPLICATION CONTEXT

The current architecture is approximately:

Frontend:
HTML / CSS / JavaScript
(Node.js involvement is uncertain and MUST be investigated)

Backend:
FastAPI / Python

Database:
PostgreSQL / AWS RDS

Storage:
AWS S3 + potentially legacy local backend storage

Hosting:
AWS Elastic Beanstalk + Docker

Integrations:
Razorpay
WhatsApp API
and any additional integrations discovered from the actual codebase

The frontend migration to Next.js has already partially started.

The current Next.js version is not yet the production frontend.

The old frontend is still the public application.

The Next.js version is currently maintained through GitHub and is not yet included in the production AWS Elastic Beanstalk deployment.

The goal is to continue improving the Next.js version until it is a complete, verified, premium replacement.

Only after I personally decide that it is ready should the production frontend be switched.

---

# 2. PRODUCTION SAFETY — ABSOLUTE

The existing public application is the GOLDEN REFERENCE and must remain operational.

The new Next.js application is a PARALLEL DEVELOPMENT/REPLACEMENT APPLICATION.

Do not damage the existing production system.

Never:
- break production
- modify production behavior without explicit approval
- prematurely switch production
- delete production data
- change production authentication behavior
- change production authorization behavior
- remove APIs because the new frontend does not currently use them
- remove old pages before parity is proven
- perform destructive changes without approval
- assume build success means completion

The old application must continue serving users throughout the migration.

---

# 3. PRIMARY OBJECTIVE

Create a production-grade Next.js frontend that is:

## Functionally
100% equivalent to the existing application.

## Architecturally
Modular, scalable, maintainable, clean, secure, and performant.

## UX/UI
Premium, professional, rich-looking, intuitive, easy to use, highly polished, and suitable for an enterprise CRM.

The final application should not look like a basic HTML-to-React conversion.

It should feel like a professionally designed enterprise product.

---

# 4. FUNCTIONAL PARITY IS NON-NEGOTIABLE

A page rendering is NOT parity.

A route existing is NOT parity.

A successful build is NOT parity.

A login screen working is NOT authentication parity.

A button appearing is NOT functionality parity.

A table appearing is NOT feature parity.

Every page/feature must preserve:

- structure
- content
- real data
- API connectivity
- authentication
- authorization
- interactions
- forms
- validation
- loading states
- error states
- empty states
- modals
- search
- filtering
- sorting
- pagination
- navigation
- data flow
- responsive behavior
- role-specific behavior
- business logic

---

# 5. PHASE 0 — DEEP FORENSIC AUDIT ONLY

Before writing or changing significant code:

**STOP AND AUDIT.**

The audit must be extremely comprehensive.

Do not inspect only obvious files.

Understand the entire application from:

User
→ Authentication
→ Frontend
→ Middleware
→ API
→ FastAPI
→ Business Logic
→ RDS/S3/External APIs
→ Response
→ Frontend state
→ UI
→ Cross-page navigation/data flow

The audit must be based on actual code and configuration.

---

# 6. VERIFY THE CURRENT FRONTEND ARCHITECTURE

Determine exactly:

- how HTML is structured
- how CSS is structured
- how JavaScript is structured
- whether Node.js is actually part of the frontend runtime
- whether Node.js is only build/package tooling
- whether there is a Node server
- package.json
- build process
- static assets
- routing
- templates
- frontend services
- state management
- API calls
- authentication
- authorization
- middleware
- modals
- forms
- tables
- cards
- chats
- search
- filters
- dashboards
- notifications
- uploads
- downloads
- payments
- external integrations

Do not assume Node.js's role.

Prove it from the application.

---

# 7. DISCOVER EVERY PAGE — 100% COVERAGE MANDATE

Start from the home page and systematically discover the entire application.

Do not depend only on a manually supplied list.

Find pages through:

- navbar
- sidebar
- navigation menus
- dropdowns
- buttons
- links
- redirects
- JavaScript navigation
- route definitions
- templates
- source references
- authentication portals
- role-based navigation
- backend route definitions
- workflows
- modals/drawers that expose additional pages
- dynamic navigation

The objective is:

**MISS ZERO PAGES.**

Hidden pages, role-specific pages, secondary pages, workflow pages, and pages behind authentication must be included.

---

# 8. COMPLETE APPLICATION INVENTORY

Create and maintain a complete inventory containing for every route/page:

- route
- page name
- purpose
- roles
- authentication requirement
- authorization requirements
- components
- API endpoints
- database entities
- S3/storage dependencies
- external integrations
- forms
- tables
- search
- filters
- pagination
- modals
- drawers
- actions
- navigation destinations
- loading states
- error states
- empty states
- existing assets
- business rules
- old implementation status
- Next.js implementation status
- verification status

Maintain this throughout the migration.

---

# 9. MIGRATION COVERAGE MATRIX

Track every page and feature:

NOT STARTED
→ AUDITED
→ ARCHITECTURE MAPPED
→ IMPLEMENTED
→ API CONNECTED
→ AUTH VERIFIED
→ ROLE VERIFIED
→ DATA VERIFIED
→ INTERACTION VERIFIED
→ VISUAL VERIFIED
→ REGRESSION TESTED
→ PRODUCTION-READY

Do not mark a page complete simply because it renders.

---

# 10. EXISTING NEXT.JS WORK — A + B STRATEGY

The Next.js migration has already partially been done.

Do NOT throw away the existing Next.js implementation automatically.

Do NOT assume it is correct either.

Use this A + B strategy.

## A — AUDIT AND REUSE

Deeply inspect every existing Next.js:

- page
- route
- component
- layout
- hook
- API service
- utility
- authentication implementation
- middleware
- state management
- styling
- design-system component
- data-fetching logic
- integration
- configuration

Determine whether it is technically sound.

If it is correct, reusable, secure, maintainable, properly integrated with FastAPI, and compatible with the target architecture:

**KEEP AND REUSE IT.**

Do not rewrite good code unnecessarily.

## B — REFACTOR OR REBUILD

If existing Next.js code is:

- incomplete
- a skeleton
- hardcoded
- mock-data driven
- incorrectly connected
- poorly structured
- duplicated
- tightly coupled
- insecure
- missing functionality
- inconsistent with the old application
- incompatible with the target architecture
- difficult to maintain
- likely to cause future issues

then:

**REFACTOR IT OR REBUILD THAT PART.**

Reuse valuable pieces where practical.

Decision process:

Existing Next.js code
→ Deep audit
→ Correct/reusable?
YES → KEEP
NO → REFACTOR / REBUILD

Evaluate:
- correctness
- parity
- architecture
- maintainability
- security
- performance
- accessibility
- integration quality
- design-system consistency
- FastAPI compatibility
- authentication/authorization compatibility
- scalability

The objective is NOT to maximize reused code.

The objective is the highest-quality production-grade result.

Do not restart from zero unless evidence shows that doing so is safer and more efficient.

Do not keep flawed code merely because it already exists.

Create an evidence-based table:

Existing Next.js Area | Current State | Decision | Reason

---

# 11. AUDIT WHY THE CURRENT NEXT.JS VERSION LOOKS LIKE A SKELETON

The current Next.js version may display little or no real data, previous structure, or functionality.

Do not assume this is simply a UI issue.

Determine whether the cause is:

- missing routes
- missing components
- missing API wiring
- incorrect API URLs
- missing environment variables
- authentication failure
- authorization failure
- middleware failure
- data-fetching failure
- mocked data
- incomplete migration
- incorrect backend contracts
- state-management problems
- rendering problems
- missing assets
- incomplete business logic
- other issues

Trace the issue to root cause.

Do not simply make the UI look populated with fake data.

---

# 12. FASTAPI BACKEND INTEGRATION

The FastAPI backend remains a critical part of the system.

The target should generally be:

Next.js
→ FastAPI
→ PostgreSQL / S3 / External APIs

unless the audit proves another approach is materially safer/better.

Audit every frontend/API dependency.

For every API determine:

- endpoint
- method
- request
- response
- authentication
- authorization
- parameters
- validation
- pagination
- filtering
- sorting
- errors
- side effects
- file handling
- database dependencies

Do not create fake frontend data where real backend data exists.

Do not rewrite backend logic unnecessarily.

---

# 13. AUTHENTICATION AND AUTHORIZATION — EXACT PRESERVATION

This is a HARD REQUIREMENT.

The new frontend must preserve the existing authentication/authorization behavior EXACTLY.

Preserve:

- staff login
- member login
- administrator login
- every other login discovered
- sessions
- cookies
- tokens
- refresh behavior
- token expiration
- redirects
- protected pages
- role checks
- permissions
- unauthorized behavior
- authentication errors
- authorization errors
- session persistence
- session expiry
- role-specific navigation
- role-specific data
- role-specific actions

Do NOT simplify or replace authentication merely because Next.js makes it convenient.

Do NOT change authentication architecture without strong evidence and explicit approval.

Create a real matrix:

Role | Login | Accessible Routes | Permissions | Redirects | APIs | Special Rules

Test every role.

A successful login for one user is not enough.

---

# 14. MIDDLEWARE AND SECURITY

Audit and preserve:

- authentication middleware
- authorization middleware
- route protection
- token validation
- session handling
- role checks
- permission checks
- redirects
- backend security assumptions
- frontend/backend trust boundaries

Do not move security responsibilities into the frontend simply because it is convenient.

The frontend must not bypass FastAPI authorization.

---

# 15. DATA FLOW AND CROSS-PAGE CONNECTIVITY

The application is large and contains interconnected pages.

Map important flows such as:

Page A
→ User action
→ API
→ Database update
→ Page B
→ Updated data

Also:

Create
→ Database
→ Dashboard
→ Statistics
→ Lists

Upload
→ FastAPI
→ S3
→ Database reference
→ Document listing
→ Preview/download

Payment
→ Razorpay
→ Backend
→ Database
→ Frontend state

WhatsApp
→ Backend/integration
→ Result/status
→ Frontend

Discover all such flows from the actual codebase.

Do not create visually correct but isolated pages.

---

# 16. DATABASE / RDS

PostgreSQL on AWS RDS is existing infrastructure.

Do not unnecessarily change the schema.

Understand:

- tables
- relationships
- important entities
- foreign keys
- API/database mappings
- business rules
- dependencies

The frontend must use real application data.

No fake/hardcoded data may remain in production-ready functionality unless it is genuinely static.

---

# 17. S3 / FILE INTEGRATION

Audit how the current frontend interacts with files.

Determine exactly whether files are coming from:

- S3
- backend/storage/
- another filesystem
- another service
- generated dynamically

The frontend migration must not break:

- uploads
- previews
- downloads
- replacements
- deletions
- document lists
- signatures
- stamps
- receipts
- PDFs
- images
- generated documents

The separate S3 architecture task should establish S3 as the persistent storage layer if the audit confirms that is appropriate.

The frontend must integrate with the resulting backend/API/S3 architecture safely.

---

# 18. HOME PAGE — START HERE

Deeply inspect the existing home page.

Identify:

- navbar
- all existing navigation elements
- hero section
- existing hero image
- bottom cards
- statistics
- CTAs
- sections
- footer
- dynamic content
- authenticated content
- conditional content
- links
- interactions
- responsive behavior

Do not create a generic replacement.

Explore the actual application and preserve all meaningful content/functionality.

Then substantially improve its UI/UX.

---

# 19. PREMIUM ENTERPRISE CRM UI/UX

The target UX should be comparable in quality and usability to modern enterprise products such as:

- ServiceNow
- Salesforce
- AWS
- Microsoft Azure
- Google Cloud

Use them as UX/design-quality references, not as templates to copy.

The application may have many components and large amounts of information on one page.

The UI must be:

- professional
- premium
- rich-looking
- clean
- easy to understand
- intuitive
- information-dense without being confusing
- visually consistent
- fast to navigate
- responsive

Use principles such as:

- strong hierarchy
- excellent spacing
- polished typography
- restrained color usage
- clear grouping
- clean grids
- sophisticated cards
- readable tables
- meaningful status indicators
- contextual actions
- progressive disclosure
- tabs
- drawers
- modals
- filters
- breadcrumbs
- sticky headers where useful
- command/search patterns where genuinely useful
- clear empty states
- excellent loading states
- clear error states

Do not make every element oversized merely to look modern.

CRM interfaces often need high information density.

Optimize for clarity and efficiency.

---

# 20. DESIGN SYSTEM

Build one coherent reusable design system.

Create reusable patterns/components for:

- navbar
- sidebar
- page headers
- breadcrumbs
- cards
- tables
- filters
- search
- forms
- inputs
- selects
- date pickers
- buttons
- badges
- statuses
- dialogs
- drawers
- tabs
- dropdowns
- tooltips
- notifications
- skeletons
- loading
- empty states
- errors
- pagination
- charts
- file upload
- file preview
- confirmation dialogs

Establish consistency for:

- typography
- spacing
- colors
- radii
- shadows
- borders
- interaction states
- accessibility

Do not build every page as a separate visual system.

---

# 21. MODULAR NEXT.JS ARCHITECTURE

Design the Next.js architecture for a large CRM.

Consider appropriate separation such as:

app/
components/
features/
services/
lib/
hooks/
types/
utils/
styles/

But do not blindly impose this structure.

Use architecture based on the actual project.

Avoid:

- giant components
- duplicated logic
- duplicated API calls
- uncontrolled global state
- unnecessary client components
- unnecessary server complexity
- tight coupling
- page-specific copies of common components

Use appropriate Next.js rendering and data-fetching strategies based on actual requirements.

---

# 22. RESPONSIVE DESIGN

Support:

- desktop
- laptop
- tablet
- mobile

Design intentionally for each viewport.

Do not destroy CRM information density merely to make everything look like a mobile card layout.

---

# 23. ACCESSIBILITY

Include:

- keyboard navigation
- focus states
- semantic HTML
- labels
- contrast
- screen-reader compatibility
- accessible tables
- accessible modals
- meaningful buttons
- accessible navigation
- understandable form errors

---

# 24. PERFORMANCE

Audit:

- bundle size
- client/server boundaries
- API request duplication
- rendering strategy
- caching
- image optimization
- lazy loading
- code splitting
- large tables
- expensive components
- unnecessary re-renders

Use evidence, not assumptions.

---

# 25. LOADING / ERROR / EMPTY / SUCCESS STATES

Every important data-driven screen must handle:

Loading
→ meaningful skeleton/progress

Empty
→ clear explanation + useful action

Error
→ understandable message + recovery

Success
→ appropriate confirmation

Do not allow blank screens to masquerade as completed pages.

---

# 26. ASSETS

Preserve and correctly reuse existing:

- hero images
- logos
- icons
- backgrounds
- illustrations
- banners
- avatars
- document previews
- other important visual assets

Do not replace important existing assets with random placeholders.

---

# 27. INTEGRATIONS

Audit and preserve all frontend-related integration behavior, including:

- Razorpay
- WhatsApp API
- S3
- RDS
- authentication systems
- notifications
- email
- webhooks
- external APIs
- background services
- any other integration discovered

Do not assume the list is complete.

---

# 28. TESTING

Test:

### Pages
Every discovered route.

### Roles
Every discovered role.

### Authentication
Every authentication state.

### APIs
Every frontend-used endpoint.

### Data
Real representative application data.

### User interactions
Every important action.

### Forms
Validation, submission, success, failure.

### Files
Upload, view, preview, download, replace, delete.

### Integrations
Razorpay, WhatsApp, S3 and all discovered integrations.

### Navigation
Every important path.

### Responsive
Desktop/tablet/mobile.

### Regression
Compare against the existing production reference.

---

# 29. PAGE-BY-PAGE PARITY + IMPROVEMENT

For each page:

1. Understand the old page.
2. Inventory every visible and hidden feature.
3. Trace all APIs.
4. Trace all data.
5. Trace all role behavior.
6. Reproduce functionality.
7. Connect real data.
8. Test interactions.
9. Validate cross-page data flow.
10. Improve UI/UX.
11. Test responsive behavior.
12. Verify against the migration matrix.

The target is:

**100% functional parity + substantially improved experience.**

---

# 30. NO PREMATURE CLEANUP

Do not delete old:

- pages
- components
- APIs
- assets
- authentication logic
- configurations
- backend functionality

just because the Next.js version currently does not use them.

Deletion requires:

1. dependency analysis
2. parity verification
3. confirmation of no remaining dependency
4. backup where appropriate
5. explicit approval when destructive

---

# 31. BUSINESS LOGIC

Do not silently "fix" unusual behavior.

First determine whether it is intentional.

If something appears wrong:

Existing behavior
→ evidence
→ possible intended purpose
→ possible bug
→ recommendation

Ask me before changing business behavior when necessary.

---

# 32. 100% COMPLETION REQUIREMENT

Never declare the project "100% complete" merely because:

- build succeeds
- application opens
- routes exist
- UI renders
- a login works
- a few API calls work

Before declaring completion provide actual verified numbers:

Total pages discovered
Total pages migrated
Total pages verified

Total API dependencies
Total API dependencies verified

Total roles
Total roles verified

Total authentication flows
Total authentication flows verified

Total major workflows
Total workflows verified

Total integrations
Total integrations verified

Total known gaps

If any significant gap remains:

**DO NOT CALL IT 100% COMPLETE.**

---

# 33. VISUAL PARITY + VISUAL MODERNIZATION

For every page:

Step 1: understand existing page
Step 2: preserve functional behavior
Step 3: connect real data
Step 4: verify interactions
Step 5: improve UI/UX

The goal is not to make the new version visually identical.

The goal is:

**Preserve 100% of functionality and information while substantially improving usability, clarity, polish, and visual quality.**

---

# 34. DEVELOPMENT PHASES

Recommended:

Phase 1 — Deep forensic audit
Phase 2 — Complete application map
Phase 3 — Current vs target architecture
Phase 4 — Existing Next.js A+B audit
Phase 5 — Design system
Phase 6 — Home page
Phase 7 — Authentication/authorization
Phase 8 — Core shared infrastructure
Phase 9 — Page-by-page migration
Phase 10 — API/data-flow integration
Phase 11 — File/S3 integration
Phase 12 — Role-based validation
Phase 13 — Responsive/accessibility
Phase 14 — Performance
Phase 15 — Full regression testing
Phase 16 — Production readiness
Phase 17 — Final approval gate
Phase 18 — Only then consider production switchover

Adapt the order if actual dependencies require a safer sequence.

---

# 35. AFTER EACH MAJOR PHASE

Report:

- what was discovered
- what changed
- what remains
- what was verified
- what failed
- what is uncertain
- what you need from me
- whether production remains untouched

Do not hide issues to make progress look better.

---

# 36. QUESTIONS / INFORMATION FROM ME

Ask me whenever genuinely necessary for:

- credentials
- environment variables
- access
- AWS configuration
- business clarification
- intended behavior
- UX preference
- production approval
- destructive-operation approval
- migration approval
- domain/configuration information

But investigate the codebase first.

Do not ask me for information you can reliably derive yourself.

---

# 37. PRODUCTION SWITCHOVER GATE

Do not replace the public frontend until ALL are verified:

- 100% route coverage
- 100% critical feature coverage
- authentication parity
- authorization parity
- role behavior
- API integration
- database/data flow
- S3/file behavior
- Razorpay
- WhatsApp
- all major workflows
- responsive behavior
- accessibility review
- performance review
- security review
- error states
- production configuration
- rollback plan
- no critical known issues
- no unexplained missing functionality

Then produce a Production Readiness Report.

Do not switch production automatically.

---

# 38. FINAL TARGET ARCHITECTURE

The likely target is:

USERS
 ↓
NEXT.JS FRONTEND
 ↓
FASTAPI BACKEND
 ↓
RDS / S3 / EXTERNAL INTEGRATIONS

Conceptually:

Elastic Beanstalk → application/runtime
RDS → structured database data
S3 → persistent files/documents/media
Next.js → modern frontend
FastAPI → backend/business/API/security layer

But validate this against the actual application.

---

# 39. FIRST ACTION — DO NOT CODE YET

Start with the DEEP FORENSIC AUDIT ONLY.

Produce:

1. Current frontend architecture
2. Whether Node.js is actually part of frontend runtime
3. Current Next.js migration status
4. Complete page/route inventory
5. Complete component/functionality inventory
6. Authentication architecture
7. Authorization/roles/permissions
8. FastAPI API inventory
9. Frontend ↔ backend data flow
10. Database dependencies
11. S3/storage dependencies
12. External integrations
13. Deployment architecture
14. Production vs development separation
15. Existing assets
16. Current UI/UX structure
17. Missing functionality in Next.js
18. Existing technical debt
19. Risks
20. Recommended target architecture
21. Recommended implementation sequence
22. What you need from me

Then create:

A. Complete application map
B. Migration coverage matrix
C. Current vs target architecture
D. Risk register
E. Implementation plan
F. Questions requiring my decision

FINAL INSTRUCTION

Do not tell me the project is 100% complete because the current Next.js application builds, runs, or displays a UI.

The previous migration may contain significant gaps.

Verify the actual state.

USE EVIDENCE, NOT ASSUMPTIONS.

PRESERVE PRODUCTION.
MISS NOTHING.
DO NOT LOSE DATA.
DO NOT LOSE FUNCTIONALITY.
DO NOT CHANGE AUTHENTICATION/AUTHORIZATION BEHAVIOR.
DO NOT INTRODUCE REGRESSIONS.
DO NOT MAKE DESTRUCTIVE CHANGES WITHOUT APPROVAL.
DO NOT BUILD A VISUAL SKELETON AND CALL IT COMPLETE.

Build a genuine production-grade Next.js replacement.

Start with the deep forensic audit only.

Do not modify the application significantly until the audit, coverage map, risks, target architecture, and migration plan are established and any genuinely required information has been requested from me.
