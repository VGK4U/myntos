#!/bin/bash
# Smart build script — skips pip install when requirements.txt hasn't changed
# DC-BUILD-CACHE-001

set -e

echo "[BUILD] Starting deployment build..."

# ── Python dependencies ──────────────────────────────────────────────────────
HASH_FILE=".pip_installed_hash"
CURRENT_HASH=$(md5sum backend/requirements.txt | cut -d' ' -f1)

if [ -f "$HASH_FILE" ] && [ "$(cat $HASH_FILE)" = "$CURRENT_HASH" ] && python3.11 -c "import fastapi, uvicorn, sqlalchemy" 2>/dev/null; then
    echo "[BUILD] ✅ Requirements unchanged — skipping pip install"
else
    echo "[BUILD] Installing Python dependencies..."
    python3.11 -m pip install --prefer-binary -q -r backend/requirements.txt
    echo "$CURRENT_HASH" > "$HASH_FILE"
    echo "[BUILD] ✅ Python dependencies installed"
fi

# ── Frontend npm (only 1 dep, fast either way) ───────────────────────────────
echo "[BUILD] Checking frontend dependencies..."
if [ -d "frontend/node_modules" ]; then
    echo "[BUILD] ✅ Frontend node_modules present — skipping npm install"
else
    npm --prefix frontend install --production --quiet
    echo "[BUILD] ✅ Frontend dependencies installed"
fi

echo "[BUILD] ✅ Build complete"
