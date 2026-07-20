# Project Architecture (VGK4U / MyntReal)

## Tech Stack Overview
This is a dual-stack application running both a Node.js frontend and a Python FastAPI backend simultaneously.

### 1. Frontend (Node.js)
- **Directory:** `/frontend`
- **Port:** Runs on `5000` (Locally and on Production).
- **Core Functionality:** Serves the static HTML/CSS/JS assets, acts as a proxy for the backend, handles route redirection, and manages caching.
- **Run Command:** `$env:PORT=5000; node server.js`

### 2. Backend (Python FastAPI)
- **Directory:** `/backend`
- **Port:** Runs on `8000` locally, but traffic in production is routed from the frontend to the backend internally.
- **Core Functionality:** Handles all database interactions, user authentication, social media API integrations (WhatsApp, Facebook), and data processing.
- **Database:** PostgreSQL (Hosted on Neon / AWS RDS).
- **Run Command:** `python -m uvicorn app.main:app --port 8000`

### 3. Production Deployment (AWS Elastic Beanstalk)
- **Platform:** Amazon Linux 2023 (Docker container).
- **Startup Script:** `start.sh` at the root directory orchestrates the boot sequence. It first launches the Python backend in the background using `uvicorn`, then launches the Node.js frontend in the foreground on port 5000.
- **Environment Variables:** Handled dynamically via the AWS Elastic Beanstalk console. They are read straight from the OS environment; no `.env` file is shipped to the production server.
- **Proxy/Routing:** Nginx sits in front of the application on AWS, listening on port 80 and forwarding traffic to port 5000 (Node.js). Node.js then proxies API requests to port 8000 (Python).
