"""
Official Partner Order Management System Service Layer - DC_PARTNER_001
Business Logic and Data Access Layer
DC Protocol Compliant - Validation and Audit at every step

Created: Dec 06, 2025
DC Protocol: Write-Verify-Validate at all levels
"""

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Tuple, Dict, Any
from decimal import Decimal
from datetime import datetime, date
from fastapi import HTTPException
import pytz

from app.models.staff import StaffEmployee, StaffRole, log_staff_audit
from app.core.security import SecurityManager
from app.models.staff_accounts import (
    AssociatedCompany, CompanySegment, StockItemMaster, 
    StockLedger, BOMMaster, ManufacturingOrder, FundAllocation,
    VendorTransactionHeader, VendorMaster,
    OfficialPartner, PartnerCompanySegment, PartnerPricingProfile,
    PartnerOrder, PartnerOrderLine, PartnerOrderStatusLog,
    PartnerOrderDispatch, PartnerPaymentRecord, PartnerProcurementLink,
    PartnerInvoice, PricingConfiguration
)
from app.models.real_dreams import RDPartnerProfile
from app.schemas.partner_schemas import (
    OfficialPartnerCreate, OfficialPartnerUpdate,
    PartnerPricingProfileCreate,
    PartnerOrderCreate, PartnerOrderUpdate, PartnerOrderApproval, PartnerOrderRouting,
    OrderLineItemCreate,
    PaymentRecordCreate, DispatchCreate, DispatchUpdate,
    InvoiceGenerateRequest, StockCheckResponse, OrderRoutingDecision,
    RoutedTo, OrderStatus, PaymentMode, DispatchStatus, PaymentStatus
)
from app.services.staff_accounts_service import StockLedgerService


def get_indian_time():
    """Get current time in IST timezone"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist)


PARTNER_ADMIN_ROLES = ['vgk4u', 'ea', 'store_manager', 'sales_head']
PARTNER_APPROVAL_ROLES = ['vgk4u', 'ea', 'store_manager']
PARTNER_DISPATCH_ROLES = ['vgk4u', 'ea', 'store_manager', 'warehouse']
PARTNER_FINANCE_ROLES = ['vgk4u', 'ea', 'accounts', 'finance']


class PartnerAccessError(Exception):
    """Raised when user doesn't have permission for partner operations"""
    pass


class PartnerValidationError(Exception):
    """Raised when validation fails"""
    pass


class PartnerNotFoundError(Exception):
    """Raised when requested resource is not found"""
    pass


class PartnerDuplicateError(Exception):
    """Raised when duplicate entry is detected"""
    pass


def validate_partner_admin_access(employee: StaffEmployee) -> bool:
    """Validate if employee has access to partner admin operations"""
    if not employee or not employee.role:
        raise PartnerAccessError("Employee role not found")
    
    role_code = employee.role.role_code.lower()
    if role_code not in PARTNER_ADMIN_ROLES:
        raise PartnerAccessError(
            f"Access denied. Only authorized roles can manage partners. Your role: {employee.role.role_name}"
        )
    return True


def validate_partner_approval_access(employee: StaffEmployee) -> bool:
    """Validate if employee can approve partner orders"""
    if not employee or not employee.role:
        raise PartnerAccessError("Employee role not found")
    
    role_code = employee.role.role_code.lower()
    if role_code not in PARTNER_APPROVAL_ROLES:
        raise PartnerAccessError(
            f"Access denied. Only Store Manager/VGK/EA can approve orders. Your role: {employee.role.role_name}"
        )
    return True


def log_partner_audit(
    db: Session,
    employee_id: int,
    action: str,
    entity_type: str,
    entity_id: int,
    old_values: Optional[Dict] = None,
    new_values: Optional[Dict] = None,
    description: str = ""
):
    """Log audit trail for partner operations"""
    log_staff_audit(
        db=db,
        employee_id=employee_id,
        action=f"PARTNER_{action}",
        resource_type=entity_type,
        resource_id=entity_id,
        old_data=old_values,
        new_data=new_values
    )


class PartnerNumberingService:
    """
    Company-scoped numbering service for orders, PIs, and invoices
    DC_PARTNER_001: Ensures each company has independent number sequences
    """
    
    @staticmethod
    def get_next_order_number(db: Session, company_id: int) -> str:
        """Generate next order number for a company"""
        company = db.query(AssociatedCompany).filter(
            AssociatedCompany.id == company_id
        ).first()
        
        if not company:
            raise PartnerNotFoundError(f"Company with ID {company_id} not found")
        
        prefix = company.company_code[:3].upper() if company.company_code else "ORD"
        year_suffix = datetime.now().strftime("%y")
        
        last_order = db.query(PartnerOrder).filter(
            PartnerOrder.company_id == company_id,
            PartnerOrder.order_number.like(f"{prefix}-{year_suffix}-%")
        ).order_by(desc(PartnerOrder.id)).first()
        
        if last_order:
            try:
                last_num = int(last_order.order_number.split('-')[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1
        
        return f"{prefix}-{year_suffix}-{next_num:05d}"
    
    @staticmethod
    def get_next_pi_number(db: Session, company_id: int) -> str:
        """Generate next PI number for a company"""
        company = db.query(AssociatedCompany).filter(
            AssociatedCompany.id == company_id
        ).first()
        
        if not company:
            raise PartnerNotFoundError(f"Company with ID {company_id} not found")
        
        prefix = company.company_code[:3].upper() if company.company_code else "PI"
        year_suffix = datetime.now().strftime("%y")
        
        last_pi = db.query(PartnerOrder).filter(
            PartnerOrder.company_id == company_id,
            PartnerOrder.pi_number.isnot(None),
            PartnerOrder.pi_number.like(f"PI-{prefix}-{year_suffix}-%")
        ).order_by(desc(PartnerOrder.id)).first()
        
        if last_pi and last_pi.pi_number:
            try:
                last_num = int(last_pi.pi_number.split('-')[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1
        
        return f"PI-{prefix}-{year_suffix}-{next_num:05d}"
    
    @staticmethod
    def get_next_invoice_number(db: Session, company_id: int) -> str:
        """Generate next invoice number for a company"""
        company = db.query(AssociatedCompany).filter(
            AssociatedCompany.id == company_id
        ).first()
        
        if not company:
            raise PartnerNotFoundError(f"Company with ID {company_id} not found")
        
        prefix = company.company_code[:3].upper() if company.company_code else "INV"
        year_suffix = datetime.now().strftime("%y")
        
        last_invoice = db.query(PartnerInvoice).filter(
            PartnerInvoice.company_id == company_id,
            PartnerInvoice.invoice_number.like(f"INV-{prefix}-{year_suffix}-%")
        ).order_by(desc(PartnerInvoice.id)).first()
        
        if last_invoice:
            try:
                last_num = int(last_invoice.invoice_number.split('-')[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1
        
        return f"INV-{prefix}-{year_suffix}-{next_num:05d}"


class OfficialPartnerService:
    """Service layer for Official Partner management"""

    # [DC-PARTNER-CONTACTS-001] Module key set
    ALL_MODULES = ("walkins", "leads", "service", "marketplace", "stock", "sales")

    @staticmethod
    def _default_module_settings(partner_type: str | None) -> dict:
        """Return default per-module on/off flags based on partner_type.
        iSales/PRODUCT → all 6 modules
        SERVICE        → all except 'leads' and 'service'
        BOTH / None    → all 6 modules
        """
        pt = (partner_type or "BOTH").upper()
        all_on = {m: True for m in OfficialPartnerService.ALL_MODULES}
        if pt == "SERVICE":
            return {**all_on, "leads": False, "service": False}
        return all_on

    @staticmethod
    def create_partner(
        db: Session,
        data: OfficialPartnerCreate,
        employee: StaffEmployee
    ) -> OfficialPartner:
        """Create a new official partner"""
        validate_partner_admin_access(employee)
        
        existing = db.query(OfficialPartner).filter(
            OfficialPartner.partner_code == data.partner_code.upper()
        ).first()
        
        if existing:
            raise PartnerDuplicateError(f"Partner with code '{data.partner_code}' already exists")
        
        partner = OfficialPartner(
            partner_code=data.partner_code.upper(),
            partner_name=data.partner_name,
            category=data.category.value,
            partner_type=data.partner_type.value if data.partner_type else None,
            is_active=True,
            contact_person=data.contact_person,
            email=data.email,
            phone=data.phone,
            whatsapp_number=getattr(data, 'whatsapp_number', None) or getattr(data, 'alternate_phone', None),
            gst_number=data.gstin.upper() if data.gstin else None,
            pan_number=data.pan.upper() if data.pan else None,
            address=data.billing_address,
            city=data.billing_city,
            state=data.billing_state,
            pincode=data.billing_pincode,
            contact_person_1_name=getattr(data, 'contact_person_1_name', None),
            contact_person_1_phone=getattr(data, 'contact_person_1_phone', None),
            contact_person_1_designation=getattr(data, 'contact_person_1_designation', None),
            contact_person_2_name=getattr(data, 'contact_person_2_name', None),
            contact_person_2_phone=getattr(data, 'contact_person_2_phone', None),
            contact_person_2_designation=getattr(data, 'contact_person_2_designation', None),
            map_link_1=getattr(data, 'map_link_1', None),
            map_link_1_label=getattr(data, 'map_link_1_label', None),
            map_link_2=getattr(data, 'map_link_2', None),
            map_link_2_label=getattr(data, 'map_link_2_label', None),
            bank_name=getattr(data, 'bank_name', None),
            bank_branch=getattr(data, 'bank_branch', None),
            account_number=getattr(data, 'account_number', None),
            ifsc_code=getattr(data, 'ifsc_code', None),
            payment_scanner_qr_url=getattr(data, 'payment_scanner_qr_url', None),
            payment_terms=getattr(data, 'payment_terms', 'ADVANCE'),
            credit_limit=Decimal(str(data.credit_limit)) if data.credit_limit else Decimal('0'),
            credit_days=getattr(data, 'credit_days', None) or data.payment_terms_days or 30,
            # DC Protocol Jan 2026: Service Center specific fields
            service_coverage_radius_km=getattr(data, 'service_coverage_radius_km', None),
            certified_technician_count=getattr(data, 'certified_technician_count', None),
            specialized_equipment_list=getattr(data, 'specialized_equipment_list', None),
            service_center_sla_hours=getattr(data, 'service_center_sla_hours', 24),
            # [DC-PARTNER-CONTACTS-001] Sales & service contacts
            sales_contact_number=getattr(data, 'sales_contact_number', None),
            sales_contact_name=getattr(data, 'sales_contact_name', None),
            service_contact_number=getattr(data, 'service_contact_number', None),
            service_contact_name=getattr(data, 'service_contact_name', None),
            # [DC-PARTNER-CONTACTS-001] Module settings — auto-seed from partner_type if not provided
            module_settings=getattr(data, 'module_settings', None) or OfficialPartnerService._default_module_settings(
                data.partner_type.value if data.partner_type else None
            ),
            # [DC-PARTNER-GST-001] Apr 2026: GST treatment type
            gst_type=getattr(data, 'gst_type', 'CGST_SGST') or 'CGST_SGST',
            created_by_id=employee.id
        )
        
        db.add(partner)
        db.flush()
        
        for company_id in data.company_ids:
            company = db.query(AssociatedCompany).filter(
                AssociatedCompany.id == company_id
            ).first()
            if not company:
                raise PartnerValidationError(f"Company with ID {company_id} not found")
            
            segment_id = None
            if data.segment_ids:
                for sid in data.segment_ids:
                    seg = db.query(CompanySegment).filter(
                        CompanySegment.id == sid,
                        CompanySegment.company_id == company_id
                    ).first()
                    if seg:
                        segment_id = sid
                        break
            
            assignment = PartnerCompanySegment(
                partner_id=partner.id,
                company_id=company_id,
                segment_id=segment_id,
                is_active=True,
                created_by_id=employee.id
            )
            db.add(assignment)
        
        if data.category.value == 'REAL_DREAM_PARTNER':
            for company_id in data.company_ids:
                rd_profile = RDPartnerProfile(
                    company_id=company_id,
                    partner_id=partner.id,
                    partner_type='REAL_ESTATE_DEALER',
                    status='DRAFT',
                    created_by_id=employee.id,
                    created_at=get_indian_time()
                )
                db.add(rd_profile)
        
        # DC Protocol (Apr 2026): Set initial password = partner_code (staff can reset later)
        _initial_pwd = partner.partner_code
        partner.password_hash = SecurityManager.get_password_hash(_initial_pwd)
        partner._auto_password = _initial_pwd   # transient attr — used by endpoint to return to caller

        db.commit()
        db.refresh(partner)
        
        log_partner_audit(
            db, employee.id, "CREATE", "OfficialPartner", partner.id,
            new_values=partner.to_dict()
        )
        
        return partner
    
    @staticmethod
    def get_partner(db: Session, partner_id: int) -> Optional[OfficialPartner]:
        """Get a partner by ID with relationships"""
        return db.query(OfficialPartner).options(
            joinedload(OfficialPartner.company_segments)
        ).filter(OfficialPartner.id == partner_id).first()
    
    @staticmethod
    def get_partner_by_code(db: Session, partner_code: str) -> Optional[OfficialPartner]:
        """Get a partner by code"""
        return db.query(OfficialPartner).filter(
            OfficialPartner.partner_code == partner_code.upper()
        ).first()
    
    @staticmethod
    def list_partners(
        db: Session,
        company_id: Optional[int] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[OfficialPartner], int]:
        """
        List partners with filters and company segments
        DC Protocol: Fixed to use subquery for filtering to prevent ID/data mismatch
        when joinedload creates duplicate rows with distinct()
        """
        from sqlalchemy.orm import subqueryload
        
        base_query = db.query(OfficialPartner.id)
        base_query = base_query.filter(OfficialPartner.category != 'VGK_TEAM')
        
        if company_id:
            base_query = base_query.join(PartnerCompanySegment, isouter=False).filter(
                PartnerCompanySegment.company_id == company_id,
                PartnerCompanySegment.is_active == True
            )
        
        if category:
            base_query = base_query.filter(OfficialPartner.category == category)
        
        if status:
            is_active = status.lower() == 'active'
            base_query = base_query.filter(OfficialPartner.is_active == is_active)
        
        if search:
            search_term = f"%{search}%"
            base_query = base_query.filter(
                or_(
                    OfficialPartner.partner_code.ilike(search_term),
                    OfficialPartner.partner_name.ilike(search_term),
                    OfficialPartner.contact_person.ilike(search_term),
                    OfficialPartner.phone.ilike(search_term)
                )
            )
        
        partner_ids = [row[0] for row in base_query.distinct().all()]
        total = len(partner_ids)
        
        if not partner_ids:
            return [], 0
        
        partners = db.query(OfficialPartner).options(
            subqueryload(OfficialPartner.company_segments)
        ).filter(
            OfficialPartner.id.in_(partner_ids)
        ).order_by(OfficialPartner.partner_name).offset(skip).limit(limit).all()
        
        return partners, total
    
    @staticmethod
    def update_partner(
        db: Session,
        partner_id: int,
        data: OfficialPartnerUpdate,
        employee: StaffEmployee
    ) -> OfficialPartner:
        """Update an existing partner"""
        validate_partner_admin_access(employee)
        
        partner = db.query(OfficialPartner).filter(OfficialPartner.id == partner_id).first()
        if not partner:
            raise PartnerNotFoundError(f"Partner with ID {partner_id} not found")
        
        old_values = partner.to_dict()
        
        update_data = data.dict(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(partner, key):
                if key == 'category' and value:
                    value = value.value if hasattr(value, 'value') else value
                if key in ['gst_number', 'pan_number'] and value:
                    value = value.upper()
                setattr(partner, key, value)

        # DC_PARTNER_STATUS_001: Sync is_active from login_status
        # active → is_active=True; inactive/expired/pause/suspended → is_active=False; others keep is_active=True
        _new_is_active = None
        if 'login_status' in update_data and update_data['login_status']:
            ls = update_data['login_status']
            if ls == 'active':
                partner.is_active = True
                _new_is_active = True
            elif ls in ('inactive', 'expired', 'pause', 'suspended'):
                partner.is_active = False
                _new_is_active = False
            else:
                partner.is_active = True
                _new_is_active = True
        
        partner.updated_by_id = employee.id
        partner.updated_at = get_indian_time()
        
        db.commit()
        db.refresh(partner)

        # DC Protocol (Apr 2026): Sync linked VGK member's is_active when partner status changes
        if _new_is_active is not None and partner.phone:
            try:
                _clean_phone = partner.phone.replace(' ', '').replace('-', '')
                _vgk_member = db.query(OfficialPartner).filter(
                    OfficialPartner.phone == _clean_phone,
                    OfficialPartner.category == 'VGK_TEAM'
                ).first()
                if _vgk_member and _vgk_member.is_active != _new_is_active:
                    _vgk_member.is_active = _new_is_active
                    if not _new_is_active:
                        _vgk_member.login_status = 'inactive'
                    else:
                        _vgk_member.login_status = 'active'
                    db.commit()
            except Exception:
                pass
        
        log_partner_audit(
            db, employee.id, "UPDATE", "OfficialPartner", partner.id,
            old_values=old_values,
            new_values=partner.to_dict()
        )
        
        return partner
    
    @staticmethod
    def get_partner_pricing(
        db: Session,
        partner_id: int,
        company_id: int,
        item_id: int
    ) -> Optional[PartnerPricingProfile]:
        """Get active pricing profile for partner/company/item"""
        today = date.today()
        return db.query(PartnerPricingProfile).filter(
            PartnerPricingProfile.partner_id == partner_id,
            PartnerPricingProfile.company_id == company_id,
            PartnerPricingProfile.item_id == item_id,
            PartnerPricingProfile.is_active == True,
            PartnerPricingProfile.effective_from <= today,
            or_(
                PartnerPricingProfile.effective_to.is_(None),
                PartnerPricingProfile.effective_to >= today
            )
        ).first()
    
    @staticmethod
    def create_pricing_profile(
        db: Session,
        data: PartnerPricingProfileCreate,
        employee: StaffEmployee
    ) -> PartnerPricingProfile:
        """Create a pricing profile for a partner"""
        validate_partner_admin_access(employee)
        
        partner = db.query(OfficialPartner).filter(OfficialPartner.id == data.partner_id).first()
        if not partner:
            raise PartnerNotFoundError(f"Partner with ID {data.partner_id} not found")
        
        item = db.query(StockItemMaster).filter(StockItemMaster.id == data.item_id).first()
        if not item:
            raise PartnerNotFoundError(f"Item with ID {data.item_id} not found")
        
        existing = db.query(PartnerPricingProfile).filter(
            PartnerPricingProfile.partner_id == data.partner_id,
            PartnerPricingProfile.company_id == data.company_id,
            PartnerPricingProfile.item_id == data.item_id,
            PartnerPricingProfile.is_active == True,
            PartnerPricingProfile.effective_from <= data.effective_from,
            or_(
                PartnerPricingProfile.effective_to.is_(None),
                PartnerPricingProfile.effective_to >= data.effective_from
            )
        ).first()
        
        if existing:
            existing.effective_to = data.effective_from
            existing.is_active = False
        
        profile = PartnerPricingProfile(
            partner_id=data.partner_id,
            company_id=data.company_id,
            item_id=data.item_id,
            discount_pct=Decimal(str(data.discount_pct)) if data.discount_pct else None,
            special_rate=Decimal(str(data.special_rate)) if data.special_rate else None,
            effective_from=data.effective_from,
            effective_to=data.effective_to,
            is_active=True,
            created_by_id=employee.id
        )
        
        db.add(profile)
        db.commit()
        db.refresh(profile)
        
        log_partner_audit(
            db, employee.id, "CREATE_PRICING", "PartnerPricingProfile", profile.id,
            new_values=profile.to_dict()
        )
        
        return profile


class PartnerOrderService:
    """Service layer for Partner Order management"""
    
    @staticmethod
    def create_order(
        db: Session,
        data: PartnerOrderCreate,
        employee: StaffEmployee
    ) -> PartnerOrder:
        """Create a new partner order"""
        partner = db.query(OfficialPartner).filter(
            OfficialPartner.id == data.partner_id
        ).first()
        if not partner:
            raise PartnerNotFoundError(f"Partner with ID {data.partner_id} not found")
        
        if not partner.is_active:
            raise PartnerValidationError(f"Partner is not active")
        
        company = db.query(AssociatedCompany).filter(
            AssociatedCompany.id == data.company_id
        ).first()
        if not company:
            raise PartnerNotFoundError(f"Company with ID {data.company_id} not found")
        
        assignment = db.query(PartnerCompanySegment).filter(
            PartnerCompanySegment.partner_id == data.partner_id,
            PartnerCompanySegment.company_id == data.company_id,
            PartnerCompanySegment.is_active == True
        ).first()
        if not assignment:
            raise PartnerValidationError(f"Partner is not assigned to company {company.company_name}")
        
        order_number = PartnerNumberingService.get_next_order_number(db, data.company_id)
        
        order = PartnerOrder(
            order_number=order_number,
            partner_id=data.partner_id,
            company_id=data.company_id,
            segment_id=data.segment_id,
            order_date=data.order_date or date.today(),
            commitment_date=data.commitment_date,
            status='DRAFT',
            subtotal=Decimal('0'),
            discount_amount=Decimal('0'),
            tax_amount=Decimal('0'),
            grand_total=Decimal('0'),
            placed_by_id=employee.id if employee else None,
            placed_by_partner=data.placed_by_partner,
            remarks=data.remarks,
            created_by_id=employee.id if employee else None
        )
        
        db.add(order)
        db.flush()
        
        subtotal = Decimal('0')
        total_discount = Decimal('0')
        total_tax = Decimal('0')
        
        for line_data in data.line_items:
            item = db.query(StockItemMaster).filter(
                StockItemMaster.id == line_data.item_id
            ).first()
            if not item:
                raise PartnerNotFoundError(f"Item with ID {line_data.item_id} not found")
            
            if line_data.unit_rate:
                unit_rate = Decimal(str(line_data.unit_rate))
            else:
                pricing = OfficialPartnerService.get_partner_pricing(
                    db, data.partner_id, data.company_id, line_data.item_id
                )
                if pricing and pricing.special_rate:
                    unit_rate = pricing.special_rate
                else:
                    price_config = db.query(PricingConfiguration).filter(
                        PricingConfiguration.item_id == line_data.item_id,
                        PricingConfiguration.company_id == data.company_id,
                        PricingConfiguration.is_active == True
                    ).first()
                    if price_config and price_config.selling_price:
                        unit_rate = price_config.selling_price
                    elif item.base_selling_price:
                        unit_rate = item.base_selling_price
                    else:
                        raise PartnerValidationError(f"No pricing found for item {item.item_name}")
            
            quantity = Decimal(str(line_data.quantity))
            line_subtotal = unit_rate * quantity
            
            discount_pct = Decimal(str(line_data.discount_pct)) if line_data.discount_pct else Decimal('0')
            pricing = OfficialPartnerService.get_partner_pricing(
                db, data.partner_id, data.company_id, line_data.item_id
            )
            if pricing and pricing.discount_pct and not line_data.discount_pct:
                discount_pct = pricing.discount_pct
            
            discount_amount = line_subtotal * (discount_pct / Decimal('100'))
            taxable = line_subtotal - discount_amount
            
            tax_rate = item.gst_rate if item.gst_rate else Decimal('0')
            tax_amount = taxable * (tax_rate / Decimal('100'))
            
            line_total = taxable + tax_amount
            
            stock_available = PartnerOrderService._check_stock_availability(
                db, line_data.item_id, data.company_id, data.segment_id, quantity
            )
            
            order_line = PartnerOrderLine(
                order_id=order.id,
                item_id=line_data.item_id,
                bom_id=line_data.bom_id,
                quantity=quantity,
                unit_of_measure=line_data.unit_of_measure.value if hasattr(line_data.unit_of_measure, 'value') else line_data.unit_of_measure,
                unit_rate=unit_rate,
                discount_pct=discount_pct,
                discount_amount=discount_amount,
                tax_rate=tax_rate,
                tax_amount=tax_amount,
                line_total=line_total,
                stock_available=stock_available,
                requires_manufacturing=not stock_available and line_data.bom_id is not None,
                requires_procurement=not stock_available and line_data.bom_id is None,
                notes=line_data.notes
            )
            
            db.add(order_line)
            
            subtotal += line_subtotal
            total_discount += discount_amount
            total_tax += tax_amount
        
        order.subtotal = subtotal
        order.discount_amount = total_discount
        order.tax_amount = total_tax
        order.grand_total = subtotal - total_discount + total_tax
        
        status_log = PartnerOrderStatusLog(
            order_id=order.id,
            from_status=None,
            to_status='DRAFT',
            changed_by_id=employee.id if employee else None,
            changed_at=get_indian_time(),
            remarks="Order created"
        )
        db.add(status_log)
        
        db.commit()
        db.refresh(order)
        
        if employee:
            log_partner_audit(
                db, employee.id, "CREATE_ORDER", "PartnerOrder", order.id,
                new_values=order.to_dict()
            )
        
        return order
    
    @staticmethod
    def _check_stock_availability(
        db: Session,
        item_id: int,
        company_id: int,
        segment_id: Optional[int],
        quantity: Decimal
    ) -> bool:
        """Check if sufficient stock is available"""
        filters = [
            StockLedger.item_id == item_id,
            StockLedger.company_id == company_id
        ]
        if segment_id:
            filters.append(StockLedger.segment_id == segment_id)
        
        latest_entry = db.query(StockLedger).filter(
            *filters
        ).order_by(desc(StockLedger.id)).first()
        
        if not latest_entry:
            return False
        
        return latest_entry.running_balance >= quantity
    
    @staticmethod
    def get_order(db: Session, order_id: int) -> Optional[PartnerOrder]:
        """Get an order by ID with relationships"""
        return db.query(PartnerOrder).options(
            joinedload(PartnerOrder.line_items),
            joinedload(PartnerOrder.partner),
            joinedload(PartnerOrder.status_logs),
            joinedload(PartnerOrder.payment_records),
            joinedload(PartnerOrder.dispatch_info)
        ).filter(PartnerOrder.id == order_id).first()
    
    @staticmethod
    def get_order_by_number(db: Session, order_number: str, company_id: int) -> Optional[PartnerOrder]:
        """Get an order by order number and company"""
        return db.query(PartnerOrder).filter(
            PartnerOrder.order_number == order_number,
            PartnerOrder.company_id == company_id
        ).first()
    
    @staticmethod
    def list_orders(
        db: Session,
        company_id: Optional[int] = None,
        partner_id: Optional[int] = None,
        status: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[PartnerOrder], int]:
        """List orders with filters"""
        query = db.query(PartnerOrder).options(
            joinedload(PartnerOrder.partner),
            joinedload(PartnerOrder.line_items)
        )
        
        if company_id:
            query = query.filter(PartnerOrder.company_id == company_id)
        
        if partner_id:
            query = query.filter(PartnerOrder.partner_id == partner_id)
        
        if status:
            query = query.filter(PartnerOrder.status == status)
        
        if from_date:
            query = query.filter(PartnerOrder.order_date >= from_date)
        
        if to_date:
            query = query.filter(PartnerOrder.order_date <= to_date)
        
        if search:
            search_term = f"%{search}%"
            query = query.join(OfficialPartner).filter(
                or_(
                    PartnerOrder.order_number.ilike(search_term),
                    PartnerOrder.pi_number.ilike(search_term),
                    OfficialPartner.partner_name.ilike(search_term),
                    OfficialPartner.partner_code.ilike(search_term)
                )
            )
        
        total = query.count()
        orders = query.order_by(desc(PartnerOrder.created_at)).offset(skip).limit(limit).all()
        
        return orders, total
    
    @staticmethod
    def generate_pi(
        db: Session,
        order_id: int,
        employee: StaffEmployee
    ) -> PartnerOrder:
        """Generate Proforma Invoice for an order"""
        order = db.query(PartnerOrder).filter(PartnerOrder.id == order_id).first()
        if not order:
            raise PartnerNotFoundError(f"Order with ID {order_id} not found")
        
        if order.status != 'DRAFT':
            raise PartnerValidationError(f"Cannot generate PI. Order status: {order.status}")
        
        if order.pi_number:
            raise PartnerValidationError(f"PI already generated: {order.pi_number}")
        
        pi_number = PartnerNumberingService.get_next_pi_number(db, order.company_id)
        
        old_values = order.to_dict()
        
        order.pi_number = pi_number
        order.pi_generated_at = get_indian_time()
        order.pi_generated_by_id = employee.id
        order.status = 'PI_GENERATED'
        
        status_log = PartnerOrderStatusLog(
            order_id=order.id,
            from_status='DRAFT',
            to_status='PI_GENERATED',
            changed_by_id=employee.id,
            changed_at=get_indian_time(),
            remarks=f"PI Generated: {pi_number}"
        )
        db.add(status_log)
        
        db.commit()
        db.refresh(order)
        
        log_partner_audit(
            db, employee.id, "GENERATE_PI", "PartnerOrder", order.id,
            old_values=old_values,
            new_values=order.to_dict()
        )
        
        return order
    
    @staticmethod
    def submit_for_approval(
        db: Session,
        order_id: int,
        employee: StaffEmployee
    ) -> PartnerOrder:
        """Submit order for Store Manager approval"""
        order = db.query(PartnerOrder).filter(PartnerOrder.id == order_id).first()
        if not order:
            raise PartnerNotFoundError(f"Order with ID {order_id} not found")
        
        valid_statuses = ['PI_GENERATED', 'PAYMENT_CONFIRMED']
        if order.status not in valid_statuses:
            raise PartnerValidationError(f"Cannot submit for approval. Status: {order.status}")
        
        old_status = order.status
        order.status = 'PENDING_APPROVAL'
        
        status_log = PartnerOrderStatusLog(
            order_id=order.id,
            from_status=old_status,
            to_status='PENDING_APPROVAL',
            changed_by_id=employee.id,
            changed_at=get_indian_time(),
            remarks="Submitted for approval"
        )
        db.add(status_log)
        
        db.commit()
        db.refresh(order)
        
        return order
    
    @staticmethod
    def approve_order(
        db: Session,
        order_id: int,
        approval_data: PartnerOrderApproval,
        employee: StaffEmployee
    ) -> PartnerOrder:
        """Approve or reject an order (Store Manager action)"""
        validate_partner_approval_access(employee)
        
        order = db.query(PartnerOrder).filter(PartnerOrder.id == order_id).first()
        if not order:
            raise PartnerNotFoundError(f"Order with ID {order_id} not found")
        
        if order.status != 'PENDING_APPROVAL':
            raise PartnerValidationError(f"Order is not pending approval. Status: {order.status}")
        
        old_status = order.status
        
        if approval_data.approved:
            order.status = 'APPROVED'
            order.approved_by_id = employee.id
            order.approved_at = get_indian_time()
            order.approval_remarks = approval_data.remarks
        else:
            order.status = 'REJECTED'
            order.approval_remarks = approval_data.remarks
        
        status_log = PartnerOrderStatusLog(
            order_id=order.id,
            from_status=old_status,
            to_status=order.status,
            changed_by_id=employee.id,
            changed_at=get_indian_time(),
            remarks=approval_data.remarks or ("Approved" if approval_data.approved else "Rejected")
        )
        db.add(status_log)
        
        db.commit()
        db.refresh(order)
        
        log_partner_audit(
            db, employee.id, "APPROVE_ORDER" if approval_data.approved else "REJECT_ORDER",
            "PartnerOrder", order.id,
            new_values={"status": order.status, "remarks": approval_data.remarks}
        )
        
        return order
    
    @staticmethod
    def record_payment(
        db: Session,
        order_id: int,
        payment_data: PaymentRecordCreate,
        employee: StaffEmployee
    ) -> PartnerPaymentRecord:
        """Record payment against an order"""
        order = db.query(PartnerOrder).filter(PartnerOrder.id == order_id).first()
        if not order:
            raise PartnerNotFoundError(f"Order with ID {order_id} not found")
        
        valid_statuses = ['PI_GENERATED', 'PAYMENT_PENDING', 'APPROVED']
        if order.status not in valid_statuses:
            raise PartnerValidationError(f"Cannot record payment. Status: {order.status}")
        
        payment = PartnerPaymentRecord(
            order_id=order_id,
            amount=Decimal(str(payment_data.amount)),
            payment_mode=payment_data.payment_mode.value if hasattr(payment_data.payment_mode, 'value') else payment_data.payment_mode,
            payment_date=payment_data.payment_date,
            reference_number=payment_data.reference_number,
            bank_name=payment_data.bank_name,
            verified=False,
            recorded_by_id=employee.id,
            remarks=payment_data.remarks
        )
        
        db.add(payment)
        
        if order.status == 'PI_GENERATED':
            order.status = 'PAYMENT_PENDING'
            
            status_log = PartnerOrderStatusLog(
                order_id=order.id,
                from_status='PI_GENERATED',
                to_status='PAYMENT_PENDING',
                changed_by_id=employee.id,
                changed_at=get_indian_time(),
                remarks=f"Payment of {payment_data.amount} recorded"
            )
            db.add(status_log)
        
        db.commit()
        db.refresh(payment)
        
        log_partner_audit(
            db, employee.id, "RECORD_PAYMENT", "PartnerPaymentRecord", payment.id,
            new_values=payment.to_dict()
        )
        
        return payment
    
    @staticmethod
    def verify_payment(
        db: Session,
        payment_id: int,
        employee: StaffEmployee
    ) -> PartnerPaymentRecord:
        """Verify a payment record (Finance action)"""
        payment = db.query(PartnerPaymentRecord).filter(
            PartnerPaymentRecord.id == payment_id
        ).first()
        if not payment:
            raise PartnerNotFoundError(f"Payment with ID {payment_id} not found")
        
        if payment.verified:
            raise PartnerValidationError("Payment is already verified")
        
        payment.verified = True
        payment.verified_at = get_indian_time()
        payment.verified_by_id = employee.id
        
        order = db.query(PartnerOrder).filter(PartnerOrder.id == payment.order_id).first()
        
        total_verified = db.query(func.sum(PartnerPaymentRecord.amount)).filter(
            PartnerPaymentRecord.order_id == payment.order_id,
            PartnerPaymentRecord.verified == True
        ).scalar() or Decimal('0')
        
        total_verified += payment.amount
        
        if total_verified >= order.grand_total:
            old_status = order.status
            order.status = 'PAYMENT_CONFIRMED'
            order.payment_confirmed_at = get_indian_time()
            order.payment_confirmed_by_id = employee.id
            
            status_log = PartnerOrderStatusLog(
                order_id=order.id,
                from_status=old_status,
                to_status='PAYMENT_CONFIRMED',
                changed_by_id=employee.id,
                changed_at=get_indian_time(),
                remarks=f"Payment verified. Total: {total_verified}"
            )
            db.add(status_log)
        
        db.commit()
        db.refresh(payment)
        
        log_partner_audit(
            db, employee.id, "VERIFY_PAYMENT", "PartnerPaymentRecord", payment.id,
            new_values={"verified": True, "verified_at": payment.verified_at.isoformat()}
        )
        
        return payment
    
    @staticmethod
    def route_order(
        db: Session,
        order_id: int,
        routing_data: PartnerOrderRouting,
        employee: StaffEmployee
    ) -> PartnerOrder:
        """Route order to Production, Procurement, or Direct Dispatch"""
        validate_partner_approval_access(employee)
        
        order = db.query(PartnerOrder).options(
            joinedload(PartnerOrder.line_items)
        ).filter(PartnerOrder.id == order_id).first()
        
        if not order:
            raise PartnerNotFoundError(f"Order with ID {order_id} not found")
        
        valid_statuses = ['APPROVED', 'PAYMENT_CONFIRMED']
        if order.status not in valid_statuses:
            raise PartnerValidationError(f"Cannot route order. Status: {order.status}")
        
        old_status = order.status
        route_to = routing_data.route_to.value if hasattr(routing_data.route_to, 'value') else routing_data.route_to
        
        order.routed_to = route_to
        order.routed_at = get_indian_time()
        order.routed_by_id = employee.id
        
        if route_to == 'PRODUCTION':
            order.status = 'ROUTED_TO_PRODUCTION'
            if routing_data.manufacturing_order_id:
                order.manufacturing_order_id = routing_data.manufacturing_order_id
        elif route_to == 'PROCUREMENT':
            order.status = 'ROUTED_TO_PROCUREMENT'
        else:
            order.status = 'READY_TO_DISPATCH'
        
        status_log = PartnerOrderStatusLog(
            order_id=order.id,
            from_status=old_status,
            to_status=order.status,
            changed_by_id=employee.id,
            changed_at=get_indian_time(),
            remarks=routing_data.remarks or f"Routed to {route_to}"
        )
        db.add(status_log)
        
        db.commit()
        db.refresh(order)
        
        log_partner_audit(
            db, employee.id, "ROUTE_ORDER", "PartnerOrder", order.id,
            new_values={"routed_to": route_to, "status": order.status}
        )
        
        return order
    
    @staticmethod
    def update_status(
        db: Session,
        order_id: int,
        new_status: str,
        employee: StaffEmployee,
        remarks: Optional[str] = None
    ) -> PartnerOrder:
        """Update order status with validation"""
        order = db.query(PartnerOrder).filter(PartnerOrder.id == order_id).first()
        if not order:
            raise PartnerNotFoundError(f"Order with ID {order_id} not found")
        
        old_status = order.status
        order.status = new_status
        order.updated_by_id = employee.id
        order.updated_at = get_indian_time()
        
        status_log = PartnerOrderStatusLog(
            order_id=order.id,
            from_status=old_status,
            to_status=new_status,
            changed_by_id=employee.id,
            changed_at=get_indian_time(),
            remarks=remarks
        )
        db.add(status_log)
        
        db.commit()
        db.refresh(order)
        
        return order
    
    @staticmethod
    def get_order_fulfillability(
        db: Session,
        order_id: int,
        employee: StaffEmployee
    ) -> Dict[str, Any]:
        """
        DC_ORDER_FULFILLMENT_001: Check stock availability and provide routing recommendation
        Returns per-line-item stock status and suggested routing action
        """
        validate_partner_admin_access(employee)
        
        order = db.query(PartnerOrder).options(
            joinedload(PartnerOrder.line_items)
        ).filter(PartnerOrder.id == order_id).first()
        
        if not order:
            raise PartnerNotFoundError(f"Order with ID {order_id} not found")
        
        line_fulfillment = []
        all_in_stock = True
        any_manufacturable = False
        any_procurement_needed = False
        
        for line in order.line_items:
            item = db.query(StockItemMaster).filter(
                StockItemMaster.id == line.item_id
            ).first()
            
            latest_stock = db.query(StockLedger).filter(
                StockLedger.company_id == order.company_id,
                StockLedger.item_id == line.item_id
            ).order_by(desc(StockLedger.id)).first()
            
            available_qty = Decimal(str(latest_stock.balance_qty)) if latest_stock else Decimal('0')
            required_qty = line.quantity
            shortage = max(Decimal('0'), required_qty - available_qty)
            is_sufficient = shortage == 0
            
            bom = db.query(BOMMaster).filter(
                BOMMaster.finished_product_id == line.item_id,
                BOMMaster.status == 'APPROVED',
                BOMMaster.is_active == True
            ).first()
            
            can_manufacture = False
            raw_materials_status = []
            
            if bom and shortage > 0:
                can_manufacture = True
                for bom_line in bom.line_items:
                    wastage_factor = Decimal('1') + (Decimal(str(bom_line.wastage_pct or 0)) / Decimal('100'))
                    raw_required = bom_line.quantity_required * shortage * wastage_factor / (bom.standard_qty or 1)
                    
                    raw_stock = db.query(StockLedger).filter(
                        StockLedger.company_id == order.company_id,
                        StockLedger.item_id == bom_line.component_id
                    ).order_by(desc(StockLedger.id)).first()
                    
                    raw_available = Decimal(str(raw_stock.balance_qty)) if raw_stock else Decimal('0')
                    raw_shortage = max(Decimal('0'), raw_required - raw_available)
                    
                    component = db.query(StockItemMaster).filter(
                        StockItemMaster.id == bom_line.component_id
                    ).first()
                    
                    raw_materials_status.append({
                        'component_id': bom_line.component_id,
                        'component_name': component.item_name if component else 'Unknown',
                        'required_qty': float(raw_required),
                        'available_qty': float(raw_available),
                        'shortage_qty': float(raw_shortage),
                        'is_sufficient': raw_shortage == 0
                    })
                    
                    if raw_shortage > 0 and not bom_line.is_optional:
                        can_manufacture = False
            
            routing = 'DIRECT_DISPATCH'
            if not is_sufficient:
                all_in_stock = False
                if bom and can_manufacture:
                    routing = 'PRODUCTION'
                    any_manufacturable = True
                else:
                    routing = 'PROCUREMENT'
                    any_procurement_needed = True
            
            line_fulfillment.append({
                'line_id': line.id,
                'item_id': line.item_id,
                'item_name': item.item_name if item else 'Unknown',
                'item_code': item.item_code if item else 'Unknown',
                'required_qty': float(required_qty),
                'available_qty': float(available_qty),
                'shortage_qty': float(shortage),
                'is_sufficient': is_sufficient,
                'has_bom': bom is not None,
                'bom_id': bom.id if bom else None,
                'can_manufacture': can_manufacture,
                'raw_materials_status': raw_materials_status,
                'recommended_routing': routing
            })
        
        overall_recommendation = 'DIRECT_DISPATCH'
        if any_procurement_needed:
            overall_recommendation = 'PROCUREMENT' if not any_manufacturable else 'SPLIT'
        elif any_manufacturable:
            overall_recommendation = 'PRODUCTION'
        
        return {
            'order_id': order.id,
            'order_number': order.order_number,
            'company_id': order.company_id,
            'all_in_stock': all_in_stock,
            'overall_recommendation': overall_recommendation,
            'line_items': line_fulfillment
        }
    
    @staticmethod
    def create_manufacturing_from_order(
        db: Session,
        order_id: int,
        line_item_ids: List[int],
        employee: StaffEmployee,
        priority: str = 'NORMAL',
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        DC_ORDER_MANUFACTURING_001: Create Manufacturing Order(s) from Partner Order
        Creates linked manufacturing orders for items that need production
        """
        from app.services.staff_accounts_service import ManufacturingService
        
        validate_partner_admin_access(employee)
        
        order = db.query(PartnerOrder).options(
            joinedload(PartnerOrder.line_items)
        ).filter(PartnerOrder.id == order_id).first()
        
        if not order:
            raise PartnerNotFoundError(f"Order with ID {order_id} not found")
        
        if order.status not in ['APPROVED', 'PAYMENT_CONFIRMED', 'ROUTED_TO_PRODUCTION']:
            raise PartnerValidationError(
                f"Cannot create manufacturing for order in {order.status} status"
            )
        
        manufacturing_orders = []
        errors = []
        
        for line in order.line_items:
            if line.id not in line_item_ids:
                continue
            
            bom = db.query(BOMMaster).filter(
                BOMMaster.finished_product_id == line.item_id,
                BOMMaster.status == 'APPROVED',
                BOMMaster.is_active == True
            ).first()
            
            if not bom:
                errors.append({
                    'line_id': line.id,
                    'item_id': line.item_id,
                    'error': 'No approved BOM found for this item'
                })
                continue
            
            latest_stock = db.query(StockLedger).filter(
                StockLedger.company_id == order.company_id,
                StockLedger.item_id == line.item_id
            ).order_by(desc(StockLedger.id)).first()
            
            available_qty = Decimal(str(latest_stock.balance_qty)) if latest_stock else Decimal('0')
            shortage = max(Decimal('0'), line.quantity - available_qty)
            
            if shortage <= 0:
                errors.append({
                    'line_id': line.id,
                    'item_id': line.item_id,
                    'error': 'Sufficient stock available, manufacturing not required'
                })
                continue
            
            try:
                mfg_order = ManufacturingService.create_order(
                    db=db,
                    company_id=order.company_id,
                    bom_id=bom.id,
                    planned_qty=shortage,
                    employee=employee,
                    priority=priority,
                    notes=notes or f"Manufacturing for Partner Order {order.order_number}"
                )
                
                manufacturing_orders.append({
                    'manufacturing_order_id': mfg_order.id,
                    'order_number': mfg_order.order_number,
                    'line_id': line.id,
                    'item_id': line.item_id,
                    'planned_qty': float(shortage),
                    'bom_id': bom.id
                })
                
                if len(manufacturing_orders) == 1:
                    order.manufacturing_order_id = mfg_order.id
                
            except Exception as e:
                errors.append({
                    'line_id': line.id,
                    'item_id': line.item_id,
                    'error': str(e)
                })
        
        if manufacturing_orders:
            old_status = order.status
            order.status = 'IN_MANUFACTURING'
            order.routed_to = 'PRODUCTION'
            order.routed_at = get_indian_time()
            order.routed_by_id = employee.id
            order.updated_by_id = employee.id
            
            status_log = PartnerOrderStatusLog(
                order_id=order.id,
                from_status=old_status,
                to_status='IN_MANUFACTURING',
                changed_by_id=employee.id,
                changed_at=get_indian_time(),
                remarks=f"Manufacturing created for {len(manufacturing_orders)} item(s)"
            )
            db.add(status_log)
            
            db.commit()
            db.refresh(order)
            
            log_partner_audit(
                db, employee.id, "CREATE_MFG_FROM_ORDER", "PartnerOrder", order.id,
                new_values={
                    "manufacturing_orders": len(manufacturing_orders),
                    "status": "IN_MANUFACTURING"
                }
            )
        
        return {
            'order_id': order.id,
            'order_number': order.order_number,
            'manufacturing_orders_created': manufacturing_orders,
            'errors': errors,
            'order_status': order.status
        }
    
    @staticmethod
    def get_pending_fulfillment_orders(
        db: Session,
        company_id: Optional[int],
        employee: StaffEmployee,
        fulfillment_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Dict], int]:
        """
        DC_ORDER_FULFILLMENT_002: Get orders pending manufacturing or procurement
        Returns orders that are waiting for stock to become available
        """
        validate_partner_admin_access(employee)
        
        pending_statuses = ['IN_MANUFACTURING', 'ROUTED_TO_PRODUCTION', 'PROCUREMENT_IN_PROGRESS', 'ROUTED_TO_PROCUREMENT']
        
        query = db.query(PartnerOrder).options(
            joinedload(PartnerOrder.line_items),
            joinedload(PartnerOrder.partner)
        ).filter(PartnerOrder.status.in_(pending_statuses))
        
        if company_id:
            query = query.filter(PartnerOrder.company_id == company_id)
        
        if fulfillment_type == 'MANUFACTURING':
            query = query.filter(PartnerOrder.status.in_(['IN_MANUFACTURING', 'ROUTED_TO_PRODUCTION']))
        elif fulfillment_type == 'PROCUREMENT':
            query = query.filter(PartnerOrder.status.in_(['PROCUREMENT_IN_PROGRESS', 'ROUTED_TO_PROCUREMENT']))
        
        total = query.count()
        
        orders = query.order_by(desc(PartnerOrder.order_date)).offset(skip).limit(limit).all()
        
        result = []
        for order in orders:
            mfg_order = None
            if order.manufacturing_order_id:
                mfg_order = db.query(ManufacturingOrder).filter(
                    ManufacturingOrder.id == order.manufacturing_order_id
                ).first()
            
            result.append({
                'order': order.to_dict(),
                'partner_name': order.partner.partner_name if order.partner else 'Unknown',
                'line_items_count': len(order.line_items),
                'manufacturing_order': {
                    'id': mfg_order.id,
                    'order_number': mfg_order.order_number,
                    'status': mfg_order.status,
                    'planned_qty': float(mfg_order.planned_qty),
                    'actual_qty': float(mfg_order.actual_qty) if mfg_order.actual_qty else None
                } if mfg_order else None
            })
        
        return result, total


class PartnerDispatchService:
    """Service layer for Partner Order Dispatch management"""
    
    @staticmethod
    def create_dispatch(
        db: Session,
        order_id: int,
        data: DispatchCreate,
        employee: StaffEmployee
    ) -> PartnerOrderDispatch:
        """Create dispatch record for an order"""
        order = db.query(PartnerOrder).filter(PartnerOrder.id == order_id).first()
        if not order:
            raise PartnerNotFoundError(f"Order with ID {order_id} not found")
        
        if order.status != 'READY_TO_DISPATCH':
            raise PartnerValidationError(f"Order is not ready for dispatch. Status: {order.status}")
        
        existing = db.query(PartnerOrderDispatch).filter(
            PartnerOrderDispatch.order_id == order_id
        ).first()
        if existing:
            raise PartnerDuplicateError(f"Dispatch already exists for order {order.order_number}")
        
        dispatch = PartnerOrderDispatch(
            order_id=order_id,
            status='PENDING',
            dispatch_date=data.dispatch_date,
            expected_delivery_date=data.expected_delivery_date,
            courier_name=data.courier_name,
            awb_number=data.awb_number,
            tracking_url=data.tracking_url,
            dispatch_from_segment_id=data.dispatch_from_segment_id,
            package_count=data.package_count or 1,
            package_weight=Decimal(str(data.package_weight)) if data.package_weight else None,
            dispatched_by_id=employee.id,
            remarks=data.remarks
        )
        
        db.add(dispatch)
        
        order.status = 'DISPATCHED'
        status_log = PartnerOrderStatusLog(
            order_id=order.id,
            from_status='READY_TO_DISPATCH',
            to_status='DISPATCHED',
            changed_by_id=employee.id,
            changed_at=get_indian_time(),
            remarks=f"Dispatched via {data.courier_name}. AWB: {data.awb_number}"
        )
        db.add(status_log)
        
        db.commit()
        db.refresh(dispatch)

        # DC_STOCK_MULTICOMP_001 T07: write SALE stock_ledger entries per order line
        try:
            from app.services.stock_service import append_stock_ledger as _asl
            from decimal import Decimal as _Dec
            _dispatch_date = data.dispatch_date or get_indian_time().date()
            for line in (order.line_items or []):
                if not line.item_id or not line.quantity or line.quantity <= 0:
                    continue
                try:
                    _asl(
                        db=db,
                        item_id=line.item_id,
                        company_id=order.company_id,
                        entry_type='SALE',
                        quantity_in=_Dec('0'),
                        quantity_out=_Dec(str(line.quantity)),
                        unit_rate=_Dec(str(line.unit_rate or 0)),
                        reference_type='SALE',
                        reference_id=order.id,
                        txn_date=_dispatch_date,
                        reference_number=order.order_number,
                        narration=f"Partner order dispatch {order.order_number}",
                        updated_by_id=employee.id,
                    )
                except Exception as _line_err:
                    import logging as _log
                    _log.getLogger(__name__).warning(
                        f"Stock SALE ledger failed for order {order.id} line item {line.item_id}: {_line_err}"
                    )
            db.commit()
        except Exception as _stock_err:
            import logging as _log
            _log.getLogger(__name__).warning(f"Stock trigger failed on dispatch create: {_stock_err}")

        log_partner_audit(
            db, employee.id, "CREATE_DISPATCH", "PartnerOrderDispatch", dispatch.id,
            new_values=dispatch.to_dict()
        )
        
        return dispatch
    
    @staticmethod
    def update_dispatch(
        db: Session,
        dispatch_id: int,
        data: DispatchUpdate,
        employee: StaffEmployee
    ) -> PartnerOrderDispatch:
        """Update dispatch record"""
        dispatch = db.query(PartnerOrderDispatch).filter(
            PartnerOrderDispatch.id == dispatch_id
        ).first()
        if not dispatch:
            raise PartnerNotFoundError(f"Dispatch with ID {dispatch_id} not found")
        
        old_values = dispatch.to_dict()
        
        update_data = data.dict(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(dispatch, key):
                if key == 'status' and value:
                    value = value.value if hasattr(value, 'value') else value
                setattr(dispatch, key, value)
        
        dispatch.updated_at = get_indian_time()
        
        order = db.query(PartnerOrder).filter(PartnerOrder.id == dispatch.order_id).first()
        
        if data.status and data.status.value == 'DELIVERED':
            order.status = 'DELIVERED'
            status_log = PartnerOrderStatusLog(
                order_id=order.id,
                from_status='DISPATCHED',
                to_status='DELIVERED',
                changed_by_id=employee.id,
                changed_at=get_indian_time(),
                remarks="Delivered"
            )
            db.add(status_log)
        elif data.status and data.status.value == 'IN_TRANSIT':
            order.status = 'IN_TRANSIT'
        
        db.commit()
        db.refresh(dispatch)
        
        log_partner_audit(
            db, employee.id, "UPDATE_DISPATCH", "PartnerOrderDispatch", dispatch.id,
            old_values=old_values,
            new_values=dispatch.to_dict()
        )
        
        return dispatch


class PartnerInvoiceService:
    """Service layer for Partner Invoice management"""
    
    @staticmethod
    def generate_invoice(
        db: Session,
        order_id: int,
        data: InvoiceGenerateRequest,
        employee: StaffEmployee
    ) -> PartnerInvoice:
        """Generate invoice for a dispatched order"""
        order = db.query(PartnerOrder).options(
            joinedload(PartnerOrder.line_items),
            joinedload(PartnerOrder.partner)
        ).filter(PartnerOrder.id == order_id).first()
        
        if not order:
            raise PartnerNotFoundError(f"Order with ID {order_id} not found")
        
        valid_statuses = ['DISPATCHED', 'IN_TRANSIT', 'DELIVERED']
        if order.status not in valid_statuses:
            raise PartnerValidationError(f"Cannot generate invoice. Order status: {order.status}")
        
        existing = db.query(PartnerInvoice).filter(
            PartnerInvoice.order_id == order_id
        ).first()
        if existing:
            raise PartnerDuplicateError(f"Invoice already exists: {existing.invoice_number}")
        
        invoice_number = PartnerNumberingService.get_next_invoice_number(db, order.company_id)
        
        company = db.query(AssociatedCompany).filter(
            AssociatedCompany.id == order.company_id
        ).first()
        partner = order.partner
        
        is_intra_state = (
            company.state and partner.billing_state and 
            company.state.lower() == partner.billing_state.lower()
        )
        
        taxable_amount = order.subtotal - order.discount_amount
        
        if is_intra_state:
            cgst_rate = Decimal('9')
            sgst_rate = Decimal('9')
            igst_rate = Decimal('0')
            cgst_amount = taxable_amount * (cgst_rate / Decimal('100'))
            sgst_amount = taxable_amount * (sgst_rate / Decimal('100'))
            igst_amount = Decimal('0')
        else:
            cgst_rate = Decimal('0')
            sgst_rate = Decimal('0')
            igst_rate = Decimal('18')
            cgst_amount = Decimal('0')
            sgst_amount = Decimal('0')
            igst_amount = taxable_amount * (igst_rate / Decimal('100'))
        
        total_tax = cgst_amount + sgst_amount + igst_amount
        grand_total = taxable_amount + total_tax
        
        total_payments = db.query(func.sum(PartnerPaymentRecord.amount)).filter(
            PartnerPaymentRecord.order_id == order_id,
            PartnerPaymentRecord.verified == True
        ).scalar() or Decimal('0')
        
        invoice = PartnerInvoice(
            invoice_number=invoice_number,
            order_id=order_id,
            partner_id=order.partner_id,
            company_id=order.company_id,
            invoice_date=date.today(),
            due_date=data.due_date,
            subtotal=order.subtotal,
            discount_amount=order.discount_amount,
            taxable_amount=taxable_amount,
            cgst_rate=cgst_rate,
            cgst_amount=cgst_amount,
            sgst_rate=sgst_rate,
            sgst_amount=sgst_amount,
            igst_rate=igst_rate,
            igst_amount=igst_amount,
            total_tax=total_tax,
            grand_total=grand_total,
            payment_status='PAID' if total_payments >= grand_total else ('PARTIAL' if total_payments > 0 else 'PENDING'),
            amount_received=total_payments,
            balance_due=grand_total - total_payments,
            remarks=data.remarks,
            terms_conditions=data.terms_conditions,
            generated_by_id=employee.id
        )
        
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        log_partner_audit(
            db, employee.id, "GENERATE_INVOICE", "PartnerInvoice", invoice.id,
            new_values=invoice.to_dict()
        )
        
        return invoice
    
    @staticmethod
    def get_invoice(db: Session, invoice_id: int) -> Optional[PartnerInvoice]:
        """Get invoice by ID"""
        return db.query(PartnerInvoice).filter(PartnerInvoice.id == invoice_id).first()
    
    @staticmethod
    def get_invoice_by_order(db: Session, order_id: int) -> Optional[PartnerInvoice]:
        """Get invoice by order ID"""
        return db.query(PartnerInvoice).filter(PartnerInvoice.order_id == order_id).first()
    
    @staticmethod
    def list_invoices(
        db: Session,
        company_id: Optional[int] = None,
        partner_id: Optional[int] = None,
        payment_status: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[PartnerInvoice], int]:
        """List invoices with filters"""
        query = db.query(PartnerInvoice)
        
        if company_id:
            query = query.filter(PartnerInvoice.company_id == company_id)
        
        if partner_id:
            query = query.filter(PartnerInvoice.partner_id == partner_id)
        
        if payment_status:
            query = query.filter(PartnerInvoice.payment_status == payment_status)
        
        if from_date:
            query = query.filter(PartnerInvoice.invoice_date >= from_date)
        
        if to_date:
            query = query.filter(PartnerInvoice.invoice_date <= to_date)
        
        total = query.count()
        invoices = query.order_by(desc(PartnerInvoice.created_at)).offset(skip).limit(limit).all()
        
        return invoices, total

    @staticmethod
    def list_payments(
        db: Session,
        order_id: Optional[int] = None,
        partner_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[dict]:
        """List payments with filters"""
        query = db.query(PartnerPaymentRecord)
        
        if order_id:
            query = query.filter(PartnerPaymentRecord.order_id == order_id)
        
        if partner_id:
            query = query.join(PartnerOrder).filter(PartnerOrder.partner_id == partner_id)
        
        if status:
            query = query.filter(PartnerPaymentRecord.status == status)
        
        payments = query.order_by(desc(PartnerPaymentRecord.created_at)).offset(skip).limit(limit).all()
        return [p.to_dict() for p in payments]
    
    @staticmethod
    def update_payment_status(
        db: Session,
        payment_id: int,
        status: str,
        verified_by: int,
        remarks: Optional[str] = None
    ) -> dict:
        """Update payment status (VERIFIED, REJECTED)"""
        payment = db.query(PartnerPaymentRecord).filter(PartnerPaymentRecord.id == payment_id).first()
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        payment.status = status
        payment.verified_by_id = verified_by
        payment.verified_at = get_indian_time()
        if remarks:
            payment.remarks = remarks
        
        db.commit()
        db.refresh(payment)
        
        log_partner_audit(
            db, verified_by, f"PAYMENT_{status}", "PartnerPaymentRecord", payment.id,
            new_values={"status": status}
        )
        
        return payment.to_dict()
    
    @staticmethod
    def update_order_status(
        db: Session,
        order_id: int,
        new_status: str,
        updated_by: int
    ) -> dict:
        """Update order status"""
        order = db.query(PartnerOrder).filter(PartnerOrder.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        old_status = order.status
        order.status = new_status
        order.updated_at = get_indian_time()
        
        if new_status == 'DELIVERED':
            order.delivered_at = get_indian_time()
        
        db.commit()
        db.refresh(order)
        
        log_partner_audit(
            db, updated_by, "UPDATE_ORDER_STATUS", "PartnerOrder", order.id,
            old_values={"status": old_status},
            new_values={"status": new_status}
        )
        
        return order.to_dict()
    
    @staticmethod
    def list_pricing_profiles(
        db: Session,
        partner_id: Optional[int] = None,
        item_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[dict]:
        """List pricing profiles with filters"""
        query = db.query(PartnerPricingProfile)
        
        if partner_id:
            query = query.filter(PartnerPricingProfile.partner_id == partner_id)
        
        if item_id:
            query = query.filter(PartnerPricingProfile.item_id == item_id)
        
        profiles = query.order_by(desc(PartnerPricingProfile.created_at)).offset(skip).limit(limit).all()
        return [p.to_dict() for p in profiles]
