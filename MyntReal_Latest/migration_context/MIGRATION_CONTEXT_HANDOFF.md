# MIGRATION CONTEXT & IN-DEPTH TECHNICAL HANDOFF

**To the Next Agent:** 
This is a highly detailed, intensive handoff document. You are taking over a massive, production-grade application for a complete frontend architecture migration. You must read every single detail here to understand the exact mechanics of the current system, the strict constraints, the precise bug fixes we recently applied, and the granular step-by-step migration strategy.

---

## 1. IN-DEPTH ARCHITECTURAL ANALYSIS

### A. The Current Frontend (The Target for Replacement)
The current frontend is highly unconventional and messy for a project of this scale. It relies on a massive custom Node.js server (`frontend/server.js` - over 30,000 lines long).
*   **Routing & Serving:** The Node server acts as a manual HTTP router. It intercepts browser requests and serves raw, plain HTML, CSS, and Vanilla JS files physically located in the `frontend/templates/` directory.
*   **Proxying Mechanics:** The `server.js` file also acts as a reverse proxy. Any request hitting the frontend starting with `/api/v1/*` is intercepted, sanitized (with custom XSS/JS escaping), and manually proxied to the Python backend over localhost.
*   **The Problem:** There is no component reusability. State management is non-existent (relying on raw DOM manipulation). It is prone to UI/UX inconsistencies and is extremely difficult to scale. 
*   **Current Dependencies:** There is a `frontend/package.json` that shows a dependency on `next@14.2.23` and `tailwindcss`, but they are not being fully utilized as a framework.

### B. The Current Backend (DO NOT CHANGE)
*   **Framework:** **FastAPI (Python 3.11)**.
*   **Execution:** Runs on `http://127.0.0.1:8000` via Uvicorn.
*   **Functionality:** Handles all core business logic, database ORM (SQLAlchemy), JWT authentication, and heavy AI integrations (using `google-genai` / Gemini models).
*   **Verdict:** The backend is perfect. Your migration task is **strictly isolated to the frontend**.

### C. The Current AWS Infrastructure (Strict Constraint)
You are restricted to using ONLY the following AWS services. Do not suggest third-party hosting (Vercel, Heroku, etc.).
*   **Database:** Amazon RDS (PostgreSQL).
*   **Storage:** Amazon S3 (for media, documents, and generated `.zip` deployment artifacts).
*   **Hosting:** AWS Elastic Beanstalk (EB).
    *   **Containerization:** The application runs on a Single Docker Container environment in EB. The `Dockerfile` at the project root builds both Python and Node environments.
    *   **Boot Sequence:** The `start.sh` script runs `uvicorn` (FastAPI) in the background (port 8000) and then runs `node server.js` in the foreground (port 5000). EB maps port 80 to 5000.

---

## 2. RECENT CRITICAL BUG FIXES (PRESERVE THESE)
In the previous session, we stabilized the production environment. When rewriting the frontend and Docker configurations, **you must ensure these fixes remain intact**:

1.  **AWS EBS Node.js Native Addon Crash (`Dockerfile`):**
    *   *Issue:* Next.js/Node on Elastic Beanstalk was crashing with `GLIBCXX_3.4.29 not found`.
    *   *Fix:* We injected `libstdc++6` and `libgcc-s1` into the `apt-get install` step in the `Dockerfile`.
2.  **Protobuf Conflict (`backend/requirements.txt`):**
    *   *Issue:* `google-generativeai` and `google-ai-generativelanguage` were clashing over `protobuf` versions, causing build failures on AWS.
    *   *Fix:* We strictly pinned the protobuf dependency to resolve the clash.
3.  **AI Chat 500 Internal Server Error (`backend/app/services/ai_marketing_pro_service.py`):**
    *   *Issue:* The Gemini model was hitting its `max_turns` limit for function calling (fetching Facebook Ads data recursively). When it hit the limit, `google-genai` returned `response.text` as `None`, which crashed the FastAPI Pydantic schema validation, resulting in a 500 error.
    *   *Fix:* Added explicit `None` checking: `final_text = response.text if response.text else "I gathered the data but reached my limit..."`
4.  **SSRF Security Vulnerability (`frontend/server.js`):**
    *   *Issue:* Automated scanners were hitting `/api/proxy?url=169.254.169.254` attempting to steal AWS EC2 metadata.
    *   *Fix:* We implemented an SSRF blocklist rejecting IP lookups for localhost and `169.254.x.x`. (When you rewrite the proxy in Next.js, you must implement similar SSRF protections).
5.  **Deployment Packaging (`build_zip_full.py`):**
    *   *Issue:* The zip script was creating messy duplicate files.
    *   *Fix:* The script now directly overwrites `MyntReal_AWS_Deploy.zip`, cleans up legacy zip files, and dynamically injects `GEMINI_API_KEY` and Meta App secrets into `.ebextensions/01_env.config` from the local `.env`.

---

## 3. THE MIGRATION GOAL: NEXT.JS + TAILWIND CSS
The objective is to replace `server.js` and `frontend/templates/` with a modern **Next.js (App Router or Pages Router, choose the most stable for this scale)** application, heavily utilizing **Tailwind CSS** for a massive UI/UX overhaul.

### UI/UX Mandate
The user explicitly stated the current UI is "just okay" and wants it to be highly professional, clean, and completely free of clutter. You must prioritize modern UI/UX principles:
*   **Enterprise Aesthetic:** The design MUST emulate top-tier enterprise software (e.g., Salesforce, AWS Console, ServiceNow, Zoho CRM).
*   **Minimalist & Neutral:** Strictly avoid unnecessary colors, heavy gradients, or flashy elements. Stick to neutral palettes (whites, light greys, slate) with highly intentional, subtle accent colors for primary actions.
*   **Component Structure:** Break down massive HTML files into small, reusable React components (e.g., `<Sidebar />`, `<DataGrid />`, `<MetricCard />`).
*   **Flawless Execution:** The UI must be implemented perfectly without bugs, visual glitches, alignment issues, or responsive layout breaks. Use Tailwind utility classes exclusively to maintain absolute consistency.

---

## 4. THE ZERO-DOWNTIME AWS DEPLOYMENT STRATEGY (BLUE/GREEN)
The user requires that users experience absolutely zero downtime and zero data loss during this massive architectural shift. You will orchestrate a **Blue/Green Deployment** on AWS Elastic Beanstalk.

**The Step-by-Step Swap Mechanics:**
1.  **Environment A (The "Blue" Live Environment):** This is the current EB environment serving live traffic, connected to the production RDS and S3.
2.  **Build the "Green" Deployment Zip:** We will build the new Next.js codebase. We will run `build_zip_full.py` to package it.
3.  **Spin Up Environment B:** In the AWS Console, the user will create a *new* Elastic Beanstalk environment within the same Application.
4.  **Deploy & Attach:** The user uploads the new `.zip` to Environment B. Environment B's `.ebextensions` will automatically connect it to the *exact same* production RDS and S3 buckets. Because they share the database, data is preserved perfectly.
5.  **Private QA Testing:** AWS provides a temporary URL (e.g., `env-b.elasticbeanstalk.com`). The user will use this to thoroughly test the new Next.js UI privately.
6.  **The "Magic Swap" (DNS CNAME Swap):** Once approved, the user clicks "Swap Environment URLs" in the AWS EB console. AWS Route 53 instantly swaps the CNAME records at the DNS level. The live domain immediately routes traffic to Environment B. Environment A is safely spun down.

---

## 5. DEVELOPMENT WORKFLOW & STRICT ISOLATION
The user is highly concerned about the new migration accidentally breaking the live site. You must strictly adhere to these isolation rules:

1.  **Separate Folder:** All new Next.js code must be placed in a completely separate folder (e.g., `frontend-next/`).
2.  **No Disruption to Current App:** The current HTML/JS/CSS frontend and Node `server.js` must remain completely untouched and runnable.
3.  **Port Separation:** When running locally, the new Next.js app will run on port `3000`, while the old Node server continues to run on port `5000`. The FastAPI backend remains on port `8000`. This allows side-by-side testing.
4.  **Zip Script Exclusions:** The `build_zip_full.py` script has already been updated to explicitly EXCLUDE the `frontend-next/` directory. This guarantees that if the user needs to push a hotfix to production using the old codebase, the unfinished Next.js code will NOT be deployed.
5.  **GitHub Iteration:** The migration will be done incrementally. We will write code, test it locally on port 3000, and push/pull to GitHub. **Do NOT update the deployment `.zip` script to include Next.js until the entire frontend is 100% finished and the user explicitly gives the green light for deployment.**

---

## 6. YOUR EXACT IMPLEMENTATION PHASES
When you (the new agent) begin, you must execute the migration in these exact, systematic phases to manage the complexity of this massive application.

### PHASE 1: Initialization & Design System
*   Set up the Next.js directory structure safely without breaking the current `server.js` (until we are ready to swap).
*   Initialize `tailwind.config.js` and global CSS variables for the new professional UI/UX design system.
*   Create the core layout shell (Navigation, Sidebar, Authentication wrappers).

### PHASE 2: API Proxying & Backend Connection
*   In the new Next.js app, configure `next.config.js` rewrites to securely proxy `/api/v1/:path*` to `http://127.0.0.1:8000/:path*`.
*   Ensure this new proxy configuration replicates the SSRF protections we built into the old `server.js`.

### PHASE 3: Iterative Component Translation (The Heavy Lifting & 100% COVERAGE MANDATE)
*   Systematically translate the old `frontend/templates/*.html` files into React components.
*   Focus heavily on replacing manual DOM manipulation (e.g., `document.getElementById`) with React State (`useState`, `useEffect`) and proper data fetching hooks.
*   **CRITICAL 100% COVERAGE MANDATE:** The user is highly concerned that due to the massive scale of this app, you might miss a page, a feature, or a specific piece of JavaScript logic. **You are strictly forbidden from missing anything.** Before you start converting pages, you must map out *every single* HTML page, CSS rule, and JavaScript function from the old frontend. Every single feature must be accounted for, migrated, and upgraded to Next.js. If you miss a piece of code, it will have a massive negative impact on production. Create a checklist if you must, but ensure 100% feature parity.

### PHASE 4: Containerization & Deployment Handoff
*   Update the `Dockerfile`. The new Dockerfile must execute `npm run build` for Next.js, and the `start.sh` script must be updated to boot FastAPI and `npm start` (Next.js production server) instead of `node server.js`.
*   Run the deployment zip script and guide the user through the AWS Blue/Green URL swap.

**Agent Acknowledgment:** In your very first reply to the user, state that you have read `MIGRATION_CONTEXT_HANDOFF.md`, you understand the strict AWS constraints, the Blue/Green deployment strategy, and you are ready to begin Phase 1.
