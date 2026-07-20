"""
Service Ticket SFMS Integration Service
DC Protocol Jan 2026: Integrates EV Service Ticket billing with SFMS

Purpose: Create proper accounting entries when service tickets are billed/closed

JOURNAL ENTRY FLOW (Service Revenue):
1. When Billing is Confirmed:
   Service Revenue (spares/labour/service)     CR    Total Amount
   Accounts Receivable - Customer              DR    Total Amount
   
2. For GST Invoices:
   Service Revenue                             CR    Taxable Amount
   CGST Output                                 CR    CGST Amount
   SGST Output                                 CR    SGST Amount  
   Accounts Receivable - Customer              DR    Total with GST

Revenue Categories:
- SPARE_PARTS_REVENUE: Revenue from spare parts sold
- SERVICE_LABOUR_REVENUE: Revenue from service/labour charges
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal
from datetime import date, datetime
from typing import Optional, Dict, Any, List
import logging

from app.models.staff_accounts import (
    AssociatedCompany, IncomeSourceType, IncomeEntry, OfficialPartner
)
from app.models.ticket import (
    ServiceTicket, ServiceTicketBilling, ServiceTicketBillingItem,
    ServiceTicketSpareRequest
)
from app.models.base import get_indian_time

logger = logging.getLogger(__name__)

SERVICE_COMPANY_CODE = "EVSC"
SERVICE_COMPANY_NAME = "EV Service Center Operations"

INCOME_SOURCE_SPARES = "EV_SPARE_PARTS_REVENUE"
INCOME_SOURCE_SERVICE = "EV_SERVICE_LABOUR_REVENUE"


def ensure_service_company_exists(db: Session) -> AssociatedCompany:
    """Ensure EV Service company exists in SFMS"""
    company = db.query(AssociatedCompany).filter(
        AssociatedCompany.company_code == SERVICE_COMPANY_CODE
    ).first()
    
    if not company:
        company = AssociatedCompany(
            company_code=SERVICE_COMPANY_CODE,
            company_name=SERVICE_COMPANY_NAME,
            company_type='SUBSIDIARY',
            is_book_keeper=True,
            is_active=True,
            created_at=get_indian_time()
        )
        db.add(company)
        db.commit()
        db.refresh(company)
        logger.info(f"[SVC-SFMS] Created EV Service company: {company.id}")
    
    return company


def ensure_income_sources_exist(db: Session) -> Dict[str, IncomeSourceType]:
    """Ensure service revenue income sources exist"""
    sources = {}
    
    spares_source = db.query(IncomeSourceType).filter(
        IncomeSourceType.source_code == INCOME_SOURCE_SPARES
    ).first()
    
    if not spares_source:
        spares_source = IncomeSourceType(
            source_code=INCOME_SOURCE_SPARES,
            source_name="EV Spare Parts Revenue",
            description="Revenue from EV spare parts sales through service tickets",
            default_tax_rate=Decimal('18.00'),
            is_taxable=True,
            requires_receipt=True,
            is_active=True,
            created_at=get_indian_time()
        )
        db.add(spares_source)
        db.commit()
        db.refresh(spares_source)
        logger.info(f"[SVC-SFMS] Created spares income source: {spares_source.id}")
    
    sources['spares'] = spares_source
    
    service_source = db.query(IncomeSourceType).filter(
        IncomeSourceType.source_code == INCOME_SOURCE_SERVICE
    ).first()
    
    if not service_source:
        service_source = IncomeSourceType(
            source_code=INCOME_SOURCE_SERVICE,
            source_name="EV Service Labour Revenue",
            description="Revenue from EV service and labour charges",
            default_tax_rate=Decimal('18.00'),
            is_taxable=True,
            requires_receipt=True,
            is_active=True,
            created_at=get_indian_time()
        )
        db.add(service_source)
        db.commit()
        db.refresh(service_source)
        logger.info(f"[SVC-SFMS] Created service income source: {service_source.id}")
    
    sources['service'] = service_source
    
    return sources


def generate_income_entry_number(db: Session) -> str:
    """Generate unique income entry number"""
    today = get_indian_time().date()
    date_str = today.strftime("%Y%m%d")
    prefix = "SVC"
    
    count = db.query(func.count(IncomeEntry.id)).filter(
        IncomeEntry.entry_number.like(f"{prefix}-{date_str}%")
    ).scalar() or 0
    
    return f"{prefix}-{date_str}-{count + 1:04d}"


def create_billing_sfms_entries(
    db: Session,
    billing: ServiceTicketBilling,
    confirmed_by_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Create SFMS income entries when billing is confirmed
    
    Creates separate entries for:
    - Spare parts revenue
    - Service/labour revenue
    
    Returns dict with created entry IDs
    """
    try:
        company = ensure_service_company_exists(db)
        income_sources = ensure_income_sources_exist(db)
        
        ticket = billing.ticket
        partner = None
        if billing.service_center_id:
            partner = db.query(OfficialPartner).filter(
                OfficialPartner.id == billing.service_center_id
            ).first()
        
        partner_name = partner.partner_name if partner else "Direct Service"
        customer_name = billing.billing_customer_name or ticket.customer_name or "Walk-in Customer"
        
        today = get_indian_time().date()
        entries_created = []
        
        items = db.query(ServiceTicketBillingItem).filter(
            ServiceTicketBillingItem.billing_id == billing.id
        ).all()
        
        spares_total = Decimal('0')
        service_total = Decimal('0')
        labour_total = Decimal('0')
        
        for item in items:
            item_total = Decimal(str(item.line_total or 0))
            if item.item_type == 'spare':
                spares_total += item_total
            elif item.item_type == 'labour':
                labour_total += item_total
            else:
                service_total += item_total
        
        combined_service_labour = service_total + labour_total

        # DC Protocol: Map billing payment_mode to IncomeEntry allowed values.
        # IncomeEntry constraint: CASH | BANK | UPI | CHEQUE | DD | NEFT | RTGS | CARD
        _VALID_INCOME_MODES = {'CASH', 'BANK', 'UPI', 'CHEQUE', 'DD', 'NEFT', 'RTGS', 'CARD'}
        _raw_mode = (getattr(billing, 'payment_mode', None) or 'cash').upper()
        income_payment_mode = _raw_mode if _raw_mode in _VALID_INCOME_MODES else 'CASH'

        if spares_total > 0:
            spares_entry = IncomeEntry(
                entry_number=generate_income_entry_number(db),
                company_id=billing.company_id or company.id,
                income_source_id=income_sources['spares'].id,
                income_date=today,
                amount=spares_total,
                reference_type="SERVICE_TICKET_BILLING",
                reference_id=str(billing.id),
                payment_mode=income_payment_mode,
                payer_name=customer_name,
                narration=f"Spare Parts Revenue - {ticket.ticket_id} - {partner_name} - Customer: {customer_name}",
                status="CONFIRMED",
                confirmed_by_id=confirmed_by_id,
                confirmed_at=get_indian_time(),
                ledger_updated=True,
                created_at=get_indian_time()
            )
            db.add(spares_entry)
            db.flush()
            entries_created.append({
                "type": "spares",
                "entry_id": spares_entry.id,
                "amount": float(spares_total)
            })
            logger.info(f"[SVC-SFMS] Created spares income entry: {spares_entry.entry_number} = ₹{spares_total}")
        
        if combined_service_labour > 0:
            service_entry = IncomeEntry(
                entry_number=generate_income_entry_number(db),
                company_id=billing.company_id or company.id,
                income_source_id=income_sources['service'].id,
                income_date=today,
                amount=combined_service_labour,
                reference_type="SERVICE_TICKET_BILLING",
                reference_id=str(billing.id),
                payment_mode=income_payment_mode,
                payer_name=customer_name,
                narration=f"Service Labour Revenue - {ticket.ticket_id} - {partner_name} - Customer: {customer_name} (Service: ₹{service_total}, Labour: ₹{labour_total})",
                status="CONFIRMED",
                confirmed_by_id=confirmed_by_id,
                confirmed_at=get_indian_time(),
                ledger_updated=True,
                created_at=get_indian_time()
            )
            db.add(service_entry)
            db.flush()
            entries_created.append({
                "type": "service_labour",
                "entry_id": service_entry.id,
                "amount": float(combined_service_labour),
                "service_component": float(service_total),
                "labour_component": float(labour_total)
            })
            logger.info(f"[SVC-SFMS] Created service/labour income entry: {service_entry.entry_number} = ₹{combined_service_labour}")
        
        billing.sfms_status = 'posted'
        billing.sfms_posted_at = get_indian_time()
        billing.status = 'confirmed'
        
        db.commit()
        
        logger.info(f"[SVC-SFMS] Successfully posted billing {billing.id} to SFMS with {len(entries_created)} entries")
        
        return {
            "success": True,
            "entries": entries_created,
            "total_spares": float(spares_total),
            "total_service": float(combined_service_labour),
            "service_component": float(service_total),
            "labour_component": float(labour_total),
            "grand_total": float(spares_total + combined_service_labour)
        }
        
    except Exception as e:
        db.rollback()
        billing.sfms_status = 'draft'
        billing.sfms_error = str(e)
        db.commit()
        logger.error(f"[SVC-SFMS] Error creating SFMS entries, rolled back: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


def get_service_center_revenue(
    db: Session,
    partner_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None
) -> List[Dict[str, Any]]:
    """
    Get revenue aggregated by service center
    DC Protocol Jan 2026: Separate Estimated Bills from Tax Invoices
    
    Returns list of:
    - partner_id, partner_name, partner_code
    - estimated_bills (count, revenue) - Non-GST documents (document_type='estimate')
    - tax_invoices (count, revenue) - GST documents (document_type='invoice')
    - total_revenue (combined)
    """
    from sqlalchemy import case
    
    query = db.query(
        OfficialPartner.id.label('partner_id'),
        OfficialPartner.partner_code,
        OfficialPartner.partner_name,
        OfficialPartner.category,
        func.count(ServiceTicketBilling.id).label('total_billings'),
        func.coalesce(func.sum(ServiceTicketBilling.spares_amount), 0).label('spares_revenue'),
        func.coalesce(func.sum(ServiceTicketBilling.service_amount), 0).label('service_revenue'),
        func.coalesce(func.sum(ServiceTicketBilling.labour_amount), 0).label('labour_revenue'),
        func.coalesce(func.sum(ServiceTicketBilling.net_payable), 0).label('total_revenue'),
        func.count(case((ServiceTicketBilling.document_type == 'estimate', 1))).label('estimate_count'),
        func.coalesce(func.sum(case((ServiceTicketBilling.document_type == 'estimate', ServiceTicketBilling.net_payable), else_=0)), 0).label('estimate_revenue'),
        func.count(case((ServiceTicketBilling.document_type == 'invoice', 1))).label('invoice_count'),
        func.coalesce(func.sum(case((ServiceTicketBilling.document_type == 'invoice', ServiceTicketBilling.net_payable), else_=0)), 0).label('invoice_revenue'),
        func.coalesce(func.sum(case((ServiceTicketBilling.document_type == 'invoice', ServiceTicketBilling.cgst_amount), else_=0)), 0).label('total_cgst'),
        func.coalesce(func.sum(case((ServiceTicketBilling.document_type == 'invoice', ServiceTicketBilling.sgst_amount), else_=0)), 0).label('total_sgst')
    ).outerjoin(
        ServiceTicketBilling, ServiceTicketBilling.service_center_id == OfficialPartner.id
    ).filter(
        OfficialPartner.category.in_(['SERVICE_CENTER', 'DEALER', 'DISTRIBUTOR'])
    )
    
    if partner_id:
        query = query.filter(OfficialPartner.id == partner_id)
    
    if date_from:
        query = query.filter(ServiceTicketBilling.created_at >= date_from)
    
    if date_to:
        query = query.filter(ServiceTicketBilling.created_at <= date_to)
    
    query = query.group_by(
        OfficialPartner.id,
        OfficialPartner.partner_code,
        OfficialPartner.partner_name,
        OfficialPartner.category
    ).order_by(
        func.sum(ServiceTicketBilling.net_payable).desc().nullslast()
    )
    
    results = query.all()
    
    return [
        {
            "partner_id": r.partner_id,
            "partner_code": r.partner_code,
            "partner_name": r.partner_name,
            "category": r.category,
            "total_billings": r.total_billings,
            "spares_revenue": float(r.spares_revenue or 0),
            "service_revenue": float(r.service_revenue or 0),
            "labour_revenue": float(r.labour_revenue or 0),
            "total_revenue": float(r.total_revenue or 0),
            "estimated_bills": {
                "count": r.estimate_count or 0,
                "revenue": float(r.estimate_revenue or 0)
            },
            "tax_invoices": {
                "count": r.invoice_count or 0,
                "revenue": float(r.invoice_revenue or 0),
                "cgst_collected": float(r.total_cgst or 0),
                "sgst_collected": float(r.total_sgst or 0)
            }
        }
        for r in results
    ]
