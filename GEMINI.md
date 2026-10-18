# VGK4U SYSTEM RULES - ENFORCE AT ALL TIMES

Strictly obey the following deployment and architecture rules to prevent AWS production server crashes and ensure cross-platform compatibility across Windows, macOS, and Linux (AWS Elastic Beanstalk).

---

### 1. NO ABSOLUTE PATHS
- **Rule**: NEVER hardcode local machine paths (e.g., `/Users/name/...`, `C:/...`, `/home/...`) into the code.
- **Context**: The codebase runs on **macOS/Windows** (local development) and **Linux** (AWS Elastic Beanstalk). Hardcoded absolute paths cause crashes and permission errors across environments.
- **Standard**: Always dynamically resolve paths relative to the current file:
  - **Python**: Use `os.path.abspath(os.path.join(os.path.dirname(__file__), "..."))` or `pathlib.Path(__file__).resolve().parent`
  - **Node.js**: Use `path.join(__dirname, "...")`

---

### 2. DOCKERFILE SYNCHRONIZATION
- **Rule**: If creating a new `package.json` (Node.js) or `requirements.txt` (Python) in any subdirectory, you MUST explicitly update the root `Dockerfile` and build scripts.
- **Standard**:
  - Add a `COPY` instruction for the manifest file.
  - Add a `RUN npm install` or `RUN pip install` instruction for that specific directory so AWS Elastic Beanstalk / Docker builds install all dependencies.

---

### 3. SSR SAFETY (NEXT.JS / NODE.JS)
- **Rule**: Never use browser-specific global objects (`window`, `document`, `localStorage`, `sessionStorage`, `navigator`) in the global scope of a file.
- **Standard**: Always wrap them in safe environment checks or `useEffect` hooks:
  ```typescript
  if (typeof window !== 'undefined') {
    // safe browser-only execution
  }
  ```

---

### 4. MEMORY AWARENESS & OOM PREVENTION
- **Rule**: The AWS production server is a monolithic instance with limited RAM. Do not silently bundle memory-heavy background processes (like Headless Chrome/Puppeteer bots, heavy AI pipelines, or unthrottled queues) into the main API startup script without warning the user about Out-Of-Memory (OOM) risks.

---

### 5. SINGLE APPLICATION STRUCTURE & FULL PLATFORM PARITY (WEB + /mobile + ANDROID + iOS)
- **Rule**: MyntOS is ONE application with FOUR delivery representations:
  1. Main Web Application
  2. `/mobile` Mobile Web Application
  3. Native Android Application (Capacitor)
  4. Native iPhone/iOS Application (Capacitor)
- **Standard**:
  - **No Accidental Divergence**: Business logic, features, workflows, permissions, API contracts, data models, and validation rules MUST remain consistent across all 4 representations.
  - **Single Implementation Pass**: Any feature or bug fix applicable across platforms must update Web, `/mobile`, Android, and iOS in the SAME pass. No "implement web now, mobile later".
  - **Mobile Synchronization Pipeline**: Every `/mobile` change requires: `npm run build` in `mobile/` -> Propagate assets to `frontend/public/mobile/` -> `npx cap sync android` -> `npx cap sync ios` -> Verify native assets and adapters.
  - **Explicit Adapters Only**: Platform-specific code is strictly limited to OS adapters (e.g., Android Foreground Services, iOS CoreLocation background APIs, native notification bridges). Business rules and state machines must remain unified.

---

### 6. FROZEN TELEPHONY & SOFTPHONE ARCHITECTURE (ZERO-MODIFICATION LOCK)
- **Rule**: The complete production Telephony & Softphone stack is **STRICTLY FROZEN AND LOCKED**. DO NOT modify, refactor, replace, or redesign any component of this architecture.
- **Protected Core Components**:
  1. **Plivo WebRTC Softphone Controller** (`frontend/public/js/plivo-softphone.js`, `mobile/src/services/telephony.service.ts`):
     - W3C RFC 8829 `pranswer` early-media signaling bridge.
     - Dual answered state machine (`onCallAnswered` / backend session watcher).
     - Audio routing: Earpiece/receiver by default; Speaker strictly OFF by default unless toggled by user.
     - In-call controls: Mute, Hold, Speaker, and DTMF dialpad.
  2. **Telephony Backend XML & Callbacks** (`backend/app/services/telephony/flow_interpreter.py`, `backend/app/api/v1/endpoints/plivo_softphone_api.py`):
     - Dual-party session recording: `<Record recordSession="true" startOnDialAnswer="true" ... />` followed by `<Dial callbackUrl="...">`.
     - Dial callback lifecycle endpoint (`/api/v1/telephony/plivo/dial-callback`).
     - Recording callback endpoint and storage pipeline.
- **Standard**: All future features, UI tweaks, CRM adjustments, or mobile builds MUST treat this stack as immutable. No modifications are permitted.

---

### 7. ZERO API KEY EXPOSURE & ENVIRONMENT ISOLATION RULE (STRICT MANDATE)
- **Rule**: NEVER hardcode API keys, AWS credentials, secret tokens, or private access keys in source code, scripts, HTML templates, frontend bundles, or committed repository files.
- **Standard**:
  - **Dynamic Environment Resolution**: All credentials MUST be loaded dynamically via environment variables (`os.getenv("AWS_ACCESS_KEY_ID")`, `process.env.API_KEY`, etc.) or local `.env` files.
  - **Git & GitHub Safeguard**: All `.env`, `backend/.env`, `frontend/.env`, `.env.local`, `.env.production`, and build archives (`*.zip`) MUST remain strictly in `.gitignore`. NEVER stage or commit `.env` files or secret credentials to Git/GitHub repositories.
  - **No Secrets in Client Bundles**: Web, `/mobile`, Android, and iOS client-side assets MUST NOT expose private backend credentials. All file operations and external API requests requiring credentials MUST route securely through backend services.

---

### 8. STRICT AWS DEPLOYMENT ZIP SANITIZATION & ZERO CREDENTIAL LEAKAGE (MANDATORY ENFORCEMENT)
- **Rule**: Whenever generating or packaging deployment zip archives (`deployment.zip`, `MyntReal_AWS_Deploy.zip`), the zip MUST be 100% sanitized and completely free of any `.env` files, `.ebextensions/01_env.config`, or raw secrets.
- **Enforcement Directives**:
  1. **Strictly Exclude `.env` & Secrets**: `.env`, `.env.*`, `backend/.env`, `frontend/.env`, `credentials.json`, `id_rsa`, `.pem`, and `.key` files MUST NEVER be included in any deployment zip.
  2. **Do NOT Bundle `01_env.config`**: Never generate `.ebextensions/01_env.config` in deployment archives. This prevents exceeding the AWS CloudFormation 4096-byte hard limit and prevents credentials from leaking into AWS CloudTrail / CloudFormation event logs.
  3. **AWS Console / EB Environment Variable Decoupling**: All production secrets (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `DATABASE_URL`, `PROD_DATABASE_URL`, `RAZORPAY_*`, `GITHUB_TOKEN`, etc.) are maintained strictly in Elastic Beanstalk Environment Properties via the AWS Console or AWS CLI, never in the zip file.
  4. **No Hardcoded Credentials in Scripts**: All migration or reconciliation scripts in `backend/scripts/` must read environment variables dynamically (`os.environ.get("PROD_DATABASE_URL")`) with safe fallbacks, never hardcoded RDS passwords.
  5. **Mandatory Post-Packaging Security Audit**: Every deployment packaging tool (`build_aws_zip.py`) MUST perform an automated audit pass over the completed zip archive:
     - Verify 0 instances of `.env`, `01_env.config`, `.pem`, `.key`, `Secrets`, or private credentials.
     - Deep-scan text files for credential signatures (`AWS_SECRET_ACCESS_KEY`, `ghp_`, RDS passwords).
     - Abort immediately with a fatal `SecurityError` if any violation is detected.


