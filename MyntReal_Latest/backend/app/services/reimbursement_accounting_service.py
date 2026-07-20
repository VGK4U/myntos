"""
Staff Reimbursement Accounting Service
DC Protocol Compliant - Company-wise ledger integration

Handles:
- ExpenseEntry creation from settled claims
- PartyLedger DEBIT entries for employee payouts
- BalanceSheetSummary updates
- Company/Employee/Expense-wise breakdown

Created: Dec 19, 2025
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.staff_accounts import (
    StaffReimbursementClaim,
    StaffReimbursementClaimItem,
    ExpenseEntry,
    PartyLedger,
    BalanceSheetSummary,
    AssociatedCompany,
    PaymentTransaction,
    FundAllocation,
    EmployeeFundLedger
)
from app.models.staff import StaffEmployee
from app.models.expense_category import ExpenseMainCategory
from app.models.base import get_indian_time


class ReimbursementAccountingService:
    """
    Service for integrating reimbursement claims with SFMS accounting.
    DC Protocol: All operations are company-scoped.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def settle_claim_with_accounting(
        self,
        claim: StaffReimbursementClaim,
        settled_by_id: int,
        settlement_mode: str,
        settlement_reference: Optional[str] = None,
        fund_allocation_id: Optional[int] = None,
        remarks: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete settlement of a claim with full accounting integration.
        
        Creates:
        1. ExpenseEntry for the claim (debit expense)
        2. PartyLedger DEBIT entry for employee payout (liability extinction)
        3. PaymentTransaction/FundLedger DEBIT for cash/bank/fund outflow
        4. Updates BalanceSheetSummary
        
        Double-Entry Accounting:
        - BANK_TRANSFER: Creates PaymentTransaction debiting bank ledger
        - CASH: Creates PaymentTransaction debiting cash ledger
        - FUND_ALLOCATION: Decrements FundAllocation balance + EmployeeFundLedger entry
        
        Returns dict with created record IDs and status.
        DC Protocol: Ensures company_id segregation throughout.
        
        Note: Transaction management is handled by the calling API endpoint.
        This method does NOT commit - caller must commit after all updates.
        """
        claim.settlement_mode = settlement_mode
        claim.settlement_reference = settlement_reference
        claim.fund_allocation_id = fund_allocation_id
        
        expense_entry = self._create_expense_entry(claim, settled_by_id, settlement_mode)
        
        ledger_entry = self._create_party_ledger_entry(
            claim, expense_entry.id, settled_by_id
        )
        
        source_result = self._create_settlement_source_debit(
            claim=claim,
            expense_entry_id=expense_entry.id,
            settlement_mode=settlement_mode,
            settlement_reference=settlement_reference,
            fund_allocation_id=fund_allocation_id,
            created_by_id=settled_by_id
        )
        
        self._update_balance_sheet_summary(claim)
        
        claim.expense_entry_id = expense_entry.id
        claim.settled_at = get_indian_time()
        claim.settled_by_id = settled_by_id
        claim.status = 'SETTLED'
        claim.finance_remarks = remarks
        
        claim.add_audit_entry('SETTLED_WITH_ACCOUNTING', settled_by_id, {
            'expense_entry_id': expense_entry.id,
            'ledger_entry_id': ledger_entry.id,
            'payment_transaction_id': source_result.get('payment_transaction_id'),
            'fund_ledger_entry_id': source_result.get('fund_ledger_entry_id'),
            'settlement_mode': settlement_mode,
            'settlement_reference': settlement_reference,
            'total_amount': float(claim.total_amount)
        })
        
        return {
            'success': True,
            'claim_id': claim.id,
            'expense_entry_id': expense_entry.id,
            'ledger_entry_id': ledger_entry.id,
            'payment_transaction_id': source_result.get('payment_transaction_id'),
            'fund_ledger_entry_id': source_result.get('fund_ledger_entry_id'),
            'message': 'Claim settled with full double-entry accounting'
        }
    
    def _create_expense_entry(
        self,
        claim: StaffReimbursementClaim,
        created_by_id: int,
        settlement_mode: str
    ) -> ExpenseEntry:
        """
        Create ExpenseEntry from settled claim.
        DC Protocol: company_id from claim.
        """
        category_breakdown = self._get_category_breakdown(claim)
        
        expense_metadata = {
            'claim_number': claim.claim_number,
            'claim_title': claim.claim_title,
            'employee_id': claim.employee_id,
            'employee_code': claim.employee.emp_code if claim.employee else None,
            'employee_name': claim.employee.full_name if claim.employee else None,
            'is_travel_claim': claim.is_travel_claim,
            'travel_details': {
                'mode': claim.travel_mode,
                'from': claim.travel_from,
                'to': claim.travel_to,
                'distance_km': float(claim.distance_km) if claim.distance_km else None
            } if claim.is_travel_claim else None,
            'category_breakdown': category_breakdown,
            'item_count': len(claim.items) if claim.items else 0,
            'items': [item.to_dict() for item in claim.items] if claim.items else []
        }
        
        primary_category = None
        if category_breakdown:
            primary_category = max(category_breakdown, key=lambda x: x['amount'])['category_name']
        
        expense_entry = ExpenseEntry(
            company_id=claim.company_id,
            segment_id=claim.segment_id,
            expense_date=claim.claim_period_to or date.today(),
            category=primary_category or 'Staff Reimbursement',
            description=f"Reimbursement: {claim.claim_title}",
            amount=claim.total_amount,
            payment_mode=settlement_mode or 'FUND_ALLOCATION',
            reference_number=claim.claim_number,
            vendor_name=claim.employee.full_name if claim.employee else 'Employee',
            notes=claim.claim_description,
            expense_metadata=expense_metadata,
            status='APPROVED',
            approved_by_id=created_by_id,
            approved_at=get_indian_time(),
            ledger_updated=True,
            created_by_id=created_by_id
        )
        
        self.db.add(expense_entry)
        self.db.flush()
        
        return expense_entry
    
    def _create_party_ledger_entry(
        self,
        claim: StaffReimbursementClaim,
        expense_entry_id: int,
        created_by_id: int
    ) -> PartyLedger:
        """
        Create PartyLedger DEBIT entry for employee payout.
        DC Protocol: company_id from claim.
        """
        latest_entry = self.db.query(PartyLedger).filter(
            PartyLedger.company_id == claim.company_id,
            PartyLedger.party_type == 'EMPLOYEE',
            PartyLedger.party_id == claim.employee_id
        ).order_by(
            PartyLedger.transaction_date.desc(),
            PartyLedger.id.desc()
        ).first()
        
        last_balance = latest_entry.running_balance if latest_entry else Decimal('0')
        new_balance = last_balance - claim.total_amount
        
        ledger_entry = PartyLedger(
            company_id=claim.company_id,
            segment_id=claim.segment_id,
            party_type='EMPLOYEE',
            party_id=claim.employee_id,
            transaction_date=get_indian_time().date(),
            entry_type='DEBIT',
            amount=claim.total_amount,
            running_balance=new_balance,
            reference_type='REIMBURSEMENT',
            reference_id=claim.id,
            reference_number=claim.claim_number,
            narration=f"Reimbursement payout: {claim.claim_title}",
            created_by_id=created_by_id
        )
        
        self.db.add(ledger_entry)
        self.db.flush()
        
        return ledger_entry
    
    def _create_settlement_source_debit(
        self,
        claim: StaffReimbursementClaim,
        expense_entry_id: int,
        settlement_mode: str,
        settlement_reference: Optional[str],
        fund_allocation_id: Optional[int],
        created_by_id: int
    ) -> Dict[str, Any]:
        """
        Create settlement source debit entry based on payment mode.
        DC Protocol: company_id from claim.
        
        Double-Entry Logic:
        - BANK_TRANSFER: Creates PaymentTransaction (debits bank ledger)
        - CASH: Creates PaymentTransaction (debits cash ledger)
        - FUND_ALLOCATION: Decrements FundAllocation + creates EmployeeFundLedger entry
        """
        result = {
            'payment_transaction_id': None,
            'fund_ledger_entry_id': None,
            'fund_allocation_updated': False
        }
        
        if settlement_mode in ['BANK_TRANSFER', 'CASH']:
            payment_txn = self._create_payment_transaction(
                claim=claim,
                expense_entry_id=expense_entry_id,
                settlement_mode=settlement_mode,
                settlement_reference=settlement_reference,
                created_by_id=created_by_id
            )
            result['payment_transaction_id'] = payment_txn.id
            
        elif settlement_mode == 'FUND_ALLOCATION' and fund_allocation_id:
            fund_result = self._process_fund_allocation_debit(
                claim=claim,
                fund_allocation_id=fund_allocation_id,
                created_by_id=created_by_id
            )
            result['fund_ledger_entry_id'] = fund_result.get('ledger_entry_id')
            result['fund_allocation_updated'] = fund_result.get('allocation_updated', False)
        
        return result
    
    def _create_payment_transaction(
        self,
        claim: StaffReimbursementClaim,
        expense_entry_id: int,
        settlement_mode: str,
        settlement_reference: Optional[str],
        created_by_id: int
    ) -> PaymentTransaction:
        """
        Create PaymentTransaction for cash/bank settlement.
        This debits the company's cash or bank ledger.
        DC Protocol: company_id from claim.
        """
        txn_date = get_indian_time()
        txn_number = f"REIMB-PAY-{claim.company_id}-{txn_date.strftime('%Y%m%d%H%M%S')}"
        
        payment_mode = 'BANK' if settlement_mode == 'BANK_TRANSFER' else 'CASH'
        
        payment_txn = PaymentTransaction(
            transaction_number=txn_number,
            transaction_type='PAYMENT_TO_VENDOR',
            company_id=claim.company_id,
            source_type='OTHER',
            source_id=claim.id,
            party_type='EMPLOYEE',
            party_id=claim.employee_id,
            party_name=claim.employee.full_name if claim.employee else 'Employee',
            transaction_date=txn_date.date(),
            amount=claim.total_amount,
            payment_mode=payment_mode,
            payment_reference=settlement_reference,
            narration=f"Reimbursement settlement: {claim.claim_number} - {claim.claim_title}",
            status='COMPLETED',
            created_by_id=created_by_id,
            ledger_entry_id=expense_entry_id
        )
        
        self.db.add(payment_txn)
        self.db.flush()
        
        return payment_txn
    
    def _process_fund_allocation_debit(
        self,
        claim: StaffReimbursementClaim,
        fund_allocation_id: int,
        created_by_id: int
    ) -> Dict[str, Any]:
        """
        Process fund allocation debit for reimbursement settlement.
        - Decrements FundAllocation.balance_remaining
        - Increments FundAllocation.total_expensed
        - Creates EmployeeFundLedger entry
        DC Protocol: Validates fund belongs to same company.
        
        Raises ValueError for validation failures to trigger API rollback.
        """
        result = {'ledger_entry_id': None, 'allocation_updated': False}
        
        fund = self.db.query(FundAllocation).with_for_update().filter(
            FundAllocation.id == fund_allocation_id,
            FundAllocation.company_id == claim.company_id
        ).first()
        
        if not fund:
            raise ValueError(f"Fund allocation #{fund_allocation_id} not found or belongs to different company")
        
        if fund.status not in ['CONFIRMED', 'PARTIALLY_SETTLED']:
            raise ValueError(f"Fund allocation status '{fund.status}' is not valid for settlement")
        
        if fund.balance_remaining < claim.total_amount:
            raise ValueError(f"Insufficient fund balance. Available: ₹{fund.balance_remaining}, Required: ₹{claim.total_amount}")
        
        fund.balance_remaining = fund.balance_remaining - claim.total_amount
        fund.total_expensed = (fund.total_expensed or Decimal('0')) + claim.total_amount
        
        if fund.balance_remaining <= 0:
            fund.status = 'SETTLED'
            fund.settlement_date = get_indian_time().date()
        elif fund.total_expensed > 0:
            fund.status = 'PARTIALLY_SETTLED'
        
        result['allocation_updated'] = True
        
        latest_fund_entry = self.db.query(EmployeeFundLedger).filter(
            EmployeeFundLedger.employee_id == claim.employee_id,
            EmployeeFundLedger.company_id == claim.company_id
        ).order_by(
            EmployeeFundLedger.transaction_date.desc(),
            EmployeeFundLedger.id.desc()
        ).first()
        
        last_balance = latest_fund_entry.balance if latest_fund_entry else Decimal('0')
        new_balance = last_balance - claim.total_amount
        
        fund_ledger = EmployeeFundLedger(
            employee_id=claim.employee_id,
            company_id=claim.company_id,
            transaction_date=get_indian_time().date(),
            entry_type='EXPENSE_MADE',
            reference_type='EXPENSE_ENTRY',
            reference_id=claim.id,
            reference_number=claim.claim_number,
            debit_amount=Decimal('0'),
            credit_amount=claim.total_amount,
            balance=new_balance,
            narration=f"Reimbursement from fund: {claim.claim_title}",
            updated_by_id=created_by_id
        )
        
        self.db.add(fund_ledger)
        self.db.flush()
        
        result['ledger_entry_id'] = fund_ledger.id
        
        return result
    
    def _update_balance_sheet_summary(self, claim: StaffReimbursementClaim):
        """
        Update BalanceSheetSummary for the company.
        DC Protocol: Updates only the claim's company.
        """
        today = date.today()
        
        category_breakdown = self._get_category_breakdown(claim)
        category_amounts = {cat['category_name']: cat['amount'] for cat in category_breakdown}
        
        for period_type in ['DAILY', 'MONTHLY']:
            if period_type == 'DAILY':
                period_date = today
            else:
                period_date = today.replace(day=1)
            
            fy_year = today.year if today.month >= 4 else today.year - 1
            financial_year = f"{fy_year}-{str(fy_year + 1)[-2:]}"
            
            existing = self.db.query(BalanceSheetSummary).filter(
                BalanceSheetSummary.company_id == claim.company_id,
                BalanceSheetSummary.period_type == period_type,
                BalanceSheetSummary.period_date == period_date
            ).first()
            
            if existing:
                existing.total_expense = (existing.total_expense or Decimal('0')) + claim.total_amount
                
                current_by_cat = existing.expense_by_category or {}
                for cat_name, amount in category_amounts.items():
                    current_by_cat[cat_name] = float(current_by_cat.get(cat_name, 0)) + amount
                existing.expense_by_category = current_by_cat
                
                existing.net_balance = (existing.total_income or Decimal('0')) - existing.total_expense
                existing.updated_at = get_indian_time()
            else:
                new_summary = BalanceSheetSummary(
                    company_id=claim.company_id,
                    period_type=period_type,
                    period_date=period_date,
                    financial_year=financial_year,
                    total_income=Decimal('0'),
                    total_expense=claim.total_amount,
                    expense_by_category=category_amounts,
                    pending_payouts=Decimal('0'),
                    pending_awards=Decimal('0'),
                    pending_allowances=Decimal('0'),
                    total_liability=Decimal('0'),
                    net_balance=-claim.total_amount
                )
                self.db.add(new_summary)
    
    def _get_category_breakdown(self, claim: StaffReimbursementClaim) -> List[Dict]:
        """
        Get expense breakdown by category from claim items.
        """
        breakdown = {}
        
        if not claim.items:
            return []
        
        for item in claim.items:
            cat_name = 'Uncategorized'
            if item.main_category_id:
                category = self.db.query(ExpenseMainCategory).filter(
                    ExpenseMainCategory.id == item.main_category_id
                ).first()
                if category:
                    cat_name = category.name
            
            if cat_name not in breakdown:
                breakdown[cat_name] = Decimal('0')
            breakdown[cat_name] += item.amount
        
        return [
            {'category_name': name, 'amount': float(amount)}
            for name, amount in breakdown.items()
        ]
    
    def get_employee_expense_ledger(
        self,
        company_id: int,
        employee_id: int,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get expense ledger for a specific employee in a company.
        DC Protocol: Filters by company_id.
        """
        query = self.db.query(PartyLedger).filter(
            PartyLedger.company_id == company_id,
            PartyLedger.party_type == 'EMPLOYEE',
            PartyLedger.party_id == employee_id,
            PartyLedger.reference_type == 'REIMBURSEMENT'
        )
        
        if from_date:
            query = query.filter(PartyLedger.transaction_date >= from_date)
        if to_date:
            query = query.filter(PartyLedger.transaction_date <= to_date)
        
        entries = query.order_by(PartyLedger.transaction_date.desc()).all()
        
        total_paid = sum(e.amount for e in entries if e.entry_type == 'DEBIT')
        
        return {
            'company_id': company_id,
            'employee_id': employee_id,
            'entries': [e.to_dict() for e in entries],
            'total_count': len(entries),
            'total_paid': float(total_paid)
        }
    
    def get_company_expense_summary(
        self,
        company_id: int,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get expense summary for a company.
        DC Protocol: Filters by company_id.
        """
        query = self.db.query(
            ExpenseEntry.category,
            func.count(ExpenseEntry.id).label('count'),
            func.sum(ExpenseEntry.amount).label('total')
        ).filter(
            ExpenseEntry.company_id == company_id,
            ExpenseEntry.status == 'APPROVED'
        )
        
        if from_date:
            query = query.filter(ExpenseEntry.expense_date >= from_date)
        if to_date:
            query = query.filter(ExpenseEntry.expense_date <= to_date)
        
        by_category = query.group_by(ExpenseEntry.category).all()
        
        employee_query = self.db.query(
            PartyLedger.party_id,
            func.sum(PartyLedger.amount).label('total')
        ).filter(
            PartyLedger.company_id == company_id,
            PartyLedger.party_type == 'EMPLOYEE',
            PartyLedger.reference_type == 'REIMBURSEMENT',
            PartyLedger.entry_type == 'DEBIT'
        )
        
        if from_date:
            employee_query = employee_query.filter(PartyLedger.transaction_date >= from_date)
        if to_date:
            employee_query = employee_query.filter(PartyLedger.transaction_date <= to_date)
        
        by_employee = employee_query.group_by(PartyLedger.party_id).all()
        
        employee_names = {}
        if by_employee:
            emp_ids = [e[0] for e in by_employee]
            employees = self.db.query(StaffEmployee).filter(
                StaffEmployee.id.in_(emp_ids)
            ).all()
            employee_names = {e.id: e.full_name for e in employees}
        
        return {
            'company_id': company_id,
            'by_category': [
                {'category': cat or 'Uncategorized', 'count': cnt, 'total': float(tot or 0)}
                for cat, cnt, tot in by_category
            ],
            'by_employee': [
                {
                    'employee_id': emp_id,
                    'employee_name': employee_names.get(emp_id, 'Unknown'),
                    'total': float(tot or 0)
                }
                for emp_id, tot in by_employee
            ],
            'grand_total': sum(float(tot or 0) for _, _, tot in by_category)
        }
