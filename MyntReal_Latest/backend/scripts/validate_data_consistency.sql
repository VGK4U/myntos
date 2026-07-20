-- DATA CONSISTENCY VALIDATION SCRIPT
-- Run this after ANY changes to income, wallets, or withdrawals

-- 1. Check Income vs Wallets
WITH income_check AS (
    SELECT 
        u.id,
        u.earning_wallet,
        (SELECT COALESCE(SUM(net_amount), 0) FROM pending_income WHERE user_id = u.id AND verification_status = 'Finance Paid') as income_paid,
        u.package_points
    FROM "user" u
    WHERE u.earning_wallet > 0
)
SELECT 
    COUNT(*) as mismatched_users,
    SUM(ABS(earning_wallet - income_paid)) as total_discrepancy
FROM income_check
WHERE package_points = 1.0 AND ABS(earning_wallet - income_paid) > 1;

-- 2. Check Withdrawals vs Available Balance
WITH withdrawal_check AS (
    SELECT 
        u.id,
        u.withdrawable_wallet,
        (SELECT COALESCE(SUM(withdrawal_amount), 0) FROM withdrawal_request WHERE user_id = u.id AND status = 'Pending') as pending_withdrawals
    FROM "user" u
)
SELECT 
    COUNT(*) as users_with_insufficient_balance
FROM withdrawal_check
WHERE pending_withdrawals > withdrawable_wallet;

-- 3. Status Distribution Summary
SELECT 'INCOME STATUS' as category, verification_status as status, COUNT(*) as count, SUM(net_amount) as total
FROM pending_income
GROUP BY verification_status
UNION ALL
SELECT 'WITHDRAWAL STATUS', status, COUNT(*), SUM(final_payout)
FROM withdrawal_request
GROUP BY status;
