FROM node:20-slim AS node-binaries

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy Node.js runtime & npm directly from official node image (instant Node.js setup)
COPY --from=node-binaries /usr/local/bin/node /usr/local/bin/
COPY --from=node-binaries /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm

# Install system dependencies required for python-magic and health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency manifests first for Docker layer caching
COPY backend/requirements.txt backend/requirements.txt
COPY frontend/package.json frontend/package.json
COPY frontend/package-lock.json frontend/package-lock.json

# Install Python dependencies with pre-compiled wheels
RUN pip install --no-cache-dir --prefer-binary -r backend/requirements.txt

# Install Node.js production dependencies
RUN cd frontend && npm install --production --no-audit --no-fund

# Copy application source code
COPY . .

RUN chmod +x start.sh

EXPOSE 5000

CMD ["./start.sh"]
