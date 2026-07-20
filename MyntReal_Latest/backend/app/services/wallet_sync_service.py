"""
Daily Wallet Sync Service - KYC Enforcement
Transfers earning wallet to withdrawable wallet based on KYC approval
Runs daily at 3 AM IST
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, text
from datetime import datetime
from decimal import Decimal
from typing import Dict, List

from app.models.user import User
from app.models.kyc_blocking_log import KYCBlockingLog, WalletSyncLog

class WalletSyncService:
    """
    Daily wallet sync service with KYC enforcement
    
    Rules:
    - Earning wallet ≥ ₹1,000
    - KYC status must be 'Verified' or 'Approved' (approved by RVZ ID)
    - If conditions met: Transfer to withdrawable wallet
    - If not: Skip and log to KYC blocking log
    """
    
    MINIMUM_TRANSFER_AMOUNT = Decimal('1000.00')
    APPROVED_KYC_STATUSES = ['Verified', 'Approved']  # KYC approved by RVZ ID
    
    def __init__(self, db: Session):
        self.db = db
    
    def run_daily_sync(self) -> Dict:
        """
        Run daily wallet sync for all users (DC Protocol Phase 1.9 - Architect Approved)
        Called by scheduler at 3 AM IST
        
        NEW FLOW: Queries pending_income instead of user.earning_wallet
        Refreshes materialized views ONCE per job (not per user) using CONCURRENTLY
        """
        sync_timestamp = datetime.now()
        
        # DC Protocol Phase 1.9: Get users with earning balance from pending_income (not user table)
        eligible_users_result = self.db.execute(text("""
            SELECT 
                user_id,
                SUM(net_amount) as earning_balance
            FROM pending_income
            WHERE verification_status IN ('Pending', 'Admin Verified', 'Super Admin Verified', 'Super Admin Approved')
            GROUP BY user_id
            HAVING SUM(net_amount) >= :minimum_amount
        """), {"minimum_amount": float(self.MINIMUM_TRANSFER_AMOUNT)}).fetchall()
        
        user_ids = [row[0] for row in eligible_users_result]
        users = self.db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []
        
        total_users = len(users)
        transferred_count = 0
        blocked_count = 0
        skipped_count = 0
        total_amount_transferred = Decimal('0.00')
        
        for user in users:
            result = self._process_user_wallet(user, sync_timestamp, skip_refresh=True)
            
            if result['status'] == 'transferred':
                transferred_count += 1
                total_amount_transferred += result['amount']
            elif result['status'] == 'blocked':
                blocked_count += 1
            elif result['status'] == 'skipped':
                skipped_count += 1
        
        # Commit all pending_income updates first
        self.db.commit()
        
        # ARCHITECT FIX: Refresh materialized views ONCE per job using CONCURRENTLY
        # This avoids ACCESS EXCLUSIVE locks and prevents blocking reads
        if transferred_count > 0:
            self.db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY user_earning_wallet_balance"))
            self.db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY user_withdrawable_wallet_balance"))
            self.db.commit()
        
        return {
            "sync_timestamp": sync_timestamp.isoformat(),
            "total_users_eligible": total_users,
            "transferred_count": transferred_count,
            "blocked_count": blocked_count,
            "skipped_count": skipped_count,
            "total_amount_transferred": float(total_amount_transferred),
            "status": "completed"
        }
    
    def sync_user_wallet_realtime(self, user: User) -> Dict:
        """
        REAL-TIME wallet sync for individual user (triggered by KYC/Bank approval)
        Called immediately when admin approves KYC or Bank details
        
        Returns:
            Dict with status ('transferred', 'blocked', 'skipped') and details
        """
        sync_timestamp = datetime.now()
        result = self._process_user_wallet(user, sync_timestamp, skip_refresh=False)
        
        # Commit immediately for real-time sync
        self.db.commit()
        
        # ARCHITECT FIX: Refresh views CONCURRENTLY for real-time sync
        if result['status'] == 'transferred':
            self.db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY user_earning_wallet_balance"))
            self.db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY user_withdrawable_wallet_balance"))
            self.db.commit()
        
        return result
    
    def _process_user_wallet(self, user: User, sync_timestamp: datetime, skip_refresh: bool = False) -> Dict:
        """
        Process individual user wallet transfer (DC Protocol Phase 1.9 - Architect Approved)
        
        NEW FLOW: Updates pending_income verification status instead of direct wallet writes
        Materialized views automatically recompute balances
        
        Args:
            skip_refresh: If True, skip materialized view refresh (used in batch mode)
        
        Returns:
            Dict with status ('transferred', 'blocked', 'skipped') and amount
        """
        # DC Protocol Phase 1.9: Get earning balance from pending_income (not user table)
        earning_balance_result = self.db.execute(text("""
            SELECT COALESCE(SUM(net_amount), 0) as earning_balance
            FROM pending_income
            WHERE user_id = :user_id
            AND verification_status IN ('Pending', 'Admin Verified', 'Super Admin Verified', 'Super Admin Approved')
        """), {"user_id": user.id}).fetchone()
        
        earning_balance = Decimal(str(earning_balance_result[0])) if earning_balance_result else Decimal('0.00')
        
        # Check KYC status (DC Protocol requirement)
        if user.kyc_status not in self.APPROVED_KYC_STATUSES:
            # KYC not approved - block transfer and log
            self._log_kyc_block(user, earning_balance, sync_timestamp)
            return {
                "status": "blocked",
                "reason": f"KYC status: {user.kyc_status}",
                "amount": 0
            }
        
        # Check bank details approval (DC Protocol requirement)
        if user.bank_details_status != 'Approved':
            # Bank details not approved - block transfer and log
            self._log_kyc_block(user, earning_balance, sync_timestamp, bank_reason=True)
            return {
                "status": "blocked",
                "reason": f"Bank details status: {user.bank_details_status}",
                "amount": 0
            }
        
        # Check minimum amount
        if earning_balance < self.MINIMUM_TRANSFER_AMOUNT:
            return {
                "status": "skipped",
                "reason": f"Below minimum: ₹{earning_balance}",
                "amount": 0
            }
        
        # DC Protocol Phase 1.9: Update pending_income verification status
        # This moves income from "Pending" → "Completed"
        # Materialized views automatically recompute:
        #   - earning_wallet decreases (less Pending income)
        #   - withdrawable_wallet increases (more Completed income)
        
        # Get withdrawable balance BEFORE update
        withdrawable_before_result = self.db.execute(text("""
            SELECT COALESCE(withdrawable_wallet, 0) as balance
            FROM user_withdrawable_wallet_balance
            WHERE user_id = :user_id
        """), {"user_id": user.id}).fetchone()
        withdrawable_before = Decimal(str(withdrawable_before_result[0])) if withdrawable_before_result else Decimal('0.00')
        earning_before = earning_balance
        
        # Update pending_income records: Pending → Completed
        update_result = self.db.execute(text("""
            UPDATE pending_income
            SET verification_status = 'Completed',
                accounts_paid_at = :paid_at,
                accounts_paid_by_id = 'SYSTEM_WALLET_SYNC'
            WHERE user_id = :user_id
            AND verification_status IN ('Pending', 'Admin Verified', 'Super Admin Verified', 'Super Admin Approved')
            RETURNING id, net_amount
        """), {
            "user_id": user.id,
            "paid_at": sync_timestamp
        })
        
        updated_records = update_result.fetchall()
        
        # ARCHITECT FIX: Detect zero-row updates (race condition - already processed)
        if not updated_records or len(updated_records) == 0:
            return {
                "status": "skipped",
                "reason": "No pending income found (already processed or race condition)",
                "amount": 0
            }
        
        transfer_amount = sum(Decimal(str(record[1])) for record in updated_records)
        
        # Update user last sync timestamp
        user.last_wallet_sync_at = sync_timestamp
        
        # Log successful transfer
        sync_log = WalletSyncLog(
            user_id=user.id,
            synced_at=sync_timestamp,
            amount_transferred=transfer_amount,
            earning_wallet_before=earning_before,
            earning_wallet_after=Decimal('0.00'),
            withdrawable_wallet_before=withdrawable_before,
            withdrawable_wallet_after=withdrawable_before + transfer_amount,
            kyc_status=user.kyc_status,
            sync_job_timestamp=sync_timestamp
        )
        self.db.add(sync_log)
        
        return {
            "status": "transferred",
            "amount": transfer_amount,
            "reason": "Success - DC Protocol Phase 1.9"
        }
    
    def _log_kyc_block(self, user: User, amount: Decimal, sync_timestamp: datetime, bank_reason: bool = False):
        """Log user blocked due to KYC or bank details issues (DC Protocol)"""
        
        # Determine reason
        if bank_reason:
            # Bank details blocking
            if user.bank_details_status == 'Not Submitted':
                reason = "Bank details not submitted - user must complete bank information"
            elif user.bank_details_status in ['Pending Admin', 'Pending Finance']:
                reason = f"Bank details approval pending - status: {user.bank_details_status}"
            elif user.bank_details_status == 'Rejected':
                reason = "Bank details rejected - user must resubmit correct information"
            else:
                reason = f"Bank details status '{user.bank_details_status}' not approved"
        else:
            # KYC blocking
            if user.kyc_status == 'Pending':
                reason = "KYC verification pending - awaiting admin approval"
            elif user.kyc_status == 'Rejected':
                reason = "KYC verification rejected - user must resubmit documents"
            else:
                reason = f"KYC status '{user.kyc_status}' not approved by RVZ ID"
        
        blocking_log = KYCBlockingLog(
            user_id=user.id,
            blocked_at=sync_timestamp,
            earning_wallet_amount=amount,
            kyc_status=user.kyc_status,
            reason=reason,
            sync_job_timestamp=sync_timestamp
        )
        self.db.add(blocking_log)
    
    def get_kyc_blocking_report(self, date: datetime = None) -> List[Dict]:
        """
        Get KYC blocking report for a specific date
        Used by admin panel
        """
        if date is None:
            date = datetime.now().date()
        
        # Get all blocks for the date
        blocks = self.db.query(KYCBlockingLog).filter(
            and_(
                KYCBlockingLog.blocked_at >= datetime.combine(date, datetime.min.time()),
                KYCBlockingLog.blocked_at < datetime.combine(date, datetime.max.time())
            )
        ).all()
        
        report = []
        for block in blocks:
            user = self.db.query(User).filter(User.id == block.user_id).first()
            if user:
                report.append({
                    "user_id": block.user_id,
                    "user_name": user.name,
                    "earning_wallet_amount": float(block.earning_wallet_amount),
                    "kyc_status": block.kyc_status,
                    "reason": block.reason,
                    "blocked_at": block.blocked_at.isoformat()
                })
        
        return report
    
    def get_wallet_sync_report(self, date: datetime = None) -> List[Dict]:
        """
        Get successful wallet sync report for a specific date
        Used by admin panel
        """
        if date is None:
            date = datetime.now().date()
        
        # Get all syncs for the date
        syncs = self.db.query(WalletSyncLog).filter(
            and_(
                WalletSyncLog.synced_at >= datetime.combine(date, datetime.min.time()),
                WalletSyncLog.synced_at < datetime.combine(date, datetime.max.time())
            )
        ).all()
        
        report = []
        for sync in syncs:
            user = self.db.query(User).filter(User.id == sync.user_id).first()
            if user:
                report.append({
                    "user_id": sync.user_id,
                    "user_name": user.name,
                    "amount_transferred": float(sync.amount_transferred),
                    "earning_wallet_before": float(sync.earning_wallet_before),
                    "withdrawable_wallet_after": float(sync.withdrawable_wallet_after),
                    "kyc_status": sync.kyc_status,
                    "synced_at": sync.synced_at.isoformat()
                })
        
        return report
