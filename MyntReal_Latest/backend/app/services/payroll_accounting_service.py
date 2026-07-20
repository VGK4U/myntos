"""
Staff Payroll Accounting Service
DC Protocol Compliant - Company-wise ledger integration

Indian Accounting Standards for Payroll:
=========================================
When payroll is approved (Accrual Entry):
  Dr. Salary & Wages Expense          (CTC Cost = Gross + Employer Contributions)
    Cr. PF Payable - Employee Share   (12% of Basic, max 1800)
    Cr. PF Payable - Employer Share   (12% of Basic, max 1800)
    Cr. ESI Payable - Employee Share  (0.75% of Gross, if applicable)
    Cr. ESI Payable - Employer Share  (3.25% of Gross, if applicable)
    Cr. Professional Tax Payable      (State-wise, max 200/month)
    Cr. TDS Payable (Section 192)     (As per tax slab)
    Cr. Salary Payable                (Net Pay to employee)

When salary is paid (Payment Entry):
  Dr. Salary Payable                  (Net Pay)
    Cr. Bank                          (Net Pay)

When statutory dues are paid:
  Dr. PF Payable (Employee + Employer)
    Cr. Bank
  Dr. ESI Payable (Employee + Employer)
    Cr. Bank
  Dr. TDS Payable
    Cr. Bank

Created: Jan 08, 2026
DC Protocol: All operations are company-scoped
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.staff_accounts import (
    ExpenseEntry,
    PartyLedger,
    AssociatedCompany
)
from app.models.expense_category import ExpenseMainCategory, ExpenseSubCategory
from app.models.staff_payroll import StaffPayrollRun, StaffPayrollCycle, StaffPayrollAuditLog
from app.models.staff import StaffEmployee
from app.models.base import get_indian_time

import logging
logger = logging.getLogger(__name__)


EXPENSE_CATEGORY_SALARY = "SALARY"
EXPENSE_SUBCATEGORY_WAGES = "WAGES"

PAYABLE_TYPES = {
    'SALARY': 'Salary Payable',
    'PF_EMPLOYEE': 'PF Payable - Employee',
    'PF_EMPLOYER': 'PF Payable - Employer',
    'ESI_EMPLOYEE': 'ESI Payable - Employee',
    'ESI_EMPLOYER': 'ESI Payable - Employer',
    'PT': 'Professional Tax Payable',
    'TDS': 'TDS Payable (Section 192)'
}


class PayrollAccountingService:
    """
    Service for integrating payroll with SFMS accounting.
    DC Protocol: All operations are company-scoped.
    
    Implements proper Indian double-entry accounting for payroll.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def post_payroll_run_to_sfms(
        self,
        run: StaffPayrollRun,
        posted_by_id: int
    ) -> Dict[str, Any]:
        """
        Post approved payroll run to SFMS with full double-entry accounting.
        
        Creates:
        1. ExpenseEntry for salary expense (debit)
        2. PartyLedger entries for all payables (credits):
           - Salary Payable (Net Pay)
           - PF Payable Employee/Employer
           - ESI Payable Employee/Employer
           - PT Payable
           - TDS Payable
        
        Returns dict with created record IDs and status.
        DC Protocol: Ensures company_id segregation throughout.
        
        Note: Transaction management is handled by the calling API endpoint.
        This method does NOT commit - caller must commit after all updates.
        """
        if run.sfms_posted:
            return {
                'success': True,
                'already_posted': True,
                'sfms_reference': run.sfms_reference,
                'message': 'Already posted to SFMS'
            }
        
        if run.status != 'APPROVED':
            return {
                'success': False,
                'error': 'Can only post approved payroll runs to SFMS'
            }
        
        cycle = self.db.query(StaffPayrollCycle).filter(
            StaffPayrollCycle.id == run.cycle_id
        ).first()
        
        employee = self.db.query(StaffEmployee).filter(
            StaffEmployee.id == run.employee_id
        ).first()
        
        if not cycle or not employee:
            return {
                'success': False,
                'error': 'Payroll cycle or employee not found'
            }
        
        import calendar
        month_name = calendar.month_name[cycle.month]
        year = cycle.year
        period_desc = f"{month_name} {year}"
        
        sfms_reference = f"SAL-{run.company_id}-{year}{cycle.month:02d}-{run.employee_id}"
        
        existing_expense = self.db.query(ExpenseEntry).filter(
            ExpenseEntry.entry_number == sfms_reference,
            ExpenseEntry.company_id == run.company_id
        ).first()
        
        if existing_expense:
            run.sfms_posted = True
            run.sfms_reference = sfms_reference
            run.sfms_posted_at = get_indian_time()
            run.sfms_posted_by = posted_by_id
            return {
                'success': True,
                'already_exists': True,
                'sfms_reference': sfms_reference,
                'expense_entry_id': existing_expense.id,
                'message': 'SFMS entries already exist'
            }
        
        ctc_cost = run.ctc_cost or (
            (run.gross_pay or Decimal('0')) + 
            (run.employer_contributions or Decimal('0'))
        )
        
        expense_entry = self._create_salary_expense_entry(
            run=run,
            cycle=cycle,
            employee=employee,
            period_desc=period_desc,
            sfms_reference=sfms_reference,
            ctc_cost=ctc_cost,
            created_by_id=posted_by_id
        )
        
        ledger_entries = self._create_payable_ledger_entries(
            run=run,
            cycle=cycle,
            employee=employee,
            expense_entry_id=expense_entry.id,
            period_desc=period_desc,
            sfms_reference=sfms_reference,
            created_by_id=posted_by_id
        )
        
        run.sfms_posted = True
        run.sfms_reference = sfms_reference
        run.sfms_posted_at = get_indian_time()
        run.sfms_posted_by = posted_by_id
        
        audit = StaffPayrollAuditLog(
            company_id=run.company_id,
            entity_type='PAYROLL_RUN',
            entity_id=run.id,
            action='SFMS_POSTED',
            action_details={
                'sfms_reference': sfms_reference,
                'expense_entry_id': expense_entry.id,
                'ledger_entries_created': len(ledger_entries),
                'ctc_cost': float(ctc_cost) if ctc_cost else 0,
                'net_pay': float(run.net_pay) if run.net_pay else 0,
                'accounting_breakdown': {
                    'salary_expense_dr': float(ctc_cost) if ctc_cost else 0,
                    'salary_payable_cr': float(run.net_pay) if run.net_pay else 0,
                    'pf_employee_cr': float(run.pf_employee or 0),
                    'pf_employer_cr': float(run.pf_employer or 0),
                    'esi_employee_cr': float(run.esi_employee or 0),
                    'esi_employer_cr': float(run.esi_employer or 0),
                    'pt_cr': float(run.pt_amount or 0),
                    'tds_cr': float(run.tds_amount or 0)
                }
            },
            performed_by=posted_by_id
        )
        self.db.add(audit)
        
        logger.info(f"[DC-PAYROLL-SFMS] Posted run {run.id} to SFMS: {sfms_reference}")
        
        return {
            'success': True,
            'sfms_reference': sfms_reference,
            'expense_entry_id': expense_entry.id,
            'ledger_entries_count': len(ledger_entries),
            'ledger_entry_ids': [e.id for e in ledger_entries],
            'accounting_summary': {
                'debit_salary_expense': float(ctc_cost) if ctc_cost else 0,
                'credit_total': float(ctc_cost) if ctc_cost else 0,
                'credits': {
                    'salary_payable': float(run.net_pay) if run.net_pay else 0,
                    'pf_employee': float(run.pf_employee or 0),
                    'pf_employer': float(run.pf_employer or 0),
                    'esi_employee': float(run.esi_employee or 0),
                    'esi_employer': float(run.esi_employer or 0),
                    'pt': float(run.pt_amount or 0),
                    'tds': float(run.tds_amount or 0)
                }
            },
            'message': 'Posted to SFMS with full double-entry accounting'
        }
    
    def _create_salary_expense_entry(
        self,
        run: StaffPayrollRun,
        cycle: StaffPayrollCycle,
        employee: StaffEmployee,
        period_desc: str,
        sfms_reference: str,
        ctc_cost: Decimal,
        created_by_id: int
    ) -> ExpenseEntry:
        """
        Create ExpenseEntry for salary expense (DEBIT side).
        DC Protocol: company_id from run.
        
        Salary Expense = CTC Cost = Gross Pay + Employer Contributions
        """
        salary_category = self.db.query(ExpenseMainCategory).filter(
            ExpenseMainCategory.category_code == EXPENSE_CATEGORY_SALARY,
            ExpenseMainCategory.company_id == run.company_id
        ).first()
        
        if not salary_category:
            salary_category = self.db.query(ExpenseMainCategory).filter(
                ExpenseMainCategory.category_code == EXPENSE_CATEGORY_SALARY
            ).first()
        
        salary_subcategory = None
        if salary_category:
            salary_subcategory = self.db.query(ExpenseSubCategory).filter(
                ExpenseSubCategory.main_category_id == salary_category.id
            ).first()
        
        expense_metadata = {
            'payroll_run_id': run.id,
            'cycle_id': cycle.id,
            'cycle_code': cycle.cycle_code,
            'employee_id': employee.id,
            'emp_code': employee.emp_code,
            'employee_name': employee.full_name or f"{employee.first_name} {employee.last_name}",
            'department': employee.department,
            'designation': employee.designation,
            'period': period_desc,
            'attendance': {
                'eligible_days': run.eligible_days,
                'paid_days': run.present_days,
                'lop_days': run.lop_days
            },
            'earnings': {
                'basic': float(run.basic_amount or 0),
                'hra': float(run.hra_amount or 0),
                'special_allowance': float(run.special_allowance or 0),
                'other_allowances': float(run.other_allowances or 0),
                'gross_pay': float(run.gross_pay or 0)
            },
            'deductions': {
                'pf_employee': float(run.pf_employee or 0),
                'esi_employee': float(run.esi_employee or 0),
                'pt': float(run.pt_amount or 0),
                'tds': float(run.tds_amount or 0),
                'other_deductions': float(run.other_deductions or 0),
                'total_deductions': float(run.total_deductions or 0)
            },
            'employer_contributions': {
                'pf_employer': float(run.pf_employer or 0),
                'esi_employer': float(run.esi_employer or 0),
                'total': float(run.employer_contributions or 0)
            },
            'summary': {
                'gross_pay': float(run.gross_pay or 0),
                'net_pay': float(run.net_pay or 0),
                'ctc_cost': float(ctc_cost or 0)
            }
        }
        
        if not salary_category or not salary_subcategory:
            logger.warning(f"[DC-PAYROLL-SFMS] Salary category not found for company {run.company_id}, auto-creating")
            return self._create_expense_entry_without_category(
                run, cycle, employee, period_desc, sfms_reference, ctc_cost, created_by_id
            )
        
        expense_entry = ExpenseEntry(
            entry_number=sfms_reference,
            company_id=run.company_id,
            main_category_id=salary_category.id,
            sub_category_id=salary_subcategory.id,
            expense_date=cycle.pay_date or get_indian_time().date(),
            amount=ctc_cost,
            payment_mode='NEFT',
            vendor_name=employee.full_name or f"{employee.first_name} {employee.last_name}",
            narration=f"Salary - {employee.full_name or employee.first_name} - {period_desc} | Run: {run.run_code}",
            related_entity_type='PAYROLL',
            related_entity_id=str(run.id),
            status='APPROVED',
            approved_by_id=created_by_id,
            approved_at=get_indian_time(),
            ledger_updated=True,
            created_by_id=created_by_id
        )
        
        self.db.add(expense_entry)
        self.db.flush()
        
        logger.info(f"[DC-PAYROLL-SFMS] Created expense entry {expense_entry.id}: ₹{ctc_cost}")
        
        return expense_entry
    
    def _create_expense_entry_without_category(
        self,
        run: StaffPayrollRun,
        cycle: StaffPayrollCycle,
        employee: StaffEmployee,
        period_desc: str,
        sfms_reference: str,
        ctc_cost: Decimal,
        created_by_id: int
    ) -> ExpenseEntry:
        """
        Create or get salary expense category, then create expense entry.
        Ensures SALARY category exists for proper accounting.
        """
        salary_category = self._ensure_salary_category_exists(run.company_id)
        salary_subcategory = self._ensure_salary_subcategory_exists(salary_category.id)
        
        expense_entry = ExpenseEntry(
            entry_number=sfms_reference,
            company_id=run.company_id,
            main_category_id=salary_category.id,
            sub_category_id=salary_subcategory.id,
            expense_date=cycle.pay_date or get_indian_time().date(),
            amount=ctc_cost,
            payment_mode='NEFT',
            vendor_name=employee.full_name or f"{employee.first_name} {employee.last_name}",
            narration=f"Salary - {employee.full_name or employee.first_name} - {period_desc} | Run: {run.run_code}",
            related_entity_type='PAYROLL',
            related_entity_id=str(run.id),
            status='APPROVED',
            approved_by_id=created_by_id,
            approved_at=get_indian_time(),
            ledger_updated=True,
            created_by_id=created_by_id
        )
        
        self.db.add(expense_entry)
        self.db.flush()
        
        logger.info(f"[DC-PAYROLL-SFMS] Created expense entry (with auto-created category) {expense_entry.id}: ₹{ctc_cost}")
        
        return expense_entry
    
    def _ensure_salary_category_exists(self, company_id: int) -> ExpenseMainCategory:
        """Ensure SALARY main category exists, create if not."""
        category = self.db.query(ExpenseMainCategory).filter(
            ExpenseMainCategory.category_code == 'SALARY',
            ExpenseMainCategory.company_id == company_id
        ).first()
        
        if not category:
            category = self.db.query(ExpenseMainCategory).filter(
                ExpenseMainCategory.category_code == 'SALARY'
            ).first()
        
        if not category:
            category = ExpenseMainCategory(
                company_id=company_id,
                category_code='SALARY',
                category_name='Salary & Wages',
                description='Employee salary and wages expense',
                gl_code='SAL001',
                is_active=True
            )
            self.db.add(category)
            self.db.flush()
            logger.info(f"[DC-PAYROLL-SFMS] Created SALARY main category for company {company_id}")
        
        return category
    
    def _ensure_salary_subcategory_exists(self, main_category_id: int) -> ExpenseSubCategory:
        """Ensure salary subcategory exists, create if not."""
        subcategory = self.db.query(ExpenseSubCategory).filter(
            ExpenseSubCategory.main_category_id == main_category_id
        ).first()
        
        if not subcategory:
            subcategory = ExpenseSubCategory(
                main_category_id=main_category_id,
                sub_category_code='SALARY_REGULAR',
                sub_category_name='Regular Salary',
                description='Regular monthly salary payments',
                gl_code='SAL001-01',
                is_active=True
            )
            self.db.add(subcategory)
            self.db.flush()
            logger.info(f"[DC-PAYROLL-SFMS] Created SALARY subcategory for category {main_category_id}")
        
        return subcategory
    
    def _create_payable_ledger_entries(
        self,
        run: StaffPayrollRun,
        cycle: StaffPayrollCycle,
        employee: StaffEmployee,
        expense_entry_id: int,
        period_desc: str,
        sfms_reference: str,
        created_by_id: int
    ) -> List[PartyLedger]:
        """
        Create PartyLedger CREDIT entries for all payables.
        DC Protocol: company_id from run.
        
        Creates separate liability entries for:
        1. Salary Payable (Net Pay to employee)
        2. PF Payable - Employee Share
        3. PF Payable - Employer Share
        4. ESI Payable - Employee Share
        5. ESI Payable - Employer Share
        6. Professional Tax Payable
        7. TDS Payable (Section 192)
        """
        entries = []
        emp_name = employee.full_name or f"{employee.first_name} {employee.last_name}"
        emp_code = employee.emp_code or str(employee.id)
        transaction_date = get_indian_time().date()
        
        if run.net_pay and run.net_pay > 0:
            entry = self._create_single_ledger_entry(
                run=run,
                party_type='EMPLOYEE',
                party_id=employee.id,
                party_name=f"{emp_name} ({emp_code})",
                entry_type='CREDIT',
                amount=run.net_pay,
                reference_number=sfms_reference,
                narration=f"Salary Payable - {emp_name} - {period_desc}",
                payable_type='SALARY',
                transaction_date=transaction_date,
                created_by_id=created_by_id
            )
            entries.append(entry)
        
        statutory_entries = [
            ('PF_EMPLOYEE', run.pf_employee, f"PF (Employee) - {emp_name} - {period_desc}"),
            ('PF_EMPLOYER', run.pf_employer, f"PF (Employer) - {emp_name} - {period_desc}"),
            ('ESI_EMPLOYEE', run.esi_employee, f"ESI (Employee) - {emp_name} - {period_desc}"),
            ('ESI_EMPLOYER', run.esi_employer, f"ESI (Employer) - {emp_name} - {period_desc}"),
            ('PT', run.pt_amount, f"Professional Tax - {emp_name} - {period_desc}"),
            ('TDS', run.tds_amount, f"TDS (Sec 192) - {emp_name} - {period_desc}")
        ]
        
        for payable_type, amount, narration in statutory_entries:
            if amount and amount > 0:
                if payable_type in ('PF_EMPLOYEE', 'PF_EMPLOYER'):
                    party_name = 'EPFO (Employees Provident Fund)'
                    party_type = 'EXTERNAL'
                    party_id = 1
                elif payable_type in ('ESI_EMPLOYEE', 'ESI_EMPLOYER'):
                    party_name = 'ESIC (Employees State Insurance)'
                    party_type = 'EXTERNAL'
                    party_id = 2
                elif payable_type == 'PT':
                    party_name = 'State Government - Professional Tax'
                    party_type = 'EXTERNAL'
                    party_id = 3
                else:
                    party_name = 'Income Tax Department - TDS'
                    party_type = 'EXTERNAL'
                    party_id = 4
                
                entry = self._create_single_ledger_entry(
                    run=run,
                    party_type=party_type,
                    party_id=party_id,
                    party_name=party_name,
                    entry_type='CREDIT',
                    amount=amount,
                    reference_number=sfms_reference,
                    narration=narration,
                    payable_type=payable_type,
                    transaction_date=transaction_date,
                    created_by_id=created_by_id
                )
                entries.append(entry)
        
        logger.info(f"[DC-PAYROLL-SFMS] Created {len(entries)} ledger entries for run {run.id}")
        
        return entries
    
    def _create_single_ledger_entry(
        self,
        run: StaffPayrollRun,
        party_type: str,
        party_id: int,
        party_name: str,
        entry_type: str,
        amount: Decimal,
        reference_number: str,
        narration: str,
        payable_type: str,
        transaction_date: date,
        created_by_id: int
    ) -> PartyLedger:
        """
        Create a single PartyLedger entry.
        DC Protocol: company_id from run.
        """
        latest_entry = self.db.query(PartyLedger).filter(
            PartyLedger.company_id == run.company_id,
            PartyLedger.party_type == party_type,
            PartyLedger.party_id == party_id
        ).order_by(
            PartyLedger.transaction_date.desc(),
            PartyLedger.id.desc()
        ).first()
        
        last_balance = latest_entry.running_balance if latest_entry else Decimal('0')
        
        if entry_type == 'CREDIT':
            new_balance = last_balance + amount
            debit_amount = Decimal('0')
            credit_amount = amount
        else:
            new_balance = last_balance - amount
            debit_amount = amount
            credit_amount = Decimal('0')
        
        ledger_entry = PartyLedger(
            company_id=run.company_id,
            party_type=party_type,
            party_id=party_id,
            party_name=party_name,
            transaction_date=transaction_date,
            entry_type=entry_type,
            debit_amount=debit_amount,
            credit_amount=credit_amount,
            running_balance=new_balance,
            reference_type='EXPENSE',
            reference_id=run.id,
            reference_number=reference_number,
            narration=narration
        )
        
        self.db.add(ledger_entry)
        self.db.flush()
        
        return ledger_entry
    
    def batch_post_payroll_cycle_to_sfms(
        self,
        cycle: StaffPayrollCycle,
        posted_by_id: int
    ) -> Dict[str, Any]:
        """
        Post all approved runs in a cycle to SFMS.
        DC Protocol: company_id from cycle.
        
        Returns summary of all posted runs.
        """
        runs = self.db.query(StaffPayrollRun).filter(
            StaffPayrollRun.cycle_id == cycle.id,
            StaffPayrollRun.status == 'APPROVED',
            StaffPayrollRun.sfms_posted == False
        ).all()
        
        if not runs:
            return {
                'success': True,
                'message': 'No pending runs to post',
                'posted_count': 0
            }
        
        results = []
        success_count = 0
        error_count = 0
        total_expense = Decimal('0')
        
        for run in runs:
            try:
                result = self.post_payroll_run_to_sfms(run, posted_by_id)
                if result.get('success'):
                    success_count += 1
                    total_expense += run.ctc_cost or Decimal('0')
                else:
                    error_count += 1
                results.append({
                    'run_id': run.id,
                    'employee_id': run.employee_id,
                    **result
                })
            except Exception as e:
                error_count += 1
                logger.error(f"[DC-PAYROLL-SFMS] Error posting run {run.id}: {str(e)}")
                results.append({
                    'run_id': run.id,
                    'employee_id': run.employee_id,
                    'success': False,
                    'error': str(e)
                })
        
        return {
            'success': error_count == 0,
            'message': f"Posted {success_count} runs to SFMS" + (f", {error_count} errors" if error_count > 0 else ""),
            'posted_count': success_count,
            'error_count': error_count,
            'total_expense': float(total_expense),
            'results': results
        }
