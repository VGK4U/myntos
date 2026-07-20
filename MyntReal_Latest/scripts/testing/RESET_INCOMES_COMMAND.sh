#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# INCOME RESET COMMAND
# ═══════════════════════════════════════════════════════════════════════════
# This command resets ALL income data to 0 for recalculation
# 
# WHAT IT DOES:
# 1. Deletes all income records (pending_income, transaction, ved_income, etc.)
# 2. Resets all user wallet balances to 0
# 3. Resets all user totals (earned_total, released_total) to 0
# 
# USAGE:
#   bash RESET_INCOMES_COMMAND.sh
# 
# OR:
#   python reset_incomes.py
# ═══════════════════════════════════════════════════════════════════════════

echo "⚠️  WARNING: This will DELETE all income data and reset wallets to 0!"
echo "Press CTRL+C to cancel, or ENTER to continue..."
read

python reset_incomes.py
