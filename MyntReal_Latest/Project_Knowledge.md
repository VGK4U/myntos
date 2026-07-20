# Project Knowledge Base

## Important Context for AI Agents & Developers
This document serves as the "Shared Brain" for any AI agents or developers working on the `vgk4u` (MyntReal) repository.

### Recent Critical Fixes (July 2026)
1. **Server Worker Fix (Uvicorn):** 
   - We migrated the backend from `gunicorn` to `uvicorn` running a single worker. 
   - **Why:** The AWS Elastic Beanstalk server (t2/t3.micro) only has 1GB of RAM. Running multiple Gunicorn workers caused memory to spike over 100% and crash. The single Uvicorn worker keeps memory stable around 85-90%.
   - **Where:** See `start.sh` where `python -m uvicorn app.main:app` is executed.

2. **Security & Password Leak:**
   - Previously, `.ebextensions/01_env.config` (which contained real production secrets) was leaked to GitHub.
   - **Fix:** We deleted the file from the codebase, added it to `.gitignore`, and wrote a dynamic Python script (`zip_for_aws.py`) to inject the secrets *during* the local zip process without committing them.
   - **Note on GitGuardian:** The GitGuardian warning was triggered because the old commit still exists in the GitHub history. We have opted to leave it for now, but rotating passwords via AWS Console is the recommended long-term fix.

3. **Local Development `.env` Setup:**
   - The `.env` file is heavily gitignored. 
   - **Rule:** If you are setting up this project locally for the first time, you MUST obtain the `.env` file from a teammate via a secure channel (Slack/Email) and place it in the root directory. The application will crash without it.
