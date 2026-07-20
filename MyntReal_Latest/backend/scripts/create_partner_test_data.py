"""
Partner System Test Data Creator
DC_PARTNER_001: Creates comprehensive test data for Official Partner Order Management System
Created: Dec 06, 2025
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.staff_accounts import (
    OfficialPartner, PartnerCompanySegment, PartnerPricingProfile,
    PartnerOrder, PartnerOrderLine, PartnerOrderStatusLog,
    PartnerOrderDispatch, PartnerPaymentRecord, PartnerInvoice,
    CompanySegment, AssociatedCompany, StockItemMaster
)

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def get_indian_time():
    from datetime import timezone
    import pytz
    return datetime.now(pytz.timezone('Asia/Kolkata')).replace(tzinfo=None)

def cleanup_existing_test_data():
    """Remove existing test data to avoid duplicates"""
    print("Cleaning up existing test data...")
    session.query(PartnerOrderLine).delete()
    session.query(PartnerOrderStatusLog).delete()
    session.query(PartnerPaymentRecord).delete()
    session.query(PartnerOrderDispatch).delete()
    session.query(PartnerInvoice).delete()
    session.query(PartnerOrder).delete()
    session.query(PartnerPricingProfile).delete()
    session.query(PartnerCompanySegment).delete()
    session.query(OfficialPartner).delete()
    session.commit()
    print("Cleanup complete!")

def create_company_segments():
    """Create company segments if they don't exist"""
    print("Creating company segments...")
    
    existing = session.query(CompanySegment).filter(CompanySegment.is_active == True).count()
    if existing > 0:
        print(f"  Found {existing} existing segments")
        return
    
    segments_data = [
        {'segment_code': 'STORE01', 'segment_name': 'Main Showroom', 'description': 'Primary retail showroom', 'company_id': 16},
        {'segment_code': 'STORE02', 'segment_name': 'East Zone Outlet', 'description': 'Eastern region outlet', 'company_id': 16},
        {'segment_code': 'WH01', 'segment_name': 'Central Warehouse', 'description': 'Main warehouse facility', 'company_id': 17},
        {'segment_code': 'FACT01', 'segment_name': 'Production Unit', 'description': 'Manufacturing facility', 'company_id': 17},
    ]
    
    for seg_data in segments_data:
        segment = CompanySegment(
            segment_code=seg_data['segment_code'],
            segment_name=seg_data['segment_name'],
            description=seg_data['description'],
            company_id=seg_data['company_id'],
            is_active=True,
            created_by_id=1,
            created_at=get_indian_time(),
            updated_at=get_indian_time()
        )
        session.add(segment)
    
    session.commit()
    print(f"  Created {len(segments_data)} segments")

def create_partners():
    """Create test partners for all 3 categories"""
    print("Creating test partners...")
    
    partners_data = [
        {
            'partner_code': 'DLR001',
            'partner_name': 'Green Motors Pvt Ltd',
            'category': 'DEALER',
            'contact_person': 'Rajesh Kumar',
            'phone': '9876543210',
            'email': 'rajesh@greenmotors.com',
            'whatsapp_number': '9876543210',
            'gst_number': '27AABCG1234A1Z5',
            'pan_number': 'AABCG1234A',
            'address': '123, Industrial Area, Sector 5',
            'city': 'Pune',
            'state': 'Maharashtra',
            'pincode': '411001',
            'zone': 'West',
            'payment_terms': 'CREDIT',
            'credit_limit': 500000,
            'credit_days': 30,
        },
        {
            'partner_code': 'DLR002',
            'partner_name': 'EV World Chennai',
            'category': 'DEALER',
            'contact_person': 'Sundar Rajan',
            'phone': '9876543211',
            'email': 'sundar@evworldchennai.com',
            'whatsapp_number': '9876543211',
            'gst_number': '33AABCE5678B2Z6',
            'pan_number': 'AABCE5678B',
            'address': '45, Anna Nagar Main Road',
            'city': 'Chennai',
            'state': 'Tamil Nadu',
            'pincode': '600040',
            'zone': 'South',
            'payment_terms': 'ADVANCE',
            'credit_limit': 0,
            'credit_days': 0,
        },
        {
            'partner_code': 'DIST001',
            'partner_name': 'National EV Distributors',
            'category': 'DISTRIBUTOR',
            'contact_person': 'Amit Sharma',
            'phone': '9876543212',
            'email': 'amit@nedevdist.com',
            'whatsapp_number': '9876543212',
            'gst_number': '09AABCD9012C3Z7',
            'pan_number': 'AABCD9012C',
            'address': '78, Logistic Park, NH-24',
            'city': 'Noida',
            'state': 'Uttar Pradesh',
            'pincode': '201301',
            'zone': 'North',
            'payment_terms': 'PARTIAL_ADVANCE',
            'credit_limit': 1000000,
            'credit_days': 45,
        },
        {
            'partner_code': 'DIST002',
            'partner_name': 'Western Zone Distribution',
            'category': 'DISTRIBUTOR',
            'contact_person': 'Priya Patel',
            'phone': '9876543213',
            'email': 'priya@wzd.co.in',
            'whatsapp_number': '9876543213',
            'gst_number': '24AABCW3456D4Z8',
            'pan_number': 'AABCW3456D',
            'address': '234, GIDC Industrial Estate',
            'city': 'Ahmedabad',
            'state': 'Gujarat',
            'pincode': '380015',
            'zone': 'West',
            'payment_terms': 'CREDIT',
            'credit_limit': 750000,
            'credit_days': 30,
        },
        {
            'partner_code': 'VND001',
            'partner_name': 'Battery Tech Suppliers',
            'category': 'VENDOR',
            'contact_person': 'Vikram Singh',
            'phone': '9876543214',
            'email': 'vikram@batterytech.in',
            'whatsapp_number': '9876543214',
            'gst_number': '07AABCB7890E5Z9',
            'pan_number': 'AABCB7890E',
            'address': '567, Electronics City, Phase 2',
            'city': 'Bangalore',
            'state': 'Karnataka',
            'pincode': '560100',
            'zone': 'South',
            'payment_terms': 'COD',
            'credit_limit': 0,
            'credit_days': 0,
        },
        {
            'partner_code': 'VND002',
            'partner_name': 'Motor Components India',
            'category': 'VENDOR',
            'contact_person': 'Neha Gupta',
            'phone': '9876543215',
            'email': 'neha@motorcomp.in',
            'whatsapp_number': '9876543215',
            'gst_number': '06AABCM2345F6Z0',
            'pan_number': 'AABCM2345F',
            'address': '890, Auto Parts Hub',
            'city': 'Gurugram',
            'state': 'Haryana',
            'pincode': '122001',
            'zone': 'North',
            'payment_terms': 'ADVANCE',
            'credit_limit': 0,
            'credit_days': 0,
        },
    ]
    
    created_partners = []
    for p_data in partners_data:
        partner = OfficialPartner(
            partner_code=p_data['partner_code'],
            partner_name=p_data['partner_name'],
            category=p_data['category'],
            contact_person=p_data['contact_person'],
            phone=p_data['phone'],
            email=p_data['email'],
            whatsapp_number=p_data['whatsapp_number'],
            gst_number=p_data['gst_number'],
            pan_number=p_data['pan_number'],
            address=p_data['address'],
            city=p_data['city'],
            state=p_data['state'],
            pincode=p_data['pincode'],
            zone=p_data['zone'],
            payment_terms=p_data['payment_terms'],
            credit_limit=Decimal(str(p_data['credit_limit'])),
            credit_days=p_data['credit_days'],
            is_active=True,
            created_by_id=1,
            created_at=get_indian_time(),
            updated_at=get_indian_time()
        )
        session.add(partner)
        created_partners.append(partner)
    
    session.commit()
    print(f"  Created {len(created_partners)} partners")
    return created_partners

def create_partner_company_segments(partners):
    """Assign partners to companies and segments"""
    print("Creating partner-company-segment assignments...")
    
    segments = session.query(CompanySegment).filter(CompanySegment.is_active == True).all()
    segment_map = {s.segment_code: s for s in segments}
    
    assignments = []
    for partner in partners:
        if partner.category == 'DEALER':
            pcs = PartnerCompanySegment(
                partner_id=partner.id,
                company_id=16,
                segment_id=segment_map.get('STORE01', segments[0] if segments else None).id if segments else None,
                is_primary=True,
                is_active=True,
                created_by_id=1,
                created_at=get_indian_time()
            )
            session.add(pcs)
            assignments.append(pcs)
        elif partner.category == 'DISTRIBUTOR':
            pcs = PartnerCompanySegment(
                partner_id=partner.id,
                company_id=17,
                segment_id=segment_map.get('WH01', segments[0] if segments else None).id if segments else None,
                is_primary=True,
                is_active=True,
                created_by_id=1,
                created_at=get_indian_time()
            )
            session.add(pcs)
            assignments.append(pcs)
        elif partner.category == 'VENDOR':
            pcs = PartnerCompanySegment(
                partner_id=partner.id,
                company_id=17,
                segment_id=segment_map.get('FACT01', segments[0] if segments else None).id if segments else None,
                is_primary=True,
                is_active=True,
                created_by_id=1,
                created_at=get_indian_time()
            )
            session.add(pcs)
            assignments.append(pcs)
    
    session.commit()
    print(f"  Created {len(assignments)} partner-company assignments")

def create_pricing_profiles(partners):
    """Create pricing profiles for partners"""
    print("Creating pricing profiles...")
    
    items = session.query(StockItemMaster).limit(5).all()
    if not items:
        print("  No stock items found, skipping pricing profiles")
        return
    
    profiles_created = 0
    today = date.today()
    
    for partner in partners:
        if partner.category in ['DEALER', 'DISTRIBUTOR']:
            for idx, item in enumerate(items):
                profile = PartnerPricingProfile(
                    partner_id=partner.id,
                    company_id=16 if partner.category == 'DEALER' else 17,
                    item_id=item.id,
                    discount_pct=Decimal(str(5 + idx * 2)),
                    special_rate=None,
                    effective_from=today,
                    effective_to=today + timedelta(days=365),
                    is_active=True,
                    created_by_id=1,
                    created_at=get_indian_time(),
                    updated_at=get_indian_time()
                )
                session.add(profile)
                profiles_created += 1
    
    session.commit()
    print(f"  Created {profiles_created} pricing profiles")

def create_orders(partners):
    """Create orders in different statuses for testing workflow"""
    print("Creating test orders...")
    
    items = session.query(StockItemMaster).limit(3).all()
    if not items:
        print("  No stock items found, skipping orders")
        return []
    
    order_scenarios = [
        {'status': 'DRAFT', 'partner_idx': 0},
        {'status': 'PI_GENERATED', 'partner_idx': 0},
        {'status': 'PENDING_APPROVAL', 'partner_idx': 1},
        {'status': 'APPROVED', 'partner_idx': 2},
        {'status': 'PAYMENT_PENDING', 'partner_idx': 3},
        {'status': 'PAYMENT_CONFIRMED', 'partner_idx': 0},
        {'status': 'ROUTED_TO_PRODUCTION', 'partner_idx': 1},
        {'status': 'IN_MANUFACTURING', 'partner_idx': 2},
        {'status': 'PROCUREMENT_IN_PROGRESS', 'partner_idx': 3},
        {'status': 'READY_TO_DISPATCH', 'partner_idx': 0},
        {'status': 'DISPATCHED', 'partner_idx': 1},
        {'status': 'DELIVERED', 'partner_idx': 2},
    ]
    
    created_orders = []
    today = date.today()
    now = get_indian_time()
    
    for idx, scenario in enumerate(order_scenarios):
        partner = partners[scenario['partner_idx'] % len(partners)]
        order_number = f"ORD{today.strftime('%Y%m%d')}{idx+1:04d}"
        pi_number = f"PI{today.strftime('%Y%m%d')}{idx+1:04d}" if scenario['status'] != 'DRAFT' else None
        
        order = PartnerOrder(
            order_number=order_number,
            pi_number=pi_number,
            partner_id=partner.id,
            company_id=16 if partner.category == 'DEALER' else 17,
            segment_id=None,
            order_date=today - timedelta(days=idx),
            commitment_date=today + timedelta(days=7-idx),
            status=scenario['status'],
            subtotal=Decimal('50000'),
            discount_amount=Decimal('2500'),
            tax_amount=Decimal('8550'),
            grand_total=Decimal('56050'),
            placed_by_id=1,
            placed_by_partner=False,
            remarks=f"Test order for {scenario['status']} status validation",
            internal_notes=f"Created by test data script for {partner.partner_name}",
            created_by_id=1,
            updated_by_id=1,
            created_at=now,
            updated_at=now
        )
        
        if scenario['status'] != 'DRAFT':
            order.pi_generated_at = now
            order.pi_generated_by_id = 1
        
        if scenario['status'] in ['APPROVED', 'PAYMENT_PENDING', 'PAYMENT_CONFIRMED', 
                                   'ROUTED_TO_PRODUCTION', 'IN_MANUFACTURING', 'PROCUREMENT_IN_PROGRESS',
                                   'READY_TO_DISPATCH', 'DISPATCHED', 'DELIVERED']:
            order.approved_by_id = 1
            order.approved_at = now
            order.approval_remarks = "Auto-approved for testing"
        
        if scenario['status'] in ['PAYMENT_CONFIRMED', 'ROUTED_TO_PRODUCTION', 'IN_MANUFACTURING', 
                                   'PROCUREMENT_IN_PROGRESS', 'READY_TO_DISPATCH', 'DISPATCHED', 'DELIVERED']:
            order.payment_confirmed_at = now
            order.payment_confirmed_by_id = 1
        
        if scenario['status'] in ['ROUTED_TO_PRODUCTION', 'IN_MANUFACTURING', 'PROCUREMENT_IN_PROGRESS', 
                                   'READY_TO_DISPATCH', 'DISPATCHED', 'DELIVERED']:
            order.routed_to = 'PRODUCTION' if scenario['status'] in ['ROUTED_TO_PRODUCTION', 'IN_MANUFACTURING'] else 'DIRECT_DISPATCH'
            order.routed_at = now
            order.routed_by_id = 1
        
        session.add(order)
        created_orders.append(order)
    
    session.commit()
    
    for order in created_orders:
        for item_idx, item in enumerate(items):
            qty = Decimal(str((item_idx + 1) * 10))
            unit_rate = Decimal('5000')
            discount_pct = Decimal('5')
            discount_amount = qty * unit_rate * discount_pct / 100
            line_total = qty * unit_rate - discount_amount
            
            line = PartnerOrderLine(
                order_id=order.id,
                item_id=item.id,
                quantity=qty,
                unit_of_measure='PCS',
                unit_rate=unit_rate,
                discount_pct=discount_pct,
                discount_amount=discount_amount,
                tax_rate=Decimal('18'),
                tax_amount=line_total * Decimal('0.18'),
                line_total=line_total,
                stock_available=True if item_idx == 0 else False,
                requires_manufacturing=True if item_idx == 1 else False,
                requires_procurement=True if item_idx == 2 else False,
                notes=f"Test line item for {item.item_name if hasattr(item, 'item_name') else 'item'}",
                created_at=get_indian_time(),
                updated_at=get_indian_time()
            )
            session.add(line)
        
        status_log = PartnerOrderStatusLog(
            order_id=order.id,
            from_status=None,
            to_status=order.status,
            changed_by_id=1,
            changed_at=get_indian_time(),
            remarks=f"Order created with status {order.status}"
        )
        session.add(status_log)
    
    session.commit()
    print(f"  Created {len(created_orders)} orders with {len(items)} line items each")
    return created_orders

def create_payment_records(orders):
    """Create payment records for orders requiring payment tracking"""
    print("Creating payment records...")
    
    payment_statuses = ['PENDING', 'VERIFIED', 'REJECTED']
    payments_created = 0
    
    for order in orders:
        if order.status in ['PAYMENT_CONFIRMED', 'ROUTED_TO_PRODUCTION', 'IN_MANUFACTURING', 
                            'PROCUREMENT_IN_PROGRESS', 'READY_TO_DISPATCH', 'DISPATCHED', 'DELIVERED']:
            payment = PartnerPaymentRecord(
                order_id=order.id,
                payment_date=date.today(),
                amount=order.grand_total,
                payment_mode='NEFT',
                reference_number=f"REF{order.order_number}",
                bank_name='HDFC Bank',
                remarks='Full payment received',
                status='VERIFIED',
                verified_by_id=1,
                verified_at=get_indian_time(),
                created_by_id=1,
                created_at=get_indian_time(),
                updated_at=get_indian_time()
            )
            session.add(payment)
            payments_created += 1
        elif order.status == 'PAYMENT_PENDING':
            payment = PartnerPaymentRecord(
                order_id=order.id,
                payment_date=date.today(),
                amount=order.grand_total,
                payment_mode='UPI',
                reference_number=f"UPI{order.order_number}",
                bank_name='ICICI Bank',
                remarks='Payment submitted, pending verification',
                status='PENDING',
                created_by_id=1,
                created_at=get_indian_time(),
                updated_at=get_indian_time()
            )
            session.add(payment)
            payments_created += 1
    
    session.commit()
    print(f"  Created {payments_created} payment records")

def create_dispatch_records(orders):
    """Create dispatch records for orders in dispatch/delivered status"""
    print("Creating dispatch records...")
    
    dispatches_created = 0
    
    for order in orders:
        if order.status in ['DISPATCHED', 'DELIVERED']:
            dispatch = PartnerOrderDispatch(
                order_id=order.id,
                dispatch_date=date.today(),
                courier_name='BlueDart Express',
                awb_number=f"BD{order.order_number}",
                tracking_url=f"https://tracking.bluedart.com/{order.order_number}",
                expected_delivery_date=date.today() + timedelta(days=2),
                actual_delivery_date=date.today() if order.status == 'DELIVERED' else None,
                dispatched_by_id=1,
                dispatched_at=get_indian_time(),
                received_by='Store Manager' if order.status == 'DELIVERED' else None,
                received_at=get_indian_time() if order.status == 'DELIVERED' else None,
                delivery_notes='Test dispatch record',
                created_at=get_indian_time(),
                updated_at=get_indian_time()
            )
            session.add(dispatch)
            dispatches_created += 1
    
    session.commit()
    print(f"  Created {dispatches_created} dispatch records")

def create_invoices(orders):
    """Create invoices for dispatched/delivered orders"""
    print("Creating invoices...")
    
    invoices_created = 0
    
    for order in orders:
        if order.status in ['DISPATCHED', 'DELIVERED']:
            invoice_number = f"INV{order.company_id}{date.today().strftime('%Y%m%d')}{invoices_created+1:04d}"
            taxable_amount = order.subtotal - (order.discount_amount or Decimal('0'))
            cgst_amount = taxable_amount * Decimal('0.09')
            sgst_amount = taxable_amount * Decimal('0.09')
            total_tax = cgst_amount + sgst_amount
            
            invoice = PartnerInvoice(
                order_id=order.id,
                partner_id=order.partner_id,
                company_id=order.company_id,
                invoice_number=invoice_number,
                invoice_date=date.today(),
                due_date=date.today() + timedelta(days=30),
                subtotal=order.subtotal,
                discount_amount=order.discount_amount,
                taxable_amount=taxable_amount,
                cgst_rate=Decimal('9'),
                cgst_amount=cgst_amount,
                sgst_rate=Decimal('9'),
                sgst_amount=sgst_amount,
                igst_rate=Decimal('0'),
                igst_amount=Decimal('0'),
                total_tax=total_tax,
                grand_total=order.grand_total,
                amount_in_words=f"Rupees {int(order.grand_total)} Only",
                payment_status='PAID' if order.status == 'DELIVERED' else 'PENDING',
                amount_received=order.grand_total if order.status == 'DELIVERED' else Decimal('0'),
                balance_due=Decimal('0') if order.status == 'DELIVERED' else order.grand_total,
                generated_by_id=1,
                remarks='Test invoice',
                created_at=get_indian_time(),
                updated_at=get_indian_time()
            )
            session.add(invoice)
            invoices_created += 1
    
    session.commit()
    print(f"  Created {invoices_created} invoices")

def main():
    """Main function to create all test data"""
    print("=" * 60)
    print("OFFICIAL PARTNER ORDER MANAGEMENT SYSTEM - TEST DATA CREATOR")
    print("=" * 60)
    print()
    
    try:
        cleanup_existing_test_data()
        
        create_company_segments()
        
        partners = create_partners()
        
        create_partner_company_segments(partners)
        
        create_pricing_profiles(partners)
        
        orders = create_orders(partners)
        
        create_payment_records(orders)
        
        create_dispatch_records(orders)
        
        create_invoices(orders)
        
        print()
        print("=" * 60)
        print("TEST DATA CREATION COMPLETE!")
        print("=" * 60)
        print()
        print("Summary:")
        print(f"  - Partners: {len(partners)} (2 Dealers, 2 Distributors, 2 Vendors)")
        print(f"  - Orders: {len(orders)} (12 orders in different statuses)")
        print("  - Pricing Profiles: Created for Dealers and Distributors")
        print("  - Payment Records: Created for payment-related orders")
        print("  - Dispatch Records: Created for dispatched/delivered orders")
        print("  - Invoices: Created for dispatched/delivered orders")
        print()
        print("You can now test the frontend pages with this data!")
        
    except Exception as e:
        session.rollback()
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()

if __name__ == '__main__':
    main()
