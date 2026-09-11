# Cross-Platform & Runtime Compatibility Rules

## 1. No Hardcoded Absolute Paths
- **Never** hardcode local machine paths (e.g. `/Users/viswanathkari/...`, `C:\Users\...`).
- Must always compute paths dynamically relative to the current file using `pathlib` or `os.path.abspath(os.path.join(os.path.dirname(__file__), '...'))`.
- Must work cleanly on both Windows (local) and Linux (AWS Elastic Beanstalk).

## 2. No Browser Globals in Node.js
- Never assume `window` or `document` exist in Node.js runtime environments.
- Always check `typeof window !== 'undefined'` before accessing browser objects.
