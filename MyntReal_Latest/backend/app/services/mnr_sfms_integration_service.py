"""
MNR-SFMS Integration Service
DC Protocol: Integrates MNR payout system with Staff Financial Management System (SFMS)

Created: Dec 30, 2025
Purpose: Create proper accounting entries when MNR withdrawals are processed

CRITICAL: PERSON-WISE ACCOUNTING (Auditor-Traceable)
=========================================================
Every earning, deduction, and payout is recorded against a specific person (member)
with mandatory identifiers: Member ID, Full Name (as per PAN), PAN Number.

Ledger Structure:
- Control Ledgers (Company Level): Business Promotion Expense, Admin Charges Income, TDS Payable (194H)
- Sub-Ledgers (Person-Wise): Incentive Payable – <Member Name (Member ID)>

Journal Entry Flow (India Compliant - Section 194H):
1. When Withdrawal is Approved (Accrual):
   Business Promotion Expense             DR    Gross Amount
     To Admin Charges Income              CR    8%
     To TDS Payable (194H – Member Name)  CR    2%
     To Incentive Payable – Member Name   CR    Net Amount (90%)

2. When Payment is Made:
   Incentive Payable – Member Name        DR    Net Amount
     To Bank                              CR    Net Amount
   (Bank narration: "Incentive payout – Member Name – MNR ID")

3. When TDS is Paid to Government:
   TDS Payable – Member Name – PAN        DR    TDS Amount
     To Bank                              CR    TDS Amount
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal
from datetime import date, datetime
from typing import Optional, Dict, Any
import logging

from app.models.staff_accounts import (
    AssociatedCompany, IncomeSourceType, IncomeEntry,
    ExpenseEntry, PartyLedger
)
from app.models.expense_category import ExpenseMainCategory, ExpenseSubCategory
from app.models.withdrawal import WithdrawalRequest
from app.models.user import User
from app.models.base import get_indian_time

logger = logging.getLogger(__name__)

MNR_COMPANY_CODE = "MNR"
MNR_COMPANY_NAME = "MNR Mega Natural Resources"

INCOME_SOURCE_ADMIN_CHARGES = "ADMIN_SERVICE_FEE"
EXPENSE_CATEGORY_BUSINESS_PROMOTION = "BUSINESS_PROMOTION"
EXPENSE_SUBCATEGORY_SALES_INCENTIVE = "SALES_INCENTIVE"


def get_member_details(db: Session, user_id: str) -> Dict[str, Any]:
    """
    Get member details for person-wise accounting
    Returns: member_id, member_name, pan_number
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {
            "member_id": user_id,
            "member_name": "Unknown Member",
            "pan_number": None
        }
    
    return {
        "member_id": user.id,
        "member_name": user.name or user.account_holder_name or f"Member {user.id}",
        "pan_number": user.pan_number,
        "bank_account": user.bank_account_number,
        "bank_name": user.bank_name,
        "ifsc_code": user.bank_ifsc_code
    }


def ensure_mnr_company_exists(db: Session) -> AssociatedCompany:
    """
    Ensure MNR company exists in SFMS, create if not
    DC Protocol: Company is the default for all MNR transactions
    """
    company = db.query(AssociatedCompany).filter(
        AssociatedCompany.company_code == MNR_COMPANY_CODE
    ).first()
    
    if not company:
        company = AssociatedCompany(
            company_code=MNR_COMPANY_CODE,
            company_name=MNR_COMPANY_NAME,
            company_type='PARENT',
            is_book_keeper=True,
            is_active=True,
            created_at=get_indian_time()
        )
        db.add(company)
        db.commit()
        db.refresh(company)
        logger.info(f"[MNR-SFMS] Created MNR company: {company.id}")
    
    return company


def ensure_income_source_exists(db: Session) -> IncomeSourceType:
    """
    Ensure Admin Service Fee income source exists
    DC Protocol: 8% admin charges recorded as company income
    """
    source = db.query(IncomeSourceType).filter(
        IncomeSourceType.source_code == INCOME_SOURCE_ADMIN_CHARGES
    ).first()
    
    if not source:
        source = IncomeSourceType(
            source_code=INCOME_SOURCE_ADMIN_CHARGES,
            source_name="Admin Service Charges (8%)",
            description="8% admin charges deducted from MNR member incentives - Section 194H compliant",
            default_tax_rate=Decimal('18.00'),
            is_taxable=True,
            requires_receipt=False,
            is_active=True,
            created_at=get_indian_time()
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        logger.info(f"[MNR-SFMS] Created income source: {source.id}")
    
    return source


def get_system_user_id(db: Session) -> Optional[str]:
    """Get a valid user ID to use as system creator for expense categories"""
    first_user = db.query(User.id).first()
    return first_user[0] if first_user else None


def ensure_expense_categories_exist(db: Session) -> tuple:
    """
    Ensure Business Promotion expense category exists
    DC Protocol: Expense is linked to actual sales/performance
    """
    main_category = db.query(ExpenseMainCategory).filter(
        ExpenseMainCategory.name == "Business Promotion"
    ).first()
    
    if not main_category:
        system_user_id = get_system_user_id(db)
        if not system_user_id:
            logger.warning("[MNR-SFMS] No user found to create expense category, skipping")
            return None, None
        
        main_category = ExpenseMainCategory(
            name="Business Promotion",
            description="Business Promotion and Sales Incentive Expenses",
            is_active=True,
            created_by_id=system_user_id,
            created_at=get_indian_time()
        )
        db.add(main_category)
        db.commit()
        db.refresh(main_category)
        logger.info(f"[MNR-SFMS] Created main category: {main_category.id}")
    
    sub_category = db.query(ExpenseSubCategory).filter(
        ExpenseSubCategory.main_category_id == main_category.id,
        ExpenseSubCategory.name == "Sales Incentive Payable"
    ).first()
    
    if not sub_category:
        system_user_id = get_system_user_id(db) or main_category.created_by_id
        sub_category = ExpenseSubCategory(
            main_category_id=main_category.id,
            name="Sales Incentive Payable",
            description="Performance-based sales incentives paid to MNR members",
            is_active=True,
            created_by_id=system_user_id,
            created_at=get_indian_time()
        )
        db.add(sub_category)
        db.commit()
        db.refresh(sub_category)
        logger.info(f"[MNR-SFMS] Created sub category: {sub_category.id}")
    
    return main_category, sub_category


def generate_entry_number(db: Session, prefix: str) -> str:
    """Generate unique entry number with prefix"""
    today = get_indian_time().date()
    date_str = today.strftime("%Y%m%d")
    
    if prefix == "INC":
        count = db.query(func.count(IncomeEntry.id)).filter(
            IncomeEntry.entry_number.like(f"{prefix}-{date_str}%")
        ).scalar() or 0
    else:
        count = db.query(func.count(ExpenseEntry.id)).filter(
            ExpenseEntry.entry_number.like(f"{prefix}-{date_str}%")
        ).scalar() or 0
    
    return f"{prefix}-{date_str}-{count + 1:04d}"


def create_withdrawal_ledger_entries(
    db: Session,
    withdrawal: WithdrawalRequest,
    approved_by_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Create SFMS ledger entries when a withdrawal is approved
    PERSON-WISE ACCOUNTING - Auditor Traceable
    
    Journal Entry (Person-Wise):
    Business Promotion Expense                   DR   Gross Amount
      To Admin Charges Income                    CR   8%
      To TDS Payable (194H – Member Name – PAN)  CR   2%
      To Incentive Payable – Member Name (ID)    CR   Net Amount
    
    Returns dict with created entry IDs
    """
    try:
        company = ensure_mnr_company_exists(db)
        income_source = ensure_income_source_exists(db)
        main_category, sub_category = ensure_expense_categories_exist(db)
        
        member = get_member_details(db, withdrawal.user_id)
        member_id = member["member_id"]
        member_name = member["member_name"]
        pan_number = member["pan_number"]
        
        pan_display = f" – PAN: {pan_number}" if pan_number else ""
        
        net_amount = Decimal(str(withdrawal.final_payout))
        admin_charges = net_amount * Decimal('0.08') / Decimal('0.88')
        tds_amount = net_amount * Decimal('0.02') / Decimal('0.88')
        gross_amount = net_amount + admin_charges + tds_amount
        
        today = get_indian_time().date()
        
        income_entry = IncomeEntry(
            entry_number=generate_entry_number(db, "INC"),
            company_id=company.id,
            income_source_id=income_source.id,
            income_date=today,
            amount=admin_charges,
            reference_type="MNR_USER",
            reference_id=member_id,
            payment_mode="BANK",
            payer_name=member_name,
            narration=f"Admin Service Fee (8%) – {member_name} ({member_id}){pan_display}",
            status="CONFIRMED",
            confirmed_by_id=approved_by_id,
            confirmed_at=get_indian_time(),
            ledger_updated=True,
            created_at=get_indian_time()
        )
        db.add(income_entry)
        
        expense_entry = ExpenseEntry(
            entry_number=generate_entry_number(db, "EXP"),
            company_id=company.id,
            main_category_id=main_category.id,
            sub_category_id=sub_category.id,
            expense_date=today,
            amount=gross_amount,
            payment_mode="BANK",
            narration=f"Business Promotion Expense – {member_name} ({member_id}){pan_display}",
            related_entity_type="MNR_WITHDRAWAL",
            related_entity_id=str(withdrawal.id),
            tds_applicable=True,
            tds_amount=tds_amount,
            net_amount=net_amount,
            status="APPROVED",
            approved_by_id=approved_by_id,
            approved_at=get_indian_time(),
            ledger_updated=True,
            created_at=get_indian_time()
        )
        db.add(expense_entry)
        
        db.flush()
        
        incentive_payable_entry = PartyLedger(
            party_type="MNR_USER",
            party_id=0,
            party_name=f"Incentive Payable – {member_name} ({member_id})",
            company_id=company.id,
            transaction_date=today,
            entry_type="CREDIT",
            reference_type="EXPENSE",
            reference_id=expense_entry.id,
            reference_number=expense_entry.entry_number,
            credit_amount=net_amount,
            debit_amount=Decimal('0'),
            running_balance=net_amount,
            narration=f"Incentive Payable – {member_name} ({member_id}) – Withdrawal #{withdrawal.id}",
            created_at=get_indian_time()
        )
        db.add(incentive_payable_entry)
        
        tds_party_name = f"TDS Payable (194H) – {member_name}"
        if pan_number:
            tds_party_name += f" – PAN: {pan_number}"
        
        tds_payable_entry = PartyLedger(
            party_type="EXTERNAL",
            party_id=0,
            party_name=tds_party_name,
            company_id=company.id,
            transaction_date=today,
            entry_type="CREDIT",
            reference_type="EXPENSE",
            reference_id=expense_entry.id,
            reference_number=expense_entry.entry_number,
            credit_amount=tds_amount,
            debit_amount=Decimal('0'),
            running_balance=tds_amount,
            narration=f"TDS Payable (194H) – {member_name} ({member_id}){pan_display} – Withdrawal #{withdrawal.id}",
            created_at=get_indian_time()
        )
        db.add(tds_payable_entry)
        
        db.commit()
        
        logger.info(f"[MNR-SFMS] Created person-wise ledger entries for {member_name} ({member_id}): "
                   f"Income={income_entry.id}, Expense={expense_entry.id}")
        
        return {
            "success": True,
            "income_entry_id": income_entry.id,
            "expense_entry_id": expense_entry.id,
            "incentive_ledger_id": incentive_payable_entry.id,
            "tds_ledger_id": tds_payable_entry.id,
            "member": {
                "member_id": member_id,
                "member_name": member_name,
                "pan_number": pan_number
            },
            "amounts": {
                "gross": float(gross_amount),
                "admin_charges": float(admin_charges),
                "tds": float(tds_amount),
                "net_payout": float(net_amount)
            }
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"[MNR-SFMS] Failed to create ledger entries for withdrawal #{withdrawal.id}: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def create_payment_ledger_entry(
    db: Session,
    withdrawal: WithdrawalRequest,
    paid_by_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Create SFMS ledger entry when payment is actually made to bank
    PERSON-WISE ACCOUNTING - Auditor Traceable
    
    Journal Entry:
    Incentive Payable – Member Name (ID)    DR   Net Amount
      To Bank                               CR   Net Amount
    
    Bank Narration: "Incentive payout – Member Name – MNR ID"
    """
    try:
        company = ensure_mnr_company_exists(db)
        
        member = get_member_details(db, withdrawal.user_id)
        member_id = member["member_id"]
        member_name = member["member_name"]
        pan_number = member["pan_number"]
        bank_account = member.get("bank_account", "")
        bank_name = member.get("bank_name", "")
        
        bank_account_masked = f"****{bank_account[-4:]}" if bank_account and len(bank_account) >= 4 else "XXXX"
        
        net_amount = Decimal(str(withdrawal.final_payout))
        today = get_indian_time().date()
        
        payment_entry = PartyLedger(
            party_type="MNR_USER",
            party_id=0,
            party_name=f"Incentive Payable – {member_name} ({member_id})",
            company_id=company.id,
            transaction_date=today,
            entry_type="DEBIT",
            reference_type="EXPENSE",
            reference_id=withdrawal.id,
            reference_number=f"WD-{withdrawal.id}",
            debit_amount=net_amount,
            credit_amount=Decimal('0'),
            running_balance=Decimal('0'),
            narration=f"Incentive Payout – {member_name} – {member_id} | {bank_name} A/c {bank_account_masked}",
            created_at=get_indian_time()
        )
        db.add(payment_entry)
        db.commit()
        
        logger.info(f"[MNR-SFMS] Created payment ledger entry for {member_name} ({member_id})")
        
        return {
            "success": True,
            "payment_ledger_id": payment_entry.id,
            "member": {
                "member_id": member_id,
                "member_name": member_name
            },
            "amount_paid": float(net_amount),
            "bank_narration": f"Incentive payout – {member_name} – {member_id}"
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"[MNR-SFMS] Failed to create payment entry for withdrawal #{withdrawal.id}: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def create_tds_payment_entry(
    db: Session,
    member_id: str,
    tds_amount: Decimal,
    payment_reference: str,
    paid_by_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Create SFMS ledger entry when TDS is paid to government
    PERSON-WISE ACCOUNTING - Auditor Traceable (Form 26Q, Form 16A)
    
    Journal Entry:
    TDS Payable (194H) – Member Name – PAN    DR   TDS Amount
      To Bank                                 CR   TDS Amount
    """
    try:
        company = ensure_mnr_company_exists(db)
        
        member = get_member_details(db, member_id)
        member_name = member["member_name"]
        pan_number = member["pan_number"]
        
        pan_display = f" – PAN: {pan_number}" if pan_number else ""
        tds_party_name = f"TDS Payable (194H) – {member_name}{pan_display}"
        
        today = get_indian_time().date()
        
        tds_payment_entry = PartyLedger(
            party_type="EXTERNAL",
            party_id=0,
            party_name=tds_party_name,
            company_id=company.id,
            transaction_date=today,
            entry_type="DEBIT",
            reference_type="EXPENSE",
            reference_id=0,
            reference_number=payment_reference,
            debit_amount=tds_amount,
            credit_amount=Decimal('0'),
            running_balance=Decimal('0'),
            narration=f"TDS Payment (194H) – {member_name} ({member_id}){pan_display} – Ref: {payment_reference}",
            created_at=get_indian_time()
        )
        db.add(tds_payment_entry)
        db.commit()
        
        logger.info(f"[MNR-SFMS] Created TDS payment entry for {member_name} ({member_id})")
        
        return {
            "success": True,
            "tds_payment_ledger_id": tds_payment_entry.id,
            "member": {
                "member_id": member_id,
                "member_name": member_name,
                "pan_number": pan_number
            },
            "tds_paid": float(tds_amount)
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"[MNR-SFMS] Failed to create TDS payment entry for {member_id}: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def initialize_mnr_sfms_data(db: Session) -> Dict[str, Any]:
    """
    Initialize all required SFMS data for MNR integration
    Called on application startup
    """
    try:
        company = ensure_mnr_company_exists(db)
        income_source = ensure_income_source_exists(db)
        main_cat, sub_cat = ensure_expense_categories_exist(db)
        
        return {
            "success": True,
            "company_id": company.id,
            "company_name": company.company_name,
            "income_source_id": income_source.id,
            "main_category_id": main_cat.id,
            "sub_category_id": sub_cat.id
        }
    except Exception as e:
        logger.error(f"[MNR-SFMS] Failed to initialize: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def get_member_incentive_summary(db: Session, member_id: str) -> Dict[str, Any]:
    """
    Get incentive summary for a member (for dashboard display)
    Shows: Gross Incentive, Admin Charges (8%), TDS (2%), Net Payable, Payment Status
    
    This is used in member dashboard for transparency
    """
    try:
        member = get_member_details(db, member_id)
        
        incentive_entries = db.query(PartyLedger).filter(
            PartyLedger.party_type == "MNR_USER",
            PartyLedger.party_name.like(f"Incentive Payable – {member['member_name']}%")
        ).all()
        
        total_credited = sum(Decimal(str(e.credit_amount or 0)) for e in incentive_entries)
        total_debited = sum(Decimal(str(e.debit_amount or 0)) for e in incentive_entries)
        balance_payable = total_credited - total_debited
        
        tds_entries = db.query(PartyLedger).filter(
            PartyLedger.party_type == "EXTERNAL",
            PartyLedger.party_name.like(f"TDS Payable (194H) – {member['member_name']}%")
        ).all()
        
        total_tds_liability = sum(Decimal(str(e.credit_amount or 0)) for e in tds_entries)
        total_tds_paid = sum(Decimal(str(e.debit_amount or 0)) for e in tds_entries)
        tds_balance = total_tds_liability - total_tds_paid
        
        from app.core.constants import NET_PAYOUT_RATE, ADMIN_DEDUCTION_RATE
        gross_incentive = (total_credited / NET_PAYOUT_RATE) if total_credited else Decimal('0')
        admin_charges = (gross_incentive * ADMIN_DEDUCTION_RATE) if total_credited else Decimal('0')
        
        return {
            "success": True,
            "member": {
                "member_id": member["member_id"],
                "member_name": member["member_name"],
                "pan_number": member["pan_number"]
            },
            "summary": {
                "total_gross_incentive": float(round(gross_incentive, 2)),
                "admin_charges_deducted": float(round(admin_charges, 2)),
                "tds_deducted": float(round(total_tds_liability, 2)),
                "net_payable": float(round(total_credited, 2)),
                "total_paid": float(round(total_debited, 2)),
                "balance_payable": float(round(balance_payable, 2)),
                "tds_paid_to_govt": float(round(total_tds_paid, 2)),
                "tds_pending": float(round(tds_balance, 2))
            },
            "payment_status": "Fully Paid" if balance_payable <= 0 else "Pending Payment",
            "form_16a_available": total_tds_paid > 0
        }
        
    except Exception as e:
        logger.error(f"[MNR-SFMS] Failed to get incentive summary for {member_id}: {e}")
        return {
            "success": False,
            "error": str(e)
        }
