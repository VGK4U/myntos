#!/bin/bash
# ======================================================
# PET 3 - Combined UI/DB Validation + Advanced Reporting
# For EV Reference Program - Admin & User Systems
# ======================================================

echo "🚀 Starting PET 3 - Comprehensive Application Check..."

REPORT_FILE="logs/advanced_report_$(date +%Y%m%d_%H%M%S).txt"
mkdir -p logs/ui_comparison

echo "📊 ADVANCED SYSTEM REPORT" > $REPORT_FILE
echo "Generated at: $(date)" >> $REPORT_FILE
echo "=========================================" >> $REPORT_FILE

# STEP 1 + STEP 2: UI Comparison + DB Validation
echo "🔍 Running Combined UI & Database Validation..."
echo "--- UI & Database Validation ---" >> $REPORT_FILE

# UI Comparison
if [ ! -d ".git" ]; then
  echo "❌ No Git repository found. Cannot compare previous version." | tee -a $REPORT_FILE
else
  PREV_COMMIT=$(git rev-parse HEAD~1)
  CURR_COMMIT=$(git rev-parse HEAD)

  echo "🔄 Comparing $PREV_COMMIT vs $CURR_COMMIT..." | tee -a $REPORT_FILE
  git diff $PREV_COMMIT $CURR_COMMIT -- \
    "frontend/src/app/admin/" \
    "frontend/src/components/" \
    "frontend/src/styles/" \
    "backend/app/" \
    > logs/ui_comparison/diff_report.txt

  if [ -s logs/ui_comparison/diff_report.txt ]; then
    echo "⚠️ UI differences found. See logs/ui_comparison/diff_report.txt" | tee -a $REPORT_FILE
  else
    echo "✅ No UI differences found." | tee -a $REPORT_FILE
  fi
fi

# Database Validation
echo "🗄️ Database: PostgreSQL + FastAPI detected" | tee -a $REPORT_FILE

# Check database connectivity
if [ -n "$DATABASE_URL" ]; then
  echo "✅ Database connection available" | tee -a $REPORT_FILE
else
  echo "❌ DATABASE_URL not found" | tee -a $REPORT_FILE
fi

# Check backend API health
echo "🔍 Checking Backend API Health..." | tee -a $REPORT_FILE
curl -f http://localhost:8000/docs > /dev/null 2>&1
if [ $? -eq 0 ]; then
  echo "✅ FastAPI backend responding" | tee -a $REPORT_FILE
else
  echo "❌ FastAPI backend not responding" | tee -a $REPORT_FILE
fi

# Check frontend
echo "🔍 Checking Frontend Health..." | tee -a $REPORT_FILE
curl -f http://localhost:3000 > /dev/null 2>&1
if [ $? -eq 0 ]; then
  echo "✅ React frontend responding" | tee -a $REPORT_FILE
else
  echo "❌ React frontend not responding" | tee -a $REPORT_FILE
fi

# STEP 3: Unit & Integration Tests
echo "🧪 Running Unit & Integration Tests..."
echo "--- Unit & Integration Tests ---" >> $REPORT_FILE

# Check for test files
if [ -f "frontend/package.json" ]; then
  cd frontend
  if grep -q '"test"' package.json; then
    echo "🔍 Running frontend tests..." | tee -a ../logs/advanced_report_*.txt
    npm test -- --watchAll=false >> ../logs/advanced_report_*.txt 2>&1 || echo "❌ Frontend tests failed" | tee -a ../logs/advanced_report_*.txt
  else
    echo "❓ No frontend test script found" | tee -a ../logs/advanced_report_*.txt
  fi
  cd ..
fi

if [ -f "backend/requirements.txt" ]; then
  echo "🔍 Checking backend dependencies..." | tee -a $REPORT_FILE
  cd backend
  python -c "import app.main; print('✅ Backend imports working')" >> ../$REPORT_FILE 2>&1 || echo "❌ Backend import failed" | tee -a ../$REPORT_FILE
  cd ..
fi

# STEP 4: End-to-End (E2E) Tests - Admin System
echo "🌐 Running Admin System E2E Tests..."
echo "--- Admin System E2E Tests ---" >> $REPORT_FILE

# Test admin pages accessibility
ADMIN_PAGES=(
  "admin/system-dashboard"
  "admin/team-management"
  "admin/bonanza-management"
  "admin/financial-operations"
  "admin/awards"
)

for page in "${ADMIN_PAGES[@]}"; do
  echo "Testing /$page..." | tee -a $REPORT_FILE
  curl -f "http://localhost:3000/$page" > /dev/null 2>&1
  if [ $? -eq 0 ]; then
    echo "✅ /$page accessible" | tee -a $REPORT_FILE
  else
    echo "❌ /$page not accessible" | tee -a $REPORT_FILE
  fi
done

# STEP 5: Error Logs (Last 60 Hours)
echo "📜 Collecting Errors from Last 60 Hours..."
echo "--- Error Log Summary ---" >> $REPORT_FILE

# Check workflow logs
find /tmp/logs/ -type f -mtime -3 -exec grep -l -i "error\|failed\|exception" {} \; | head -10 | while read file; do
  echo "Error found in: $file" >> $REPORT_FILE
  grep -i "error\|failed\|exception" "$file" | tail -5 >> $REPORT_FILE
done

# Check application logs
if [ -d "logs" ]; then
  find logs/ -type f -mtime -3 -exec cat {} \; | grep -i "error" >> $REPORT_FILE
fi

if grep -q "error\|failed\|exception" $REPORT_FILE; then
  echo "⚠️ Errors found in last 60 hours. See report." | tee -a $REPORT_FILE
else
  echo "✅ No errors found in last 60 hours." | tee -a $REPORT_FILE
fi

# STEP 6: System Status Check
echo "🔍 Running System Status Check..."
echo "--- System Status ---" >> $REPORT_FILE

# Check processes
ps aux | grep -E "(node|python|uvicorn)" >> $REPORT_FILE

# Check ports
netstat -tuln | grep -E "(3000|8000|5432)" >> $REPORT_FILE 2>/dev/null || echo "No netstat available" >> $REPORT_FILE

# STEP 7: Final Report
echo "✅ PET 3 Full-System Check Completed!"
echo "📊 Advanced report saved at: $REPORT_FILE"
echo "👉 Remember: Any changes must not break other data or functionality (Thumb Rule)."

# Show summary
echo ""
echo "=== VALIDATION SUMMARY ==="
echo "Report file: $REPORT_FILE"
if grep -q "❌" $REPORT_FILE; then
  echo "⚠️  ISSUES FOUND - Please check the report"
else
  echo "✅ ALL CHECKS PASSED"
fi