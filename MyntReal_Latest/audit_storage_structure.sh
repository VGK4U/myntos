#!/bin/bash

echo "===================================="
echo " MNR – STORAGE & MEDIA AUDIT REPORT "
echo "===================================="
echo ""

echo "1️⃣ PROJECT ROOT STRUCTURE"
echo "-------------------------"
ls -lah
echo ""

echo "2️⃣ FRONTEND STRUCTURE"
echo "---------------------"
ls -lah frontend || echo "❌ frontend folder missing"
echo ""

echo "3️⃣ BACKEND STRUCTURE"
echo "--------------------"
ls -lah backend || echo "❌ backend folder missing"
echo ""

echo "4️⃣ STORAGE DIRECTORIES (CRITICAL)"
echo "--------------------------------"
echo "Checking common storage paths:"
for dir in storage frontend/storage backend/storage public/storage; do
  if [ -d "$dir" ]; then
    echo "✅ FOUND: $dir"
    ls -lah "$dir" | head -n 20
  else
    echo "❌ MISSING: $dir"
  fi
  echo ""
done

echo "5️⃣ SEARCH FOR IMAGE FILES"
echo "-------------------------"
find . -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) 2>/dev/null | head -n 50
echo ""

echo "6️⃣ SEARCH FOR ANNOUNCEMENT MEDIA REFERENCES"
echo "------------------------------------------"
grep -rln "announcement" backend frontend 2>/dev/null | head -n 30 || echo "⚠️ No announcement references found"
echo ""

echo "7️⃣ BACKEND STORAGE ENDPOINT"
echo "---------------------------"
grep -rn "storage" backend 2>/dev/null | head -n 50
echo ""

echo "8️⃣ ENVIRONMENT VARIABLES (SANITIZED)"
echo "------------------------------------"
env | grep -i storage 2>/dev/null
env | grep -i s3 2>/dev/null
env | grep -i bucket 2>/dev/null
echo ""

echo "✅ AUDIT COMPLETE"
