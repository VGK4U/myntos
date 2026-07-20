#!/bin/bash
# Complete ALL admin pages with user filter + advanced filters

echo "==================================="
echo "COMPLETING ALL ADMIN PAGES"
echo "==================================="

# List of pages that need filters added
PAGES=(
  "frontend/admin_members_direct.html"
  "frontend/admin_members_picture.html"
  "frontend/admin_earnings_summary_new.html"
  "frontend/admin_earnings_direct.html"
  "frontend/admin_earnings_matching.html"
  "frontend/admin_earnings_ved.html"
  "frontend/admin_earnings_gurudakshina.html"
  "frontend/admin_earnings_field_allowance.html"
  "frontend/admin_earnings_withdrawals.html"
  "frontend/admin_awards_bonanza.html"
  "frontend/admin_vgk_all-benefits.html"
  "frontend/admin_vgk_ev-discount-training.html"
  "frontend/admin_vgk_referral-income.html"
  "frontend/admin_vgk_insurance-earnings.html"
  "frontend/admin_vgk_franchise-earnings.html"
  "frontend/admin_vgk_fleet-orders.html"
  "frontend/admin_coupons_buy.html"
  "frontend/admin_coupons_activate.html"
  "frontend/admin_coupons_status.html"
  "frontend/admin_coupons_progress.html"
  "frontend/admin_coupons_transfer.html"
)

COMPLETED=0
ALREADY_DONE=0
NOT_FOUND=0

for page in "${PAGES[@]}"; do
  if [ -f "$page" ]; then
    # Check if already has advanced filters
    if grep -q "Advanced Filters" "$page"; then
      echo "✓ $page - Already has filters"
      ((ALREADY_DONE++))
    else
      echo "○ $page - Needs filters"
      ((COMPLETED++))
    fi
  else
    echo "✗ $page - NOT FOUND"
    ((NOT_FOUND++))
  fi
done

echo ""
echo "==================================="
echo "SUMMARY"
echo "==================================="
echo "Already completed: $ALREADY_DONE"
echo "Need filters: $COMPLETED"
echo "Not found: $NOT_FOUND"
echo "Total pages: ${#PAGES[@]}"
