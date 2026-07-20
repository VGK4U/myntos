"""
Staff Financial Management System - Seed Script
DC_SFMS_SEED_001: Idempotent initialization of core SFMS data
DC_SFMS_SEED_002 (May 2026): Tally ERP-9 standard 28 groups + default ledger heads + HSN catalog

This script creates:
1. Mynt Real LLP as the default book keeper company
2. Default company segments for the book keeper
3. Default income source types
4. Default Chart of Accounts (Tally 28 groups + ~28 default ledgers per company)
5. Default HSN/SAC code catalog (~30 common codes — global, run once)

All operations are idempotent - safe to run multiple times.
All operations are additive - never deletes/overwrites existing data.

Created: Dec 06, 2025
Extended: May 02, 2026 — Tally COA + HSN catalog
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from decimal import Decimal
import logging

from app.models.staff_accounts import (
    AssociatedCompany,
    CompanySegment,
    IncomeSourceType,
    PricingConfiguration,
    AccountLedgerMaster,
    HSNMaster
)
from app.models.base import get_indian_time

logger = logging.getLogger(__name__)


def seed_mynt_real_llp(db: Session, created_by_id: Optional[int] = None) -> AssociatedCompany:
    """
    Create or return Mynt Real LLP as the book keeper company.
    DC: Idempotent - checks for existing before creating.
    """
    existing = db.query(AssociatedCompany).filter(
        AssociatedCompany.is_book_keeper == True
    ).first()
    
    if existing:
        logger.info(f"[DC_SFMS_SEED_001] Book keeper already exists: {existing.company_name}")
        return existing
    
    existing_by_code = db.query(AssociatedCompany).filter(
        func.lower(AssociatedCompany.company_code) == 'mynt_real_llp'
    ).first()
    
    if existing_by_code:
        existing_by_code.is_book_keeper = True
        existing_by_code.updated_at = get_indian_time()
        db.commit()
        db.refresh(existing_by_code)
        logger.info(f"[DC_SFMS_SEED_001] Set existing company as book keeper: {existing_by_code.company_name}")
        return existing_by_code
    
    mynt_real = AssociatedCompany(
        company_code="MYNT_REAL_LLP",
        company_name="Mynt Real LLP",
        company_type="PARENT",
        gst_number=None,
        pan_number=None,
        cin_number=None,
        address="Registered Office Address",
        city="Mumbai",
        state="Maharashtra",
        pincode="400001",
        bank_name=None,
        bank_branch=None,
        account_number=None,
        ifsc_code=None,
        account_type="CURRENT",
        receipt_prefix="MR",
        invoice_prefix="MR",
        is_book_keeper=True,
        is_active=True,
        created_by_id=created_by_id
    )
    
    db.add(mynt_real)
    db.commit()
    db.refresh(mynt_real)
    
    logger.info(f"[DC_SFMS_SEED_001] Created book keeper company: {mynt_real.company_name} (ID: {mynt_real.id})")
    return mynt_real


def seed_default_segments(db: Session, company_id: int, created_by_id: Optional[int] = None) -> list:
    """
    Create default segments for a company.
    DC: Idempotent - skips existing segments by code.
    """
    default_segments = [
        {
            "segment_code": "GENERAL",
            "segment_name": "General",
            "description": "General company operations",
            "is_default": True,
            "display_order": 0
        },
        {
            "segment_code": "SALES",
            "segment_name": "Sales",
            "description": "Sales and revenue operations",
            "is_default": False,
            "display_order": 1
        },
        {
            "segment_code": "PURCHASE",
            "segment_name": "Purchase",
            "description": "Purchase and procurement operations",
            "is_default": False,
            "display_order": 2
        },
        {
            "segment_code": "SERVICE",
            "segment_name": "Service",
            "description": "Service delivery operations",
            "is_default": False,
            "display_order": 3
        },
        {
            "segment_code": "MNR_PAYMENTS",
            "segment_name": "MNR Payments",
            "description": "MNR user payment processing",
            "is_default": False,
            "display_order": 4
        }
    ]
    
    created_segments = []
    
    for seg_data in default_segments:
        existing = db.query(CompanySegment).filter(
            CompanySegment.company_id == company_id,
            func.lower(CompanySegment.segment_code) == seg_data["segment_code"].lower()
        ).first()
        
        if existing:
            logger.info(f"[DC_SFMS_SEED_001] Segment already exists: {seg_data['segment_code']}")
            created_segments.append(existing)
            continue
        
        segment = CompanySegment(
            company_id=company_id,
            segment_code=seg_data["segment_code"],
            segment_name=seg_data["segment_name"],
            description=seg_data["description"],
            is_default=seg_data["is_default"],
            display_order=seg_data["display_order"],
            is_active=True,
            created_by_id=created_by_id
        )
        
        db.add(segment)
        created_segments.append(segment)
        logger.info(f"[DC_SFMS_SEED_001] Created segment: {seg_data['segment_code']}")
    
    db.commit()
    return created_segments


def seed_default_income_sources(db: Session, company_id: int, created_by_id: Optional[int] = None) -> list:
    """
    Create default income source types.
    DC: Idempotent - skips existing by source code.
    DC_SFMS_001: is_taxable, default_tax_rate, requires_receipt configurable by VGK/EA/Accounts.
    """
    default_sources = [
        {
            "source_code": "SALES",
            "source_name": "Product Sales",
            "description": "Income from product sales",
            "requires_reference": False,
            "reference_type": None,
            "is_taxable": True,
            "default_tax_rate": 18.00,
            "requires_receipt": True,
            "display_order": 0
        },
        {
            "source_code": "SERVICE",
            "source_name": "Service Income",
            "description": "Income from service delivery",
            "requires_reference": False,
            "reference_type": None,
            "is_taxable": True,
            "default_tax_rate": 18.00,
            "requires_receipt": True,
            "display_order": 1
        },
        {
            "source_code": "MNR_PAYMENTS",
            "source_name": "MNR User Payments",
            "description": "Payments received from MNR users",
            "requires_reference": True,
            "reference_type": "MNR_USER",
            "is_taxable": True,
            "default_tax_rate": 0.00,
            "requires_receipt": True,
            "display_order": 2
        },
        {
            "source_code": "INTEREST",
            "source_name": "Interest Income",
            "description": "Interest earned on deposits and loans",
            "requires_reference": False,
            "reference_type": None,
            "is_taxable": True,
            "default_tax_rate": 0.00,
            "requires_receipt": False,
            "display_order": 3
        },
        {
            "source_code": "OTHER",
            "source_name": "Other Income",
            "description": "Miscellaneous income",
            "requires_reference": False,
            "reference_type": None,
            "is_taxable": True,
            "default_tax_rate": 0.00,
            "requires_receipt": False,
            "display_order": 4
        }
    ]
    
    created_sources = []
    
    for src_data in default_sources:
        existing = db.query(IncomeSourceType).filter(
            func.lower(IncomeSourceType.source_code) == src_data["source_code"].lower()
        ).first()
        
        if existing:
            logger.info(f"[DC_SFMS_SEED_001] Income source already exists: {src_data['source_code']}")
            created_sources.append(existing)
            continue
        
        source = IncomeSourceType(
            source_code=src_data["source_code"],
            source_name=src_data["source_name"],
            description=src_data["description"],
            requires_reference=src_data["requires_reference"],
            reference_type=src_data["reference_type"],
            is_taxable=src_data["is_taxable"],
            default_tax_rate=src_data["default_tax_rate"],
            requires_receipt=src_data["requires_receipt"],
            applicable_companies=["ALL"],
            display_order=src_data["display_order"],
            is_active=True,
            created_by_id=created_by_id
        )
        
        db.add(source)
        created_sources.append(source)
        logger.info(f"[DC_SFMS_SEED_001] Created income source: {src_data['source_code']}")
    
    db.commit()
    return created_sources


def seed_default_pricing_config(db: Session, company_id: int, created_by_id: Optional[int] = None) -> PricingConfiguration:
    """
    Create default pricing configuration for a company.
    DC: Default markup 20%, incentive share 50%.
    Uses model field names: default_markup_pct, incentive_pct, config_type.
    """
    existing = db.query(PricingConfiguration).filter(
        PricingConfiguration.company_id == company_id,
        PricingConfiguration.config_type == 'SERVICE_ITEM_MARKUP'
    ).first()
    
    if existing:
        logger.info(f"[DC_SFMS_SEED_001] Pricing config already exists for company ID: {company_id}")
        return existing
    
    config = PricingConfiguration(
        company_id=company_id,
        config_type="SERVICE_ITEM_MARKUP",
        default_markup_pct=20.00,
        incentive_pct=50.00,
        min_markup_pct=10.00,
        allow_below_cost=False,
        is_active=True,
        configured_by_id=created_by_id
    )
    
    db.add(config)
    db.commit()
    db.refresh(config)
    
    logger.info(f"[DC_SFMS_SEED_001] Created default pricing config: 20% markup, 50% incentive share")
    return config


# ────────────────────────────────────────────────────────────────────────────
# DC_SFMS_SEED_002: Tally ERP-9 Standard Chart of Accounts
# ────────────────────────────────────────────────────────────────────────────
#
# Tally has 15 PRIMARY groups + 13 PRE-DEFINED SUB-GROUPS = 28 total groups.
# Below we list the 28 groups (parent_group field on AccountLedgerMaster carries
# the Tally group name) and ~28 default ledger heads under them.
#
# account_type values constrained by AccountLedgerMaster CHECK:
#   CASH / BANK / UPI / INCOME / EXPENSE / STOCK / PARTY / CAPITAL / LOAN /
#   LIABILITY / ASSET
#
# Idempotent — UNIQUE(company_id, account_type, account_name) prevents duplicates.

DEFAULT_LEDGERS = [
    # ===== CAPITAL ACCOUNT =====
    {"account_name": "Owner's Capital",      "account_type": "CAPITAL",   "parent_group": "Capital Account",                         "code": "1001"},
    {"account_name": "Reserves & Surplus",   "account_type": "CAPITAL",   "parent_group": "Capital Account/Reserves & Surplus",      "code": "1002"},

    # ===== LOANS (LIABILITY) =====
    {"account_name": "Bank Loan A/c",        "account_type": "LOAN",      "parent_group": "Loans (Liability)/Secured Loans",         "code": "1101"},
    {"account_name": "Unsecured Loans",      "account_type": "LOAN",      "parent_group": "Loans (Liability)/Unsecured Loans",       "code": "1102"},
    {"account_name": "Bank OD A/c",          "account_type": "LOAN",      "parent_group": "Loans (Liability)/Bank OD A/c",           "code": "1103"},

    # ===== CURRENT LIABILITIES → DUTIES & TAXES =====
    {"account_name": "CGST Output",          "account_type": "LIABILITY", "parent_group": "Current Liabilities/Duties & Taxes",      "code": "1201"},
    {"account_name": "SGST Output",          "account_type": "LIABILITY", "parent_group": "Current Liabilities/Duties & Taxes",      "code": "1202"},
    {"account_name": "IGST Output",          "account_type": "LIABILITY", "parent_group": "Current Liabilities/Duties & Taxes",      "code": "1203"},
    {"account_name": "TDS Payable",          "account_type": "LIABILITY", "parent_group": "Current Liabilities/Duties & Taxes",      "code": "1204"},
    {"account_name": "Provisions",           "account_type": "LIABILITY", "parent_group": "Current Liabilities/Provisions",          "code": "1205"},
    # Sundry Creditors handled via party_ledger (VENDOR), no master ledger needed

    # ===== CURRENT ASSETS → CASH =====
    {"account_name": "Cash",                 "account_type": "CASH",      "parent_group": "Current Assets/Cash-in-hand",             "code": "2001"},

    # ===== CURRENT ASSETS → BANK =====
    # Per-company bank accounts created from AssociatedCompany.bank_name if present.
    # We seed a generic placeholder so BS Bank section is never empty.
    {"account_name": "Bank Account",         "account_type": "BANK",      "parent_group": "Current Assets/Bank Accounts",            "code": "2101"},

    # ===== CURRENT ASSETS → STOCK =====
    {"account_name": "Stock-in-Hand",        "account_type": "STOCK",     "parent_group": "Current Assets/Stock-in-Hand",            "code": "2201"},

    # ===== CURRENT ASSETS → DUTIES & TAXES (INPUT GST receivable) =====
    {"account_name": "CGST Input",           "account_type": "ASSET",     "parent_group": "Current Assets/Duties & Taxes",           "code": "2301"},
    {"account_name": "SGST Input",           "account_type": "ASSET",     "parent_group": "Current Assets/Duties & Taxes",           "code": "2302"},
    {"account_name": "IGST Input",           "account_type": "ASSET",     "parent_group": "Current Assets/Duties & Taxes",           "code": "2303"},
    {"account_name": "Loans & Advances",     "account_type": "ASSET",     "parent_group": "Current Assets/Loans & Advances (Asset)", "code": "2304"},
    {"account_name": "Deposits",             "account_type": "ASSET",     "parent_group": "Current Assets/Deposits (Asset)",         "code": "2305"},
    # Sundry Debtors handled via party_ledger (CUSTOMER), no master ledger needed

    # ===== FIXED ASSETS =====
    {"account_name": "Fixed Assets",         "account_type": "ASSET",     "parent_group": "Fixed Assets",                            "code": "3001"},

    # ===== INVESTMENTS =====
    {"account_name": "Investments",          "account_type": "ASSET",     "parent_group": "Investments",                             "code": "3101"},

    # ===== MISC. EXPENSES (ASSET) =====
    {"account_name": "Suspense A/c",         "account_type": "ASSET",     "parent_group": "Misc. Expenses (Asset)",                  "code": "3201"},

    # ===== SALES ACCOUNTS (INCOME) =====
    {"account_name": "Sales A/c",            "account_type": "INCOME",    "parent_group": "Sales Accounts",                          "code": "4001"},
    {"account_name": "Service Revenue",      "account_type": "INCOME",    "parent_group": "Sales Accounts",                          "code": "4002"},

    # ===== PURCHASE ACCOUNTS (EXPENSE) =====
    {"account_name": "Purchase A/c",         "account_type": "EXPENSE",   "parent_group": "Purchase Accounts",                       "code": "5001"},

    # ===== DIRECT EXPENSES =====
    {"account_name": "Freight & Cartage",    "account_type": "EXPENSE",   "parent_group": "Direct Expenses",                         "code": "5101"},
    {"account_name": "Courier Charges",      "account_type": "EXPENSE",   "parent_group": "Direct Expenses",                         "code": "5102"},
    {"account_name": "Transport Charges",    "account_type": "EXPENSE",   "parent_group": "Direct Expenses",                         "code": "5103"},
    {"account_name": "Wages",                "account_type": "EXPENSE",   "parent_group": "Direct Expenses",                         "code": "5104"},

    # ===== INDIRECT EXPENSES =====
    {"account_name": "Salaries",             "account_type": "EXPENSE",   "parent_group": "Indirect Expenses",                       "code": "6001"},
    {"account_name": "Rent",                 "account_type": "EXPENSE",   "parent_group": "Indirect Expenses",                       "code": "6002"},
    {"account_name": "Electricity Charges",  "account_type": "EXPENSE",   "parent_group": "Indirect Expenses",                       "code": "6003"},
    {"account_name": "Telephone & Internet", "account_type": "EXPENSE",   "parent_group": "Indirect Expenses",                       "code": "6004"},
    {"account_name": "Office Expenses",      "account_type": "EXPENSE",   "parent_group": "Indirect Expenses",                       "code": "6005"},
    {"account_name": "Bank Charges",         "account_type": "EXPENSE",   "parent_group": "Indirect Expenses",                       "code": "6006"},
    {"account_name": "Printing & Stationery","account_type": "EXPENSE",   "parent_group": "Indirect Expenses",                       "code": "6007"},
    {"account_name": "Professional Fees",    "account_type": "EXPENSE",   "parent_group": "Indirect Expenses",                       "code": "6008"},
    {"account_name": "Travelling Expenses",  "account_type": "EXPENSE",   "parent_group": "Indirect Expenses",                       "code": "6009"},
    {"account_name": "Repairs & Maintenance","account_type": "EXPENSE",   "parent_group": "Indirect Expenses",                       "code": "6010"},

    # ===== INDIRECT INCOMES =====
    {"account_name": "Interest Received",    "account_type": "INCOME",    "parent_group": "Indirect Incomes",                        "code": "7001"},
    {"account_name": "Discount Received",    "account_type": "INCOME",    "parent_group": "Indirect Incomes",                        "code": "7002"},
    {"account_name": "Other Income",         "account_type": "INCOME",    "parent_group": "Indirect Incomes",                        "code": "7003"},
]


def seed_default_chart_of_accounts(db: Session, company_id: int, created_by_id: Optional[int] = None) -> list:
    """
    Seed default Chart of Accounts (Tally 28 groups) for a company.
    DC_SFMS_SEED_002: Idempotent — skips existing ledgers per (company_id, account_type, account_name).
    
    Creates ~28 default ledger heads covering Tally's standard groups.
    Also auto-creates a per-company Bank Account ledger from AssociatedCompany.bank_name if present.
    """
    company = db.query(AssociatedCompany).filter(AssociatedCompany.id == company_id).first()
    if not company:
        logger.warning(f"[DC_SFMS_SEED_002] Company {company_id} not found — skipping COA seed")
        return []

    created = []
    skipped = 0

    for ledger_data in DEFAULT_LEDGERS:
        existing = db.query(AccountLedgerMaster).filter(
            AccountLedgerMaster.company_id == company_id,
            AccountLedgerMaster.account_type == ledger_data["account_type"],
            func.lower(AccountLedgerMaster.account_name) == ledger_data["account_name"].lower()
        ).first()
        
        if existing:
            skipped += 1
            continue
        
        ledger = AccountLedgerMaster(
            company_id=company_id,
            account_type=ledger_data["account_type"],
            account_name=ledger_data["account_name"],
            account_code=ledger_data["code"],
            parent_group=ledger_data["parent_group"],
            description=f"Default Tally ledger: {ledger_data['parent_group']}",
            opening_balance=Decimal('0'),
            opening_balance_type='DEBIT',
            opening_balance_posted=False,
            is_active=True,
            created_by_id=created_by_id
        )
        db.add(ledger)
        created.append(ledger)
    
    # Per-company Bank Account ledger from AssociatedCompany.bank_name (if filled)
    if company.bank_name:
        bank_label = company.bank_name.strip()
        existing_bank = db.query(AccountLedgerMaster).filter(
            AccountLedgerMaster.company_id == company_id,
            AccountLedgerMaster.account_type == 'BANK',
            func.lower(AccountLedgerMaster.account_name) == bank_label.lower()
        ).first()
        if not existing_bank:
            bank_ledger = AccountLedgerMaster(
                company_id=company_id,
                account_type='BANK',
                account_name=bank_label,
                account_code='2102',
                parent_group='Current Assets/Bank Accounts',
                description=f"Bank account for {company.company_name}",
                bank_name=company.bank_name,
                account_number=company.account_number,
                ifsc_code=company.ifsc_code,
                opening_balance=Decimal('0'),
                opening_balance_type='DEBIT',
                opening_balance_posted=False,
                is_active=True,
                created_by_id=created_by_id
            )
            db.add(bank_ledger)
            created.append(bank_ledger)
    
    db.commit()
    logger.info(f"[DC_SFMS_SEED_002] COA for company {company_id} ({company.company_name}): created={len(created)}, skipped={skipped}")
    return created


# ────────────────────────────────────────────────────────────────────────────
# DC_SFMS_SEED_002: Default HSN/SAC catalog (~30 common codes)
# ────────────────────────────────────────────────────────────────────────────
# Goods + Services. Rates per current Indian GST regime.
# CGST + SGST = IGST (intra-state vs inter-state).

DEFAULT_HSN_CODES = [
    # ===== EV / VEHICLE GOODS (28%) =====
    ("8711", "Motorcycles & Mopeds (incl. EV bikes)", 14.00, 14.00, 28.00),
    ("8714", "Motorcycle parts & accessories",        14.00, 14.00, 28.00),
    ("8703", "Motor cars & passenger vehicles",       14.00, 14.00, 28.00),
    ("8704", "Goods transport vehicles (trucks)",     14.00, 14.00, 28.00),
    ("8708", "Motor vehicle parts & accessories",     14.00, 14.00, 28.00),
    ("4011", "Pneumatic tyres - new",                 14.00, 14.00, 28.00),
    ("8512", "Vehicle lighting & signalling equip.",  14.00, 14.00, 28.00),

    # ===== EV / ELECTRICAL (18%) =====
    ("8507", "Electric accumulators (batteries)",      9.00,  9.00, 18.00),
    ("8501", "Electric motors & generators",           9.00,  9.00, 18.00),
    ("8536", "Electrical switches & connectors",       9.00,  9.00, 18.00),
    ("8544", "Insulated wires & cables",               9.00,  9.00, 18.00),
    ("8482", "Ball & roller bearings",                 9.00,  9.00, 18.00),
    ("7318", "Screws, bolts, nuts & fasteners",        9.00,  9.00, 18.00),
    ("8413", "Pumps for liquids",                      9.00,  9.00, 18.00),

    # ===== PACKAGING / GENERAL GOODS =====
    ("4819", "Cartons, boxes & cases of paper (12%)",  6.00,  6.00, 12.00),
    ("3923", "Plastic containers & packaging (18%)",   9.00,  9.00, 18.00),

    # ===== APPAREL (12%) =====
    ("6109", "T-shirts, vests & singlets (12%)",       6.00,  6.00, 12.00),
    ("6203", "Men's apparel (12%)",                    6.00,  6.00, 12.00),

    # ===== ELECTRONICS =====
    ("8517", "Mobile phones & telephone equipment",    9.00,  9.00, 18.00),
    ("8528", "Television sets & monitors (28%)",      14.00, 14.00, 28.00),

    # ===== ESSENTIAL GOODS (5%) =====
    ("1006", "Rice (5%)",                              2.50,  2.50,  5.00),
    ("0902", "Tea (5%)",                               2.50,  2.50,  5.00),

    # ===== SAC / SERVICES (18%) =====
    ("9954", "Construction services",                  9.00,  9.00, 18.00),
    ("9961", "Wholesale trade services",               9.00,  9.00, 18.00),
    ("9965", "Goods transport services",               2.50,  2.50,  5.00),
    ("9966", "Rental services of vehicles",            9.00,  9.00, 18.00),
    ("9971", "Financial services",                     9.00,  9.00, 18.00),
    ("9983", "Other professional & technical services",9.00,  9.00, 18.00),
    ("9984", "Telecommunication services",             9.00,  9.00, 18.00),
    ("9985", "Support services",                       9.00,  9.00, 18.00),
    ("9988", "Job-work / manufacturing services",      9.00,  9.00, 18.00),
    ("9992", "Education services",                     9.00,  9.00, 18.00),
    ("9993", "Healthcare services (exempt)",           0.00,  0.00,  0.00),
    ("9999", "Miscellaneous services",                 9.00,  9.00, 18.00),
]


def seed_default_hsn_codes(db: Session, created_by_id: Optional[int] = None) -> list:
    """
    Seed default HSN/SAC code catalog. Global (not per-company).
    DC_SFMS_SEED_002: Idempotent — skips existing codes by hsn_code (UNIQUE constraint).
    """
    created = []
    skipped = 0
    
    for code, desc, cgst, sgst, igst in DEFAULT_HSN_CODES:
        existing = db.query(HSNMaster).filter(HSNMaster.hsn_code == code).first()
        if existing:
            skipped += 1
            continue
        
        hsn = HSNMaster(
            hsn_code=code,
            description=desc,
            cgst_rate=Decimal(str(cgst)),
            sgst_rate=Decimal(str(sgst)),
            igst_rate=Decimal(str(igst)),
            cess_rate=Decimal('0'),
            is_active=True,
            created_by_id=created_by_id
        )
        db.add(hsn)
        created.append(hsn)
    
    db.commit()
    logger.info(f"[DC_SFMS_SEED_002] HSN catalog: created={len(created)}, skipped={skipped}")
    return created


def seed_company_full_defaults(db: Session, company_id: int, created_by_id: Optional[int] = None) -> dict:
    """
    Seed all default data for a SINGLE company: segments, income sources, COA, pricing.
    DC_SFMS_SEED_002: Wrapper used by both create_company auto-seed and startup backfill.
    Idempotent — safe to re-run.
    """
    result = {"company_id": company_id, "errors": []}
    try:
        segs = seed_default_segments(db, company_id, created_by_id)
        result["segments_count"] = len(segs)
    except Exception as e:
        logger.error(f"[DC_SFMS_SEED_002] segments failed for co={company_id}: {e}")
        result["errors"].append(f"segments: {e}")
        db.rollback()
    
    try:
        srcs = seed_default_income_sources(db, company_id, created_by_id)
        result["income_sources_count"] = len(srcs)
    except Exception as e:
        logger.error(f"[DC_SFMS_SEED_002] income_sources failed for co={company_id}: {e}")
        result["errors"].append(f"income_sources: {e}")
        db.rollback()
    
    try:
        coa = seed_default_chart_of_accounts(db, company_id, created_by_id)
        result["coa_created"] = len(coa)
    except Exception as e:
        logger.error(f"[DC_SFMS_SEED_002] COA failed for co={company_id}: {e}")
        result["errors"].append(f"coa: {e}")
        db.rollback()
    
    try:
        pc = seed_default_pricing_config(db, company_id, created_by_id)
        result["pricing_config_id"] = pc.id if pc else None
    except Exception as e:
        logger.error(f"[DC_SFMS_SEED_002] pricing failed for co={company_id}: {e}")
        result["errors"].append(f"pricing: {e}")
        db.rollback()
    
    return result


def cleanup_jv_receipt_ledger_duplicates(db: Session) -> dict:
    """
    DC-DEDUP-FIX-001: Remove duplicate account_ledger rows created by the now-fixed
    RECEIPT JV double-posting bug.

    Root cause: JournalVoucherService.create() for RECEIPT type first posted
    DR (Bank DEBIT) + CR (Party CREDIT) under reference_type='JOURNAL', then also
    called post_income_confirmed() which posted Bank DEBIT + Income CREDIT + Party CREDIT
    again under reference_type='INCOME' — for the same transaction.

    This function deletes all account_ledger rows where:
      - reference_type = 'INCOME'
      - reference_id points to an income_entry whose reference_type = 'JOURNAL_VOUCHER'
      (i.e. auto-created by a RECEIPT JV — these are the duplicates)

    Then recomputes running_balance for all affected (company_id, account_type, account_name)
    combinations so the General Ledger stays accurate.

    Fully idempotent — safe to run on every startup; if nothing to delete, returns immediately.
    """
    from app.models.staff_accounts import AccountLedger as _AL, IncomeEntry as _IE

    result = {"deleted": 0, "rebalanced": 0, "errors": []}

    try:
        # Find income_entry IDs that were auto-created by RECEIPT JVs
        jv_income_ids = [
            row.id for row in db.query(_IE.id).filter(
                _IE.reference_type == 'JOURNAL_VOUCHER'
            ).all()
        ]
        if not jv_income_ids:
            return result

        # Find the duplicate account_ledger rows
        dup_rows = db.query(_AL).filter(
            _AL.reference_type == 'INCOME',
            _AL.reference_id.in_(jv_income_ids)
        ).all()

        if not dup_rows:
            return result

        # Collect all (company_id, account_type, account_name) that will need rebalancing
        affected = set()
        for row in dup_rows:
            affected.add((row.company_id, row.account_type, row.account_name))

        # Delete the duplicate rows
        for row in dup_rows:
            db.delete(row)
        db.flush()
        result["deleted"] = len(dup_rows)

        # Recompute running_balance for all affected account chains
        for (co_id, acct_type, acct_name) in affected:
            try:
                entries = db.query(_AL).filter(
                    _AL.company_id == co_id,
                    _AL.account_type == acct_type,
                    _AL.account_name == acct_name,
                ).order_by(_AL.transaction_date.asc(), _AL.id.asc()).all()
                from decimal import Decimal as _D
                bal = _D('0')
                for e in entries:
                    bal = bal + _D(str(e.debit_amount or 0)) - _D(str(e.credit_amount or 0))
                    e.running_balance = bal
                result["rebalanced"] += 1
            except Exception as _re:
                result["errors"].append(f"rebalance {acct_name}: {_re}")

        db.commit()

    except Exception as e:
        result["errors"].append(str(e))
        try:
            db.rollback()
        except Exception:
            pass

    return result


def backfill_account_ledger_postings(db: Session) -> dict:
    """
    DC_SALES_LEDGER_001 + DC_PURCHASE_LEDGER_001 (May 2026):
    Retroactively post account_ledger entries for HISTORICAL CONFIRMED records that
    were created before the multi-leg posting code was deployed.
    
    Fully idempotent — uses LedgerPostingService.post_*_confirmed which both check
    for existing entries before inserting.
    
    Wrapped in per-record try/except so a single bad record never blocks the rest.
    """
    from app.models.staff_accounts import (
        SalesInvoice, PurchaseInvoiceUpload, AccountLedger
    )
    from app.services.staff_accounts_service import LedgerPostingService
    
    result = {
        "sales_invoices_scanned": 0,
        "sales_invoices_posted": 0,
        "purchase_uploads_scanned": 0,
        "purchase_uploads_posted": 0,
        "errors": []
    }
    
    # ── Sales Invoices ─────────────────────────────────────────────────────
    try:
        # Only fetch CONFIRMED invoices that have NO account_ledger entry yet
        # (left-join on account_ledger filtered to SALES_INVOICE refs)
        from sqlalchemy import not_, exists, and_
        sub_q = exists().where(and_(
            AccountLedger.reference_type == 'SALES_INVOICE',
            AccountLedger.reference_id == SalesInvoice.id
        ))
        unposted = db.query(SalesInvoice).filter(
            SalesInvoice.status == 'CONFIRMED',
            not_(sub_q)
        ).limit(500).all()  # safety cap per startup run
        
        result["sales_invoices_scanned"] = len(unposted)
        for inv in unposted:
            try:
                _by = getattr(inv, 'confirmed_by_id', None) or getattr(inv, 'created_by_id', None) or 0
                LedgerPostingService.post_sales_invoice_confirmed(
                    db, inv, _by, is_reversal=False
                )
                db.commit()  # commit-per-record so one failure cannot rollback prior successes
                result["sales_invoices_posted"] += 1
            except Exception as _e:
                _err = f"SI #{inv.id} ({inv.invoice_number}): {type(_e).__name__}: {_e}"
                result["errors"].append(_err)
                logger.warning(f"[DC-POST] {_err}")
                try: db.rollback()
                except Exception: pass
        logger.info(f"[DC-POST] Sales invoice backfill: {result['sales_invoices_posted']}/{result['sales_invoices_scanned']} posted")
    except Exception as e:
        logger.error(f"[DC-POST] Sales backfill loop failed: {e}")
        result["errors"].append(f"sales_loop: {e}")
        try: db.rollback()
        except Exception: pass
    
    # ── Purchase Invoice Uploads ───────────────────────────────────────────
    try:
        from sqlalchemy import not_, exists, and_
        # Includes both new (Purchase A/c, CGST/SGST/IGST Input) and legacy
        # (Purchases A/c, *_Tax) names so we don't double-post historical rows.
        sub_q = exists().where(and_(
            AccountLedger.reference_type == 'PURCHASE_UPLOAD',
            AccountLedger.reference_id == PurchaseInvoiceUpload.id,
            AccountLedger.account_name.in_([
                'Purchase A/c', 'CGST Input', 'SGST Input', 'IGST Input',
                'Purchases A/c', 'CGST Input Tax', 'SGST Input Tax', 'IGST Input Tax'
            ])
        ))
        unposted = db.query(PurchaseInvoiceUpload).filter(
            PurchaseInvoiceUpload.status == 'CONFIRMED',
            not_(sub_q)
        ).limit(500).all()
        
        result["purchase_uploads_scanned"] = len(unposted)
        for up in unposted:
            try:
                _by = getattr(up, 'confirmed_by_id', None) or getattr(up, 'created_by_id', None) or 0
                _vt = getattr(up, 'vendor_transaction_id', None)
                LedgerPostingService.post_purchase_upload_confirmed(
                    db, up, _vt, _by, is_reversal=False
                )
                db.commit()  # commit-per-record so one failure cannot rollback prior successes
                result["purchase_uploads_posted"] += 1
            except Exception as _e:
                _err = f"PU #{up.id}: {type(_e).__name__}: {_e}"
                result["errors"].append(_err)
                logger.warning(f"[DC-POST] {_err}")
                try: db.rollback()
                except Exception: pass
        logger.info(f"[DC-POST] Purchase upload backfill: {result['purchase_uploads_posted']}/{result['purchase_uploads_scanned']} posted")
    except Exception as e:
        logger.error(f"[DC-POST] Purchase backfill loop failed: {e}")
        result["errors"].append(f"purchase_loop: {e}")
        try: db.rollback()
        except Exception: pass
    
    return result


def backfill_party_ledger_for_purchases(db: Session) -> dict:
    """
    DC-PL-BACKFILL-001 (Jun 2026):
    Retroactively create party_ledger entries for CONFIRMED purchase uploads
    that pre-date the DC_PURCHASE_LEDGER_001 party-posting code, or whose
    party_ledger entry was silently dropped by a SAVEPOINT rollback.

    Idempotent — checks for existing (reference_type='VENDOR_TXN', reference_id)
    entry before inserting. Safe to run on every startup.
    """
    from app.models.staff_accounts import (
        PurchaseInvoiceUpload, PartyLedger as _PL, VendorMaster as _VM
    )
    from app.services.staff_accounts_service import PartyLedgerService
    from sqlalchemy import not_, exists, and_, case
    from app.models.base import get_indian_time

    result = {"scanned": 0, "posted": 0, "errors": []}

    try:
        confirmed = db.query(PurchaseInvoiceUpload).filter(
            PurchaseInvoiceUpload.status == 'CONFIRMED',
            PurchaseInvoiceUpload.vendor_id.isnot(None),
        ).all()

        result["scanned"] = len(confirmed)

        for up in confirmed:
            try:
                _pl_ref_id = up.vendor_transaction_id if up.vendor_transaction_id else up.id

                exists_q = db.query(_PL.id).filter(
                    _PL.reference_type == 'VENDOR_TXN',
                    _PL.reference_id == _pl_ref_id,
                ).first()
                if exists_q:
                    continue

                vendor = db.query(_VM).filter(_VM.id == up.vendor_id).first()
                vendor_name = vendor.vendor_name if vendor else f"Vendor #{up.vendor_id}"

                txn_num = None
                if up.vendor_transaction_id:
                    from app.models.staff_accounts import VendorTransactionHeader as _VTH
                    _vt = db.query(_VTH).filter(_VTH.id == up.vendor_transaction_id).first()
                    txn_num = _vt.transaction_number if _vt else None

                _pl_ref_num = txn_num or up.upload_number or f"PU-{up.id}"
                _txn_date = up.vendor_invoice_date or (up.confirmed_at.date() if up.confirmed_at else get_indian_time().date())
                _amount = up.grand_total or Decimal('0')
                _by = getattr(up, 'confirmed_by_id', None) or getattr(up, 'created_by_id', None) or 0

                PartyLedgerService.create_entry(
                    db=db,
                    party_type='VENDOR',
                    party_id=up.vendor_id,
                    party_name=vendor_name,
                    company_id=up.company_id,
                    transaction_date=_txn_date,
                    entry_type='CREDIT',
                    reference_type='VENDOR_TXN',
                    reference_id=_pl_ref_id,
                    reference_number=_pl_ref_num,
                    debit_amount=Decimal('0'),
                    credit_amount=_amount,
                    narration=f"Purchase invoice: {up.vendor_invoice_no or up.upload_number}",
                    segment_id=up.segment_id,
                )
                db.flush()
                db.commit()
                result["posted"] += 1
            except Exception as _e:
                _err = f"PU #{up.id}: {type(_e).__name__}: {_e}"
                result["errors"].append(_err)
                logger.warning(f"[DC-PL-BACKFILL-001] {_err}")
                try: db.rollback()
                except Exception: pass
    except Exception as e:
        logger.error(f"[DC-PL-BACKFILL-001] loop failed: {e}")
        result["errors"].append(f"loop: {e}")
        try: db.rollback()
        except Exception: pass

    logger.info(f"[DC-PL-BACKFILL-001] party_ledger purchase backfill: {result['posted']}/{result['scanned']} posted, {len(result['errors'])} errors")
    return result


def run_sfms_seed(db: Session, created_by_id: Optional[int] = None) -> dict:
    """
    Run complete SFMS seed process.
    DC_SFMS_SEED_001 + DC_SFMS_SEED_002:
      1. Ensure book keeper company exists (Mynt Real LLP)
      2. Seed global HSN catalog (once)
      3. For EVERY active company: seed segments, income_sources, COA, pricing_config
    
    All idempotent — safe to run multiple times.
    Used both by /system/seed endpoint and by backend startup.
    
    Returns dict with seeded entities summary.
    """
    logger.info("[DC_SFMS_SEED_001] Starting SFMS seed process...")
    
    summary = {
        "success": True,
        "companies_processed": 0,
        "hsn_created": 0,
        "per_company": [],
        "errors": []
    }
    
    try:
        # 1. Ensure book keeper exists
        mynt_real = seed_mynt_real_llp(db, created_by_id)
        summary["book_keeper"] = {
            "id": mynt_real.id,
            "company_code": mynt_real.company_code,
            "company_name": mynt_real.company_name
        }
    except Exception as e:
        logger.error(f"[DC_SFMS_SEED_001] book keeper seed failed: {e}")
        summary["errors"].append(f"book_keeper: {e}")
        db.rollback()
    
    # 2. HSN catalog (global)
    try:
        hsn_created = seed_default_hsn_codes(db, created_by_id)
        summary["hsn_created"] = len(hsn_created)
    except Exception as e:
        logger.error(f"[DC_SFMS_SEED_002] HSN seed failed: {e}")
        summary["errors"].append(f"hsn: {e}")
        db.rollback()
    
    # 3. Per-company: backfill segments, income sources, COA, pricing for ALL active companies
    try:
        all_companies = db.query(AssociatedCompany).filter(
            AssociatedCompany.is_active == True
        ).all()
        
        for co in all_companies:
            co_result = seed_company_full_defaults(db, co.id, created_by_id)
            co_result["company_name"] = co.company_name
            summary["per_company"].append(co_result)
            summary["companies_processed"] += 1
    except Exception as e:
        logger.error(f"[DC_SFMS_SEED_002] backfill loop failed: {e}")
        summary["errors"].append(f"backfill_loop: {e}")
        db.rollback()
    
    if summary["errors"]:
        summary["success"] = False
    
    logger.info(f"[DC_SFMS_SEED_001] SFMS seed complete — {summary['companies_processed']} companies, {summary['hsn_created']} new HSN codes, {len(summary['errors'])} errors")
    return summary
