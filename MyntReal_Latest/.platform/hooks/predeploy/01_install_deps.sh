#!/bin/bash
set -e
echo "[EB-HOOK] Installing backend Python dependencies..."
cd /var/app/staging 2>/dev/null || cd /var/app/current 2>/dev/null || true
PYTHON_CMD=$(which python3 2>/dev/null || which python 2>/dev/null || echo "python3")
$PYTHON_CMD -m pip install --prefer-binary -r backend/requirements.txt || true
echo "[EB-HOOK] Python dependencies setup completed."
