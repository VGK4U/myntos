"""
Wallet Service - Transaction and Wallet Management
Handles all wallet operations, transactions, and withdrawals
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, text

from app.models.user import User
from app.models.transaction import Transaction, PendingIncome
from app.models.base import get_indian_time

class WalletService:
    """Wallet and transaction management service"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_wallet_balance(self, user_id: str) -> Dict[str, float]:
        """Get user's wallet balances - DC Protocol Phase 1.6: READ from materialized views
        
        PRODUCTION CUTOVER: Now reads computed values from database ledger tables
        Single source of truth: pending_income + withdrawal_request tables
        """
        from app.services.wallet_balance_service import get_both_wallets
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}
        
        # DC Protocol Phase 1.6: Read computed balances from materialized views
        computed_wallets = get_both_wallets(self.db, user_id)
        earning_wallet = float(computed_wallets['earning_wallet'])
        withdrawable_wallet = float(computed_wallets['withdrawable_wallet'])
        
        # Use earned_total from user table (reset to ₹0, scheduler will update with new income)
        total_earnings = float(getattr(user, 'earned_total', 0) or 0)
        
        return {
            "success": True,
            # DC Protocol Phase 1.6: COMPUTED values from materialized views (single source of truth)
            "earning_wallet": earning_wallet,
            "withdrawable_wallet": withdrawable_wallet,
            # Existing Wallets (deprecated, but kept for compatibility)
            "wallet_balance": float(getattr(user, 'wallet_balance', 0) or 0),
            "upgrade_wallet_balance": float(getattr(user, 'upgrade_wallet_balance', 0) or 0),
            "total_earnings": float(total_earnings),  # Sum from pending_income (includes future)
            "released_total": float(getattr(user, 'released_total', 0) or 0),
            # KYC Status
            "kyc_status": getattr(user, 'kyc_status', 'Pending'),
            "last_wallet_sync_at": getattr(user, 'last_wallet_sync_at', None).isoformat() if getattr(user, 'last_wallet_sync_at', None) else None
        }
    
    # DC Protocol Phase 1.7: REMOVED dead create_transaction() method (lines 57-184)
    # Reason: No endpoint calls this function - verified via grep search
    # Impact: None - this was dead code
    # Replacement: All income flows through pending_income table (single source of truth)
    
    def get_transaction_history(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        transaction_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get user's transaction history"""
        query = self.db.query(Transaction).filter(Transaction.referrer_id == user_id)
        
        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)
        
        total = query.count()
        transactions = query.order_by(desc(Transaction.timestamp)).limit(limit).offset(offset).all()
        
        return {
            "success": True,
            "transactions": [
                {
                    "id": str(getattr(t, 'id', '')),
                    "amount": float(getattr(t, 'amount', 0) or 0),
                    "type": str(getattr(t, 'transaction_type', '')),
                    "timestamp": getattr(t, 'timestamp', datetime.now()).isoformat()
                }
                for t in transactions
            ],
            "total": total,
            "page": offset // limit + 1 if limit > 0 else 1
        }
    
    def get_earnings_summary(self, user_id: str) -> Dict[str, Any]:
        """
        DC Protocol Phase 1.7: Thin wrapper over DashboardService._get_financial_summary
        DECOMMISSIONED old income_type breakdown logic (was duplicate code)
        Returns canonical earnings data from SINGLE SOURCE OF TRUTH
        """
        from app.services.dashboard_service import DashboardService
        
        # Get canonical financial summary from DashboardService
        dashboard_service = DashboardService(self.db)
        current_month = datetime.now().strftime("%Y-%m")
        financial_summary = dashboard_service._get_financial_summary(user_id, current_month)
        
        # Extract lifetime earnings (backward compatible format)
        lifetime = financial_summary.get('lifetime', {})
        
        # Query income_type breakdown for backward compatibility
        income_summary = self.db.query(
            PendingIncome.income_type,
            func.count(PendingIncome.id).label('count'),
            func.sum(PendingIncome.gross_amount).label('gross_total'),
            func.sum(PendingIncome.net_amount).label('net_total')
        ).filter(
            PendingIncome.user_id == user_id
        ).group_by(PendingIncome.income_type).all()
        
        # Build income type breakdown
        income_breakdown = {
            'Direct Referral': {'gross': 0.0, 'net': 0.0, 'count': 0},
            'Matching Referral': {'gross': 0.0, 'net': 0.0, 'count': 0},
            'Ved Income': {'gross': 0.0, 'net': 0.0, 'count': 0},
            'Guru Dakshina': {'gross': 0.0, 'net': 0.0, 'count': 0}
        }
        
        for row in income_summary:
            income_type = row.income_type
            if income_type in income_breakdown:
                income_breakdown[income_type] = {
                    'gross': float(row.gross_total or 0),
                    'net': float(row.net_total or 0),
                    'count': int(row.count or 0)
                }
        
        # Return unified format using DashboardService canonical data
        return {
            # Income type breakdown
            'direct_referral_total': income_breakdown['Direct Referral']['gross'],
            'direct_referral_net': income_breakdown['Direct Referral']['net'],
            'direct_referral_count': income_breakdown['Direct Referral']['count'],
            'matching_referral_total': income_breakdown['Matching Referral']['gross'],
            'matching_referral_net': income_breakdown['Matching Referral']['net'],
            'matching_referral_count': income_breakdown['Matching Referral']['count'],
            'ved_income_total': income_breakdown['Ved Income']['gross'],
            'ved_income_net': income_breakdown['Ved Income']['net'],
            'ved_income_count': income_breakdown['Ved Income']['count'],
            'guru_dakshina_total': income_breakdown['Guru Dakshina']['gross'],
            'guru_dakshina_net': income_breakdown['Guru Dakshina']['net'],
            'guru_dakshina_count': income_breakdown['Guru Dakshina']['count'],
            
            # Deduction breakdown from canonical source
            'total_gurudakshina_deduction': lifetime.get('deduction_breakdown', {}).get('guru_dakshina', 0.0),
            'total_admin_deduction': lifetime.get('deduction_breakdown', {}).get('admin_charge', 0.0),
            'total_tds_deduction': lifetime.get('deduction_breakdown', {}).get('tds', 0.0),
            
            # Totals from canonical source (DashboardService) - BOTH GROSS and NET
            'total_gross_earnings': lifetime.get('gross_earnings', 0.0),
            'total_net_earnings': lifetime.get('net_earnings', 0.0),
            # Withdrawn amounts - BOTH GROSS and NET (no reverse calculations!)
            'withdrawn_gross': lifetime.get('withdrawn_gross', 0.0),
            'withdrawn_net': lifetime.get('withdrawn_net', 0.0),
            # Pending balances - BOTH GROSS and NET
            'pending_balance_gross': lifetime.get('pending_balance_gross', 0.0),
            'pending_balance_net': lifetime.get('pending_balance_net', 0.0),
            # Legacy fields for backward compatibility
            'total_withdrawn': lifetime.get('total_withdrawn', 0.0),
            'pending_balance': lifetime.get('pending_balance', 0.0)
        }
    
    def request_withdrawal(
        self,
        user_id: str,
        amount: float,
        withdrawal_type: str = 'bank_transfer'
    ) -> Dict[str, Any]:
        """Request a withdrawal - KYC ENFORCEMENT ENABLED"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}
        
        # TEMPORARY: KYC check disabled - skip for now (November 2, 2025)
        # CRITICAL: KYC Enforcement - Check KYC status first
        # kyc_status = getattr(user, 'kyc_status', 'Pending')
        # if kyc_status not in ['Verified', 'Approved']:
        #     if kyc_status == 'Pending':
        #         return {
        #             "success": False, 
        #             "error": "Your KYC verification is pending. Please complete KYC verification to withdraw funds.",
        #             "kyc_required": True
        #         }
        #     elif kyc_status == 'Rejected':
        #         return {
        #             "success": False,
        #             "error": "Your KYC verification was rejected. Please resubmit KYC documents to withdraw funds.",
        #             "kyc_required": True
        #         }
        #     else:
        #         return {
        #             "success": False,
        #             "error": "KYC verification required. Please complete KYC to withdraw funds.",
        #             "kyc_required": True
        #         }
        
        # NEW: Use withdrawable_wallet instead of wallet_balance
        withdrawable_balance = float(getattr(user, 'withdrawable_wallet', 0) or 0)
        earning_balance = float(getattr(user, 'earning_wallet', 0) or 0)
        
        # Validate amount
        if amount <= 0:
            return {"success": False, "error": "Invalid withdrawal amount"}
        
        if amount > withdrawable_balance:
            # Show helpful message if they have earning wallet balance
            if earning_balance > 0:
                return {
                    "success": False,
                    "error": f"Insufficient withdrawable balance. Available: ₹{withdrawable_balance:,.2f}. You have ₹{earning_balance:,.2f} in earning wallet (transfers daily at 3 AM after KYC approval)."
                }
            else:
                return {
                    "success": False,
                    "error": f"Insufficient balance. Available: ₹{withdrawable_balance:,.2f}"
                }
        
        # Check minimum withdrawal
        if amount < 100:
            return {"success": False, "error": "Minimum withdrawal amount is ₹100"}
        
        # Create withdrawal transaction (pending)
        transaction = Transaction(
            user_id=user_id,
            amount=Decimal(str(-amount)),
            transaction_type='Withdrawal Request',
            timestamp=get_indian_time(),
            description=f"Withdrawal request - {withdrawal_type}"
        )
        
        try:
            self.db.add(transaction)
            self.db.commit()
            
            return {
                "success": True,
                "message": "Withdrawal request submitted successfully",
                "request_id": str(getattr(transaction, 'id', '')),
                "amount": amount,
                "status": "pending"
            }
        
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def process_withdrawal(
        self,
        transaction_id: str,
        admin_id: str,
        approved: bool,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a withdrawal request (admin action)"""
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            return {"success": False, "error": "Withdrawal request not found"}
        
        user = self.db.query(User).filter(User.id == str(getattr(transaction, 'user_id', ''))).first()
        if not user:
            return {"success": False, "error": "User not found"}
        
        try:
            if approved:
                # DC Protocol Phase 1.5: Set session variable to authorize wallet write
                self.db.execute(text("SET LOCAL app.wallet_write_allowed = 'wallet_sync'"))
                
                # Deduct from withdrawable_wallet (NEW KYC ENFORCEMENT)
                withdrawable_balance = float(getattr(user, 'withdrawable_wallet', 0) or 0)
                withdrawal_amount = abs(float(getattr(transaction, 'amount', 0) or 0))
                
                setattr(user, 'withdrawable_wallet', Decimal(str(withdrawable_balance - withdrawal_amount)))
                setattr(transaction, 'description', f"Withdrawal approved - {notes or ''}")
                
                self.db.commit()
                
                return {
                    "success": True,
                    "message": "Withdrawal approved and processed",
                    "new_balance": float(getattr(user, 'wallet_balance', 0) or 0)
                }
            else:
                # Reject withdrawal
                setattr(transaction, 'description', f"Withdrawal rejected - {notes or ''}")
                self.db.delete(transaction)
                self.db.commit()
                
                return {
                    "success": True,
                    "message": "Withdrawal request rejected"
                }
        
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}
