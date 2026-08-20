#!/bin/bash
# Smart build script — skips pip install when requirements.txt hasn't changed
# DC-BUILD-CACHE-001

set -e

echo "[BUILD] Starting deployment build..."

# ── Python dependencies ──────────────────────────────────────────────────────
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    if command -v python3.11 &> /dev/null; then
        PYTHON_CMD="python3.11"
    else
        PYTHON_CMD="python"
    fi
fi

HASH_FILE=".pip_installed_hash"
CURRENT_HASH=$(md5sum backend/requirements.txt 2>/dev/null | cut -d' ' -f1 || md5 -q backend/requirements.txt 2>/dev/null || echo "nocache")

if [ -f "$HASH_FILE" ] && [ "$(cat $HASH_FILE)" = "$CURRENT_HASH" ] && $PYTHON_CMD -c "import fastapi, uvicorn, sqlalchemy" 2>/dev/null; then
    echo "[BUILD] ✅ Requirements unchanged — skipping pip install"
else
    echo "[BUILD] Installing Python dependencies with $PYTHON_CMD..."
    $PYTHON_CMD -m pip install --prefer-binary -q -r backend/requirements.txt || pip install --prefer-binary -q -r backend/requirements.txt
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
