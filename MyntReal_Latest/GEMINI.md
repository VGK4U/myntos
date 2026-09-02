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
