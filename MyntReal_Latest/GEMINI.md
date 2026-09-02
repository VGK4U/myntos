# Project Guidelines & Critical Rules

## Cross-Platform Compatibility & Runtime Environment Rules

### 1. NO HARDCODED ABSOLUTE PATHS
- **Rule**: NEVER hardcode local machine paths (e.g., `/Users/viswanathkari/...`, `C:\Users\...`, `/home/...`) into the code.
- **Context**: The codebase runs on **Windows** (local development) and **Linux** (AWS Elastic Beanstalk). Hardcoded paths cause `PermissionError: [WinError 5]` on Windows and `[Errno 13] Permission denied` on Linux.
- **Standard**: Always compute paths dynamically relative to the current file using Python's `pathlib` or `os.path.abspath(os.path.join(os.path.dirname(__file__), '...'))`.

### 2. NO BROWSER GLOBALS IN NODE.JS
- **Rule**: Never assume browser globals like `window` or `document` exist when code is evaluated in a Node.js environment (e.g., SSR, shared utilities, build tools, backend scripts).
- **Context**: Accessing `window` without safety guards causes `ReferenceError: window is not defined` crashes in Node.js, crashing backend services.
- **Standard**: Always use safe environment checks before referencing browser globals:
  ```typescript
  if (typeof window !== 'undefined') {
    // safe browser-only execution
  }
  ```
