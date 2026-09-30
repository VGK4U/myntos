# VGK4U SYSTEM RULES - ENFORCE AT ALL TIMES

You are an AI coding assistant working on the VGK4U codebase. You must strictly obey the following deployment rules to prevent AWS production server crashes. If you violate these rules, the Elastic Beanstalk server will fail.

1. **NO ABSOLUTE PATHS:** Never generate or use hardcoded absolute paths (e.g., `/Users/name/...` or `C:/...`). All file paths must be dynamically resolved.
   - Python: Use `os.path.abspath(os.path.join(os.path.dirname(__file__), "..."))`
   - Node: Use `path.join(__dirname, "...")`

2. **DOCKERFILE SYNCHRONIZATION:** If you instruct the user to create a new `package.json` (for Node) or `requirements.txt` (for Python) in any subdirectory, you MUST explicitly update the root `Dockerfile`. 
   - You must add a `COPY` instruction for the manifest file.
   - You must add a `RUN npm install` or `RUN pip install` instruction for that specific directory so AWS knows to install it.

3. **SSR SAFETY (NEXT.JS):** The frontend uses Server-Side Rendering. Never use browser-specific global objects (`window`, `document`, `localStorage`) in the global scope of a file. 
   - You must wrap them in `if (typeof window !== 'undefined') { ... }` or place them inside `useEffect` hooks.

4. **MEMORY AWARENESS:** The AWS production server is a monolithic instance with limited RAM. Do not silently bundle memory-heavy background processes (like Headless Chrome/Puppeteer bots) into the main API startup script without warning the user about Out-Of-Memory (OOM) risks.
