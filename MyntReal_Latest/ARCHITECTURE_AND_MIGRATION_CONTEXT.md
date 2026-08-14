# VGK Network - Architecture & Migration Context

**Last Updated:** August 14, 2026
**Purpose of this Document:** This document serves as the absolute source of truth for the VGK Network software migration project. It is designed to preserve the full context, agenda, and architectural decisions of the project so that any new AI agent, developer, or team member can immediately understand the system state and resume work without needing prior chat history.

---

## 1. Project Overview & Agenda
The VGK Network (MyntReal) is a comprehensive business ecosystem combining Real Estate, Solar Energy, Multi-Level Marketing (MLM), and Vendor Partnerships. 

**The Master Agenda:** 
The primary goal of this project is to achieve **100% parity** with the legacy system while radically upgrading the technology stack. The legacy frontend consisted of over 100+ raw `.html`, `.js`, and `.css` files (running alongside a Python backend). 
The mission is to migrate all legacy frontend UI into a modern, secure, and highly responsive **Next.js (App Router)** application styled with **Tailwind CSS**, while maintaining compatibility with the existing **FastAPI** Python backend.

---

## 2. Technology Stack
*   **Frontend Framework:** Next.js (App Router, React 18)
*   **Styling:** Tailwind CSS (Vanilla CSS in `globals.css` for base styles)
*   **State & Data:** React Context API (Strictly segregated by domain: `StaffAuthContext`, `MemberAuthContext`, `VendorAuthContext`)
*   **Icons & UI:** FontAwesome (via CDN), Chart.js (for analytics)
*   **Backend:** Python FastAPI (Running on `http://127.0.0.1:5000` locally)
*   **Infrastructure Context:** Targeted for deployment on resource-constrained environments (e.g., 1GB RAM AWS EC2).

---

## 3. Key Architectural Decisions
1.  **Strict Route Segregation:** The frontend is strictly divided into distinct portals using Next.js route groups and folder structures to ensure security and clean layouts:
    *   `/app/staff/*` -> Staff & Employee Portal
    *   `/app/member/*` -> VGK Network Members Portal (MLM, Wallet)
    *   `/app/vendor/*` -> External Partner/Vendor Portal
    *   `/app/superadmin/*` -> Supreme Finance & System Admin Portal
2.  **Context-Based Authentication:** Each major portal has its own dedicated React Context (e.g., `StaffAuthContext.tsx`, `MemberAuthContext.tsx`). This prevents cross-contamination of JWT tokens and ensures a staff member cannot accidentally access member routes with their staff token.
3.  **Modern Aesthetic:** The UI design mandate requires a "premium, dynamic, and state-of-the-art" aesthetic. This means heavy use of gradients, interactive hover states, micro-animations, and clean typography, avoiding cliché dashboards.

---

## 4. Completed Work (Phases 1-32)
We have successfully migrated the largest portions of the legacy system into Next.js. **The Staff Portal and the Member Portal are 100% complete on the frontend UI.**

### The Staff Portal (Phases 1-28)
*   **Core Systems:** Accounting ledgers, CRM & Lead Management, Support Ticketing, and the VGK Admin dashboard.
*   **HR & Performance:** Task Kanban boards (`/staff/tasks`), Daily Planners, KRA tracking (`/staff/performance/kra`), and Incentive points (`/staff/hr/incentives`).
*   **Field Tracking:** GPS Location history and Travel Journey logging for expense claims.
*   **Marketing Suite:** A complete Meta Ads integration UI (Dashboard, Campaigns, Creative Studio).
*   **Security:** Staff Profile, 2FA Security, Audit Logs, and NDA/Compliance tracking.

### The Member Portal (Phases 29-32)
*   **Auth & Layout:** Built `MemberAuthContext` and the Member Sidebar layout.
*   **MLM Network:** Built the Direct Referrals list, the Guru Dakshina tracker, and a complex **Visual Genealogy Tree** for Matching pairs (`/member/network/matching`).
*   **Wallets:** Created an E-Wallet ledger and a secure 3-step PIN-authorized withdrawal flow.
*   **Benefits:** Built visual "ticket-style" Coupons, an EV Vehicle Scheme progress tracker, and a National Leaderboard for awards.

---

## 5. Upcoming & Pending Work (Phases 33-36)
The following phases represent the final legacy files (`vendor_*.html`, `superadmin_*.html`, `vgk_finance_supreme.html`) that need to be migrated to hit 100% total completion.

*   **Phase 33: The Vendor App**
    *   `vendor_login.html` -> `/app/(auth)/vendor/login/page.tsx`
    *   `vendor_portal.html` -> `/app/vendor/dashboard/page.tsx`
    *   `vendor_scan.html` -> `/app/vendor/scan/page.tsx`
*   **Phase 34: Super Admin Controls**
    *   Migrate global configs, placement approvals, and system health checks to `/app/superadmin/*`.
*   **Phase 35: Supreme Finance Module**
    *   Migrate the top-level company revenue, cash income, and expense ledgers used by directors.
*   **Phase 36: Final Cleanup**
    *   Migrate remaining public landing pages and testing scaffolds.

---

## 6. How to Resume Work (Instructions for AI Agents)
If you are an AI reading this document at the start of a new session:
1.  **Acknowledge Context:** You are operating in the `MyntReal_Latest` directory. The legacy HTML files are in `frontend/`. The new Next.js app is in `frontend-next/`.
2.  **Check Progress:** Review `task.md` and `walkthrough.md` in the `.gemini/antigravity/brain/` artifacts directory to see exactly which phase was last completed.
3.  **Continue Execution:** Proceed with the next uncompleted phase listed in Section 5 of this document, utilizing `write_to_file` to generate the React components. Ensure you follow the premium aesthetic guidelines (Tailwind) and strict route structures.
