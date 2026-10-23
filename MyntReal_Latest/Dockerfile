FROM node:20-slim AS node-binaries

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy Node.js runtime & npm directly from official node image (instant Node.js setup)
COPY --from=node-binaries /usr/local/bin/node /usr/local/bin/
COPY --from=node-binaries /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm

# Install system dependencies required for python-magic, Node.js (libstdc++6), health checks, and ffmpeg for video overlays
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    libstdc++6 \
    libgcc-s1 \
    curl \
    ca-certificates \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency manifests first for Docker layer caching
COPY backend/requirements.txt backend/requirements.txt
COPY frontend/package.json frontend/package.json
COPY backend/whatsapp-group-bot/package.json backend/whatsapp-group-bot/package.json
COPY backend/whatsapp-group-bot/package-lock.json backend/whatsapp-group-bot/package-lock.json

# Install Python dependencies with pre-compiled wheels
RUN pip install --no-cache-dir --prefer-binary --default-timeout=120 -r backend/requirements.txt

# Install Node.js production dependencies for frontend (no-package-lock prevents EINTEGRITY) and whatsapp bot
RUN cd frontend && npm install --omit=dev --no-audit --no-fund --no-package-lock
RUN cd backend/whatsapp-group-bot && NODE_OPTIONS="--max-old-space-size=512" npm install --omit=dev --no-audit --no-fund

# Cache buster ensures AWS Docker daemon always copies fresh application code without busting dependency cache
ARG BUILD_ID=v2.4.72-whatsapp-media-preview-and-bonanza-poster-tuning

# Copy application source code
COPY . .

# Fix line endings and make start.sh executable
RUN sed -i 's/\r$//' start.sh && chmod +x start.sh

EXPOSE 5000

CMD ["./start.sh"]
