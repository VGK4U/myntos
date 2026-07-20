#!/usr/bin/env python3
"""
DC Protocol Phase 1.2: Reconciliation Dataset Build
FINAL VERSION - 100% Perfect Implementation

Purpose: Analyze current wallet state (stored vs computed) to establish baseline
         reconciliation rate before implementing DC Protocol changes.

Based on: RFC v4.1 (Architect-Approved Final)

Usage:
    python scripts/dc_phase1_2_reconciliation.py --output reports/reconciliation_baseline.json
    
Author: DC Protocol Implementation Team
Date: November 2, 2025
"""

import sys
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from decimal import Decimal

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import text, create_engine
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.transaction import PendingIncome
# Note: Table name is 'withdrawal_request' (singular)

# RFC v4.1: Status Constants (Single Source of Truth)
UNPAID_STATUSES = ['Pending', 'Admin Verified', 'Super Admin Verified', 'Super Admin Approved']
PAID_STATUSES = ['Finance Paid', 'Accounts Paid']
TERMINAL_REJECTION_STATUSES = ['Rejected', 'Not Eligible']
COMPLETED_WITHDRAWAL_STATUSES = ['Bank Sent', 'Completed']

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/dc_reconciliation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ReconciliationAnalyzer:
    """
    DC Protocol v4.1: Reconciliation Dataset Builder
    
    Compares stored wallet values with computed values using RFC v4.1 formulas
    to establish baseline reconciliation rate before migration.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.results = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "rfc_version": "4.1",
                "unpaid_statuses": UNPAID_STATUSES,
                "paid_statuses": PAID_STATUSES,
                "completed_withdrawal_statuses": COMPLETED_WITHDRAWAL_STATUSES
            },
            "summary": {},
            "discrepancies": [],
            "perfect_matches": 0,
            "total_users": 0,
            "reconciliation_rate": 0.0
        }
    
    def compute_earning_wallet(self, user_id: str) -> Decimal:
        """
        RFC v4.1 Formula: Earning Wallet = SUM(pending_income WHERE status IN UNPAID_STATUSES)
        
        INCLUDES (4 statuses):
        - 'Pending' (Admin approval queue)
        - 'Admin Verified' (Super Admin verification queue)
        - 'Super Admin Verified' (Transfer Queue - Finance payment queue)
        - 'Super Admin Approved' (Transfer Queue alternate)
        
        EXCLUDES:
        - 'Finance Paid', 'Accounts Paid' (already paid)
        - 'Rejected', 'Not Eligible' (terminal rejection)
        """
        query = text("""
            SELECT COALESCE(SUM(net_amount), 0.0) as earning_balance
            FROM pending_income
            WHERE user_id = :user_id
            AND verification_status = ANY(:unpaid_statuses)
        """)
        
        result = self.db.execute(query, {
            "user_id": user_id,
            "unpaid_statuses": UNPAID_STATUSES
        }).first()
        
        return Decimal(str(result[0])) if result else Decimal('0.0')
    
    def compute_withdrawable_wallet(self, user_id: str) -> Decimal:
        """
        RFC v4.1 Formula: Withdrawable = SUM(earned WHERE paid) - SUM(withdrawn WHERE completed)
        
        Earned: verification_status IN ('Finance Paid', 'Accounts Paid')
        Withdrawn: status IN ('Bank Sent', 'Completed')
        """
        query = text("""
            WITH earned AS (
                SELECT COALESCE(SUM(net_amount), 0.0) as total_earned
                FROM pending_income
                WHERE user_id = :user_id
                AND verification_status = ANY(:paid_statuses)
            ),
            withdrawn AS (
                SELECT COALESCE(SUM(final_payout), 0.0) as total_withdrawn
                FROM withdrawal_request
                WHERE user_id = :user_id
                AND status = ANY(:withdrawn_statuses)
            )
            SELECT 
                (SELECT total_earned FROM earned) - (SELECT total_withdrawn FROM withdrawn) as withdrawable_balance
        """)
        
        result = self.db.execute(query, {
            "user_id": user_id,
            "paid_statuses": PAID_STATUSES,
            "withdrawn_statuses": COMPLETED_WITHDRAWAL_STATUSES
        }).first()
        
        return Decimal(str(result[0])) if result else Decimal('0.0')
    
    def get_income_breakdown(self, user_id: str) -> Dict:
        """Get detailed income breakdown by status for analysis"""
        query = text("""
            SELECT 
                verification_status,
                COUNT(*) as count,
                COALESCE(SUM(net_amount), 0.0) as total_amount
            FROM pending_income
            WHERE user_id = :user_id
            GROUP BY verification_status
            ORDER BY verification_status
        """)
        
        results = self.db.execute(query, {"user_id": user_id}).fetchall()
        
        breakdown = {}
        for row in results:
            breakdown[row[0]] = {
                "count": row[1],
                "total_amount": float(row[2])
            }
        
        return breakdown
    
    def get_withdrawal_breakdown(self, user_id: str) -> Dict:
        """Get withdrawal breakdown by status for analysis"""
        query = text("""
            SELECT 
                status,
                COUNT(*) as count,
                COALESCE(SUM(final_payout), 0.0) as total_amount
            FROM withdrawal_request
            WHERE user_id = :user_id
            GROUP BY status
            ORDER BY status
        """)
        
        results = self.db.execute(query, {"user_id": user_id}).fetchall()
        
        breakdown = {}
        for row in results:
            breakdown[row[0]] = {
                "count": row[1],
                "total_amount": float(row[2])
            }
        
        return breakdown
    
    def analyze_user(self, user: User) -> Dict:
        """
        Analyze single user wallet reconciliation
        
        Returns:
            dict: Reconciliation analysis for user
        """
        # Get stored values (current database columns)
        stored_earning = Decimal(str(user.earning_wallet or 0.0))
        stored_withdrawable = Decimal(str(user.withdrawable_wallet or 0.0))
        
        # Compute values using RFC v4.1 formulas
        computed_earning = self.compute_earning_wallet(user.id)
        computed_withdrawable = self.compute_withdrawable_wallet(user.id)
        
        # Calculate differences
        earning_diff = abs(stored_earning - computed_earning)
        withdrawable_diff = abs(stored_withdrawable - computed_withdrawable)
        
        # Tolerance: ±0.01 (1 paisa)
        TOLERANCE = Decimal('0.01')
        
        earning_match = earning_diff <= TOLERANCE
        withdrawable_match = withdrawable_diff <= TOLERANCE
        perfect_match = earning_match and withdrawable_match
        
        analysis = {
            "user_id": user.id,
            "stored": {
                "earning_wallet": float(stored_earning),
                "withdrawable_wallet": float(stored_withdrawable)
            },
            "computed": {
                "earning_wallet": float(computed_earning),
                "withdrawable_wallet": float(computed_withdrawable)
            },
            "differences": {
                "earning_wallet": float(earning_diff),
                "withdrawable_wallet": float(withdrawable_diff)
            },
            "matches": {
                "earning_wallet": earning_match,
                "withdrawable_wallet": withdrawable_match,
                "perfect_match": perfect_match
            }
        }
        
        # If mismatch, get detailed breakdown
        if not perfect_match:
            analysis["income_breakdown"] = self.get_income_breakdown(user.id)
            analysis["withdrawal_breakdown"] = self.get_withdrawal_breakdown(user.id)
        
        return analysis
    
    def run_full_analysis(self, sample_size: Optional[int] = None) -> Dict:
        """
        Run complete reconciliation analysis
        
        Args:
            sample_size: If provided, analyze only first N users (for testing)
        
        Returns:
            dict: Complete reconciliation report
        """
        logger.info("=" * 70)
        logger.info("DC PROTOCOL PHASE 1.2: RECONCILIATION DATASET BUILD")
        logger.info("RFC Version: v4.1 (Architect-Approved Final)")
        logger.info("=" * 70)
        
        # Get all users (or sample)
        query = self.db.query(User)
        if sample_size:
            query = query.limit(sample_size)
            logger.info(f"Analyzing SAMPLE: First {sample_size} users")
        else:
            logger.info("Analyzing ALL users")
        
        users = query.all()
        self.results["total_users"] = len(users)
        
        logger.info(f"Total users to analyze: {len(users)}")
        
        # Analyze each user
        perfect_matches = 0
        earning_mismatches = 0
        withdrawable_mismatches = 0
        both_mismatches = 0
        
        for i, user in enumerate(users, 1):
            if i % 100 == 0:
                logger.info(f"Progress: {i}/{len(users)} users analyzed...")
            
            analysis = self.analyze_user(user)
            
            if analysis["matches"]["perfect_match"]:
                perfect_matches += 1
            else:
                self.results["discrepancies"].append(analysis)
                
                if not analysis["matches"]["earning_wallet"]:
                    earning_mismatches += 1
                if not analysis["matches"]["withdrawable_wallet"]:
                    withdrawable_mismatches += 1
                if not analysis["matches"]["earning_wallet"] and not analysis["matches"]["withdrawable_wallet"]:
                    both_mismatches += 1
        
        # Calculate reconciliation rate
        reconciliation_rate = (perfect_matches / len(users) * 100) if users else 0.0
        
        # Build summary
        self.results["summary"] = {
            "total_users": len(users),
            "perfect_matches": perfect_matches,
            "total_discrepancies": len(self.results["discrepancies"]),
            "earning_wallet_mismatches": earning_mismatches,
            "withdrawable_wallet_mismatches": withdrawable_mismatches,
            "both_wallets_mismatched": both_mismatches,
            "reconciliation_rate_percent": round(reconciliation_rate, 4),
            "target_rate_percent": 99.95,
            "meets_target": reconciliation_rate >= 99.95
        }
        
        self.results["reconciliation_rate"] = reconciliation_rate
        self.results["perfect_matches"] = perfect_matches
        
        # Log summary
        logger.info("")
        logger.info("=" * 70)
        logger.info("RECONCILIATION ANALYSIS COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Total Users Analyzed:     {len(users):,}")
        logger.info(f"Perfect Matches:          {perfect_matches:,} ({reconciliation_rate:.2f}%)")
        logger.info(f"Total Discrepancies:      {len(self.results['discrepancies']):,}")
        logger.info(f"  - Earning Mismatches:   {earning_mismatches:,}")
        logger.info(f"  - Withdrawable Mismatches: {withdrawable_mismatches:,}")
        logger.info(f"  - Both Mismatched:      {both_mismatches:,}")
        logger.info("")
        logger.info(f"Reconciliation Rate:      {reconciliation_rate:.4f}%")
        logger.info(f"Target Rate:              99.95%")
        logger.info(f"Meets Target:             {'✓ YES' if reconciliation_rate >= 99.95 else '✗ NO'}")
        logger.info("=" * 70)
        
        return self.results
    
    def save_report(self, output_path: str):
        """Save reconciliation report to JSON file"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"Report saved to: {output_path}")
        
        # Also save top 10 discrepancies for quick review
        if self.results["discrepancies"]:
            top_10_path = output_path.replace('.json', '_top10.json')
            top_10 = sorted(
                self.results["discrepancies"],
                key=lambda x: x["differences"]["earning_wallet"] + x["differences"]["withdrawable_wallet"],
                reverse=True
            )[:10]
            
            with open(top_10_path, 'w') as f:
                json.dump({
                    "metadata": self.results["metadata"],
                    "summary": self.results["summary"],
                    "top_10_discrepancies": top_10
                }, f, indent=2)
            
            logger.info(f"Top 10 discrepancies saved to: {top_10_path}")
    
    def generate_human_readable_report(self, output_path: str):
        """Generate human-readable markdown report"""
        md_path = output_path.replace('.json', '.md')
        
        with open(md_path, 'w') as f:
            f.write("# DC Protocol Phase 1.2: Reconciliation Analysis Report\n\n")
            f.write(f"**Generated**: {self.results['metadata']['timestamp']}\n")
            f.write(f"**RFC Version**: {self.results['metadata']['rfc_version']}\n\n")
            
            f.write("## Executive Summary\n\n")
            summary = self.results["summary"]
            f.write(f"- **Total Users Analyzed**: {summary['total_users']:,}\n")
            f.write(f"- **Perfect Matches**: {summary['perfect_matches']:,}\n")
            f.write(f"- **Reconciliation Rate**: {summary['reconciliation_rate_percent']:.4f}%\n")
            f.write(f"- **Target Rate**: {summary['target_rate_percent']}%\n")
            f.write(f"- **Meets Target**: {'✓ YES' if summary['meets_target'] else '✗ NO'}\n\n")
            
            f.write("## Discrepancy Breakdown\n\n")
            f.write(f"- **Total Discrepancies**: {summary['total_discrepancies']:,}\n")
            f.write(f"- **Earning Wallet Mismatches**: {summary['earning_wallet_mismatches']:,}\n")
            f.write(f"- **Withdrawable Wallet Mismatches**: {summary['withdrawable_wallet_mismatches']:,}\n")
            f.write(f"- **Both Wallets Mismatched**: {summary['both_wallets_mismatched']:,}\n\n")
            
            f.write("## RFC v4.1 Formulas Used\n\n")
            f.write("### Earning Wallet\n")
            f.write("```\n")
            f.write("SUM(pending_income WHERE verification_status IN [\n")
            for status in UNPAID_STATUSES:
                f.write(f"  '{status}',\n")
            f.write("])\n```\n\n")
            
            f.write("### Withdrawable Wallet\n")
            f.write("```\n")
            f.write("SUM(pending_income WHERE status IN ['Finance Paid', 'Accounts Paid'])\n")
            f.write("- SUM(withdrawal_request WHERE status IN ['Bank Sent', 'Completed'])\n")
            f.write("```\n\n")
            
            if self.results["discrepancies"]:
                f.write("## Top 10 Largest Discrepancies\n\n")
                top_10 = sorted(
                    self.results["discrepancies"],
                    key=lambda x: x["differences"]["earning_wallet"] + x["differences"]["withdrawable_wallet"],
                    reverse=True
                )[:10]
                
                f.write("| User ID | Earning Diff (₹) | Withdrawable Diff (₹) | Total Diff (₹) |\n")
                f.write("|---------|------------------|----------------------|----------------|\n")
                for disc in top_10:
                    earning_diff = disc["differences"]["earning_wallet"]
                    withdrawable_diff = disc["differences"]["withdrawable_wallet"]
                    total_diff = earning_diff + withdrawable_diff
                    f.write(f"| {disc['user_id']} | {earning_diff:.2f} | {withdrawable_diff:.2f} | {total_diff:.2f} |\n")
            
            f.write("\n## Next Steps\n\n")
            if summary['meets_target']:
                f.write("✓ Reconciliation rate meets 99.95% target.\n")
                f.write("✓ Safe to proceed to Phase 1.3 (Materialized Views).\n")
            else:
                f.write("✗ Reconciliation rate below 99.95% target.\n")
                f.write("✗ Investigate discrepancies before proceeding.\n")
                f.write("✗ Review income_breakdown and withdrawal_breakdown in full JSON report.\n")
        
        logger.info(f"Human-readable report saved to: {md_path}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='DC Protocol Phase 1.2: Reconciliation Analysis')
    parser.add_argument('--output', default='reports/dc_reconciliation_baseline.json',
                       help='Output JSON file path')
    parser.add_argument('--sample', type=int, default=None,
                       help='Analyze only first N users (for testing)')
    
    args = parser.parse_args()
    
    # Get database session
    db = next(get_db())
    
    try:
        # Create analyzer
        analyzer = ReconciliationAnalyzer(db)
        
        # Run analysis
        results = analyzer.run_full_analysis(sample_size=args.sample)
        
        # Save reports
        analyzer.save_report(args.output)
        analyzer.generate_human_readable_report(args.output)
        
        # Exit code based on reconciliation rate
        if results["summary"]["meets_target"]:
            logger.info("")
            logger.info("✓ SUCCESS: Reconciliation rate meets target (≥99.95%)")
            logger.info("✓ Safe to proceed to Phase 1.3")
            sys.exit(0)
        else:
            logger.warning("")
            logger.warning("⚠ WARNING: Reconciliation rate below target (<99.95%)")
            logger.warning("⚠ Review discrepancies before proceeding")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"ERROR: {e}", exc_info=True)
        sys.exit(2)
    
    finally:
        db.close()


if __name__ == '__main__':
    main()
