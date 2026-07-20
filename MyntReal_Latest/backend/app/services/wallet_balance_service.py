"""
DC Protocol Phase 1.3: Wallet Balance Service
Queries materialized views for real-time wallet balances

Purpose: Provide fast, accurate wallet balance queries using materialized views
         instead of expensive CTE calculations on every request.

Author: DC Protocol Implementation Team
Date: November 2, 2025
"""

from typing import Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text
from decimal import Decimal


class WalletBalanceService:
    """Service for querying wallet balances from materialized views"""
    
    @staticmethod
    def get_earning_wallet(db: Session, user_id: str) -> Decimal:
        """
        Get earning wallet balance from materialized view
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Decimal: Earning wallet balance (0.0 if user not in view)
        """
        query = text("""
            SELECT earning_wallet
            FROM user_earning_wallet_balance
            WHERE user_id = :user_id
        """)
        
        result = db.execute(query, {"user_id": user_id}).first()
        
        if result:
            return Decimal(str(result[0]))
        return Decimal("0.0")
    
    @staticmethod
    def get_withdrawable_wallet(db: Session, user_id: str) -> Decimal:
        """
        Get withdrawable wallet balance from materialized view
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Decimal: Withdrawable wallet balance (0.0 if user not in view)
        """
        query = text("""
            SELECT withdrawable_wallet
            FROM user_withdrawable_wallet_balance
            WHERE user_id = :user_id
        """)
        
        result = db.execute(query, {"user_id": user_id}).first()
        
        if result:
            return Decimal(str(result[0]))
        return Decimal("0.0")
    
    @staticmethod
    def get_both_wallets(db: Session, user_id: str) -> Dict[str, Decimal]:
        """
        Get both wallet balances from materialized views
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Dict with keys: earning_wallet, withdrawable_wallet
        """
        earning_query = text("""
            SELECT earning_wallet
            FROM user_earning_wallet_balance
            WHERE user_id = :user_id
        """)
        
        withdrawable_query = text("""
            SELECT withdrawable_wallet
            FROM user_withdrawable_wallet_balance
            WHERE user_id = :user_id
        """)
        
        earning_result = db.execute(earning_query, {"user_id": user_id}).first()
        withdrawable_result = db.execute(withdrawable_query, {"user_id": user_id}).first()
        
        return {
            "earning_wallet": Decimal(str(earning_result[0])) if earning_result else Decimal("0.0"),
            "withdrawable_wallet": Decimal(str(withdrawable_result[0])) if withdrawable_result else Decimal("0.0")
        }
    
    @staticmethod
    def get_earning_wallet_details(db: Session, user_id: str) -> Optional[Dict]:
        """
        Get detailed earning wallet information from materialized view
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Dict with earning_wallet, pending_income_count, last_income_date, last_refreshed
            None if user not in view
        """
        query = text("""
            SELECT 
                earning_wallet,
                pending_income_count,
                last_income_date,
                last_refreshed
            FROM user_earning_wallet_balance
            WHERE user_id = :user_id
        """)
        
        result = db.execute(query, {"user_id": user_id}).first()
        
        if result:
            return {
                "earning_wallet": Decimal(str(result[0])),
                "pending_income_count": result[1],
                "last_income_date": result[2],
                "last_refreshed": result[3]
            }
        return None
    
    @staticmethod
    def get_withdrawable_wallet_details(db: Session, user_id: str) -> Optional[Dict]:
        """
        Get detailed withdrawable wallet information from materialized view
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Dict with total_earned, total_withdrawn, withdrawable_wallet, 
            paid_income_count, withdrawal_count, last_refreshed
            None if user not in view
        """
        query = text("""
            SELECT 
                total_earned,
                total_withdrawn,
                withdrawable_wallet,
                paid_income_count,
                withdrawal_count,
                last_refreshed
            FROM user_withdrawable_wallet_balance
            WHERE user_id = :user_id
        """)
        
        result = db.execute(query, {"user_id": user_id}).first()
        
        if result:
            return {
                "total_earned": Decimal(str(result[0])),
                "total_withdrawn": Decimal(str(result[1])),
                "withdrawable_wallet": Decimal(str(result[2])),
                "paid_income_count": result[3],
                "withdrawal_count": result[4],
                "last_refreshed": result[5]
            }
        return None
    
    @staticmethod
    def refresh_views(db: Session) -> None:
        """
        Manually refresh both materialized views
        
        Note: Normally views are auto-refreshed by triggers.
              This is for manual refresh if needed.
        
        Args:
            db: Database session
        """
        query = text("SELECT refresh_wallet_materialized_views()")
        db.execute(query)
        db.commit()
    
    @staticmethod
    def get_view_stats(db: Session) -> Dict:
        """
        Get statistics about materialized views
        
        Returns:
            Dict with counts, totals, and refresh timestamps
        """
        earning_stats_query = text("""
            SELECT 
                COUNT(*) as user_count,
                COALESCE(SUM(earning_wallet), 0.0) as total_earning,
                MAX(last_refreshed) as last_refresh
            FROM user_earning_wallet_balance
        """)
        
        withdrawable_stats_query = text("""
            SELECT 
                COUNT(*) as user_count,
                COALESCE(SUM(total_earned), 0.0) as total_earned,
                COALESCE(SUM(total_withdrawn), 0.0) as total_withdrawn,
                COALESCE(SUM(withdrawable_wallet), 0.0) as total_withdrawable,
                MAX(last_refreshed) as last_refresh
            FROM user_withdrawable_wallet_balance
        """)
        
        earning_stats = db.execute(earning_stats_query).first()
        withdrawable_stats = db.execute(withdrawable_stats_query).first()
        
        return {
            "earning_wallet_view": {
                "user_count": earning_stats[0],
                "total_earning": float(earning_stats[1]),
                "last_refreshed": earning_stats[2]
            },
            "withdrawable_wallet_view": {
                "user_count": withdrawable_stats[0],
                "total_earned": float(withdrawable_stats[1]),
                "total_withdrawn": float(withdrawable_stats[2]),
                "total_withdrawable": float(withdrawable_stats[3]),
                "last_refreshed": withdrawable_stats[4]
            }
        }


# Convenience functions for direct import
def get_earning_wallet(db: Session, user_id: str) -> Decimal:
    """Get earning wallet balance from materialized view"""
    return WalletBalanceService.get_earning_wallet(db, user_id)


def get_withdrawable_wallet(db: Session, user_id: str) -> Decimal:
    """Get withdrawable wallet balance from materialized view"""
    return WalletBalanceService.get_withdrawable_wallet(db, user_id)


def get_both_wallets(db: Session, user_id: str) -> Dict[str, Decimal]:
    """Get both wallet balances from materialized views"""
    return WalletBalanceService.get_both_wallets(db, user_id)
