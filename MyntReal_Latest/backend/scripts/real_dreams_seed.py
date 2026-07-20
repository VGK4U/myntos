#!/usr/bin/env python3
"""
Real Dreams E2E Validation Data Seeder
Creates complete sample data for end-to-end testing of Real Dreams workflow.

Run with: cd backend && python -m scripts.real_dreams_seed
"""

import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import engine, SessionLocal
from app.models.staff_accounts import AssociatedCompany, OfficialPartner, PartnerCompanySegment
from app.models.real_dreams import (
    RDCompanyConfig, RDPartnerProfile, RDPropertyType, RDAmenity,
    RDProperty, RDPropertyMedia, RDPropertyAmenity, RDLead, RDLeadFollowup, RDDeal
)


def seed_real_dreams_data():
    """Seed complete Real Dreams test data"""
    db = SessionLocal()
    try:
        print("=" * 60)
        print("REAL DREAMS E2E DATA SEEDER")
        print("=" * 60)
        
        # Step 1: Ensure test company exists and is enabled
        print("\n[1/8] Setting up test company...")
        test_company = db.query(AssociatedCompany).filter_by(company_code="RDTEST").first()
        if not test_company:
            test_company = AssociatedCompany(
                company_code="RDTEST",
                company_name="Real Dreams Test Company",
                company_type="SUBSIDIARY",
                city="Mumbai",
                state="Maharashtra",
                is_active=True
            )
            db.add(test_company)
            db.flush()
            print(f"   Created company: {test_company.company_name} (ID: {test_company.id})")
        else:
            print(f"   Using existing company: {test_company.company_name} (ID: {test_company.id})")
        
        company_id = test_company.id
        
        # Step 2: Enable Real Dreams for this company
        print("\n[2/8] Enabling Real Dreams for company...")
        rd_config = db.query(RDCompanyConfig).filter_by(company_id=company_id).first()
        if not rd_config:
            rd_config = RDCompanyConfig(
                company_id=company_id,
                is_enabled=True,
                allow_partner_listings=True,
                allow_employee_listings=True,
                allow_member_listings=True,
                default_commission_percent=Decimal("2.50"),
                auto_approve_partner_properties=False,
                auto_approve_employee_properties=False,
                max_images_per_property=15,
                max_properties_per_member=10,
                enabled_by_id=1,
                enabled_at=datetime.utcnow()
            )
            db.add(rd_config)
            print("   Real Dreams ENABLED for company")
        else:
            rd_config.is_enabled = True
            print("   Real Dreams already enabled, updated config")
        
        # Step 3: Create Official Partners
        print("\n[3/8] Creating Official Partners...")
        partners_data = [
            {
                "partner_code": "RD-DLR001",
                "partner_name": "Premium Real Estate Dealers",
                "category": "DEALER",
                "contact_person": "Rahul Sharma",
                "phone": "9876543210",
                "email": "rahul@premiumrealestate.com",
                "city": "Mumbai",
                "state": "Maharashtra",
                "is_active": True
            },
            {
                "partner_code": "RD-BLD001",
                "partner_name": "Skyline Builders Pvt Ltd",
                "category": "DISTRIBUTOR",
                "contact_person": "Priya Patel",
                "phone": "9876543211",
                "email": "priya@skylinebuilders.com",
                "city": "Pune",
                "state": "Maharashtra",
                "is_active": True
            },
            {
                "partner_code": "RD-AGT001",
                "partner_name": "PropertyFirst Agents",
                "category": "VENDOR",
                "contact_person": "Amit Kumar",
                "phone": "9876543212",
                "email": "amit@propertyfirst.in",
                "city": "Bangalore",
                "state": "Karnataka",
                "is_active": True
            }
        ]
        
        created_partners = []
        for p_data in partners_data:
            partner = db.query(OfficialPartner).filter_by(partner_code=p_data["partner_code"]).first()
            if not partner:
                partner = OfficialPartner(**p_data)
                db.add(partner)
                db.flush()
                print(f"   Created: {partner.partner_name} ({partner.partner_code})")
            else:
                print(f"   Exists: {partner.partner_name} ({partner.partner_code})")
            created_partners.append(partner)
            
            # Link partner to company via PartnerCompanySegment
            segment = db.query(PartnerCompanySegment).filter_by(
                partner_id=partner.id,
                company_id=company_id
            ).first()
            if not segment:
                segment = PartnerCompanySegment(
                    partner_id=partner.id,
                    company_id=company_id,
                    is_active=True
                )
                db.add(segment)
                print(f"      Linked to company")
        
        # Step 4: Create Property Types
        print("\n[4/8] Creating Property Types...")
        property_types = [
            {"name": "Residential Flat", "slug": "residential-flat", "description": "Apartment in residential complex", "icon": "fas fa-building"},
            {"name": "Independent Villa", "slug": "independent-villa", "description": "Standalone villa with garden", "icon": "fas fa-home"},
            {"name": "Commercial Plot", "slug": "commercial-plot", "description": "Plot for commercial use", "icon": "fas fa-store"},
            {"name": "Agricultural Land", "slug": "agricultural-land", "description": "Farm land for agriculture", "icon": "fas fa-tractor"},
            {"name": "Row House", "slug": "row-house", "description": "Connected housing unit", "icon": "fas fa-house-user"}
        ]
        
        created_types = []
        for pt_data in property_types:
            pt = db.query(RDPropertyType).filter_by(name=pt_data["name"], company_id=company_id).first()
            if not pt:
                pt = RDPropertyType(company_id=company_id, is_active=True, **pt_data)
                db.add(pt)
                db.flush()
                print(f"   Created: {pt.name}")
            else:
                print(f"   Exists: {pt.name}")
            created_types.append(pt)
        
        # Step 5: Create Amenities
        print("\n[5/8] Creating Amenities...")
        amenities = [
            {"name": "Swimming Pool", "icon": "fas fa-swimming-pool", "category": "LIFESTYLE"},
            {"name": "Gymnasium", "icon": "fas fa-dumbbell", "category": "LIFESTYLE"},
            {"name": "24x7 Security", "icon": "fas fa-shield-alt", "category": "SECURITY"},
            {"name": "Covered Parking", "icon": "fas fa-parking", "category": "PARKING"},
            {"name": "Power Backup", "icon": "fas fa-bolt", "category": "UTILITIES"},
            {"name": "Children Play Area", "icon": "fas fa-child", "category": "OUTDOOR"},
            {"name": "Clubhouse", "icon": "fas fa-users", "category": "INDOOR"},
            {"name": "Garden/Landscaping", "icon": "fas fa-tree", "category": "OUTDOOR"}
        ]
        
        created_amenities = []
        for am_data in amenities:
            am = db.query(RDAmenity).filter_by(name=am_data["name"], company_id=company_id).first()
            if not am:
                am = RDAmenity(company_id=company_id, is_active=True, **am_data)
                db.add(am)
                db.flush()
                print(f"   Created: {am.name}")
            else:
                print(f"   Exists: {am.name}")
            created_amenities.append(am)
        
        db.flush()
        
        # Step 6: Create Real Dreams Partner Profiles (various statuses)
        print("\n[6/8] Creating Real Dreams Partner Profiles...")
        profiles_data = [
            {
                "partner": created_partners[0],
                "partner_type": "REAL_ESTATE_DEALER",
                "rera_registration_number": "RERA/MH/2024/12345",
                "specialization": ["Residential Flats", "Villas", "Premium Properties"],
                "service_areas": ["Mumbai", "Thane", "Navi Mumbai"],
                "status": "APPROVED",
                "nda_signed": True
            },
            {
                "partner": created_partners[1],
                "partner_type": "BUILDER",
                "rera_registration_number": "RERA/MH/2024/67890",
                "specialization": ["Commercial Complexes", "IT Parks"],
                "service_areas": ["Pune", "Hinjewadi", "Wakad"],
                "status": "PENDING",
                "nda_signed": True
            },
            {
                "partner": created_partners[2],
                "partner_type": "AGENT",
                "rera_registration_number": "RERA/KA/2024/11111",
                "specialization": ["Residential", "Rental"],
                "service_areas": ["Bangalore", "Electronic City", "Whitefield"],
                "status": "DRAFT",
                "nda_signed": False
            }
        ]
        
        created_profiles = []
        for prof_data in profiles_data:
            profile = db.query(RDPartnerProfile).filter_by(
                partner_id=prof_data["partner"].id,
                company_id=company_id
            ).first()
            if not profile:
                profile = RDPartnerProfile(
                    company_id=company_id,
                    partner_id=prof_data["partner"].id,
                    partner_type=prof_data["partner_type"],
                    rera_registration_number=prof_data["rera_registration_number"],
                    specialization=prof_data["specialization"],
                    service_areas=prof_data["service_areas"],
                    status=prof_data["status"],
                    nda_signed=prof_data["nda_signed"],
                    nda_signed_at=datetime.utcnow() if prof_data["nda_signed"] else None,
                    created_by_id=1
                )
                if prof_data["status"] == "APPROVED":
                    profile.reviewed_by_id = 1
                    profile.reviewed_at = datetime.utcnow()
                db.add(profile)
                db.flush()
                print(f"   Created: {prof_data['partner'].partner_name} [{prof_data['status']}]")
            else:
                print(f"   Exists: {prof_data['partner'].partner_name}")
            created_profiles.append(profile)
        
        # Step 7: Create Properties (various statuses)
        print("\n[7/8] Creating Properties...")
        approved_profile = created_profiles[0]  # Use the approved partner
        
        properties_data = [
            {
                "property_code": "RD-PROP-001",
                "title": "Luxury 3BHK Sea View Apartment",
                "description": "Premium sea-facing apartment with modern amenities in prime location. 24x7 security, covered parking, and world-class clubhouse.",
                "property_type_id": created_types[0].id,
                "address": "Palm Beach Road, Sector 25",
                "city": "Navi Mumbai",
                "state": "Maharashtra",
                "pincode": "400614",
                "latitude": Decimal("19.0330"),
                "longitude": Decimal("73.0297"),
                "total_area": Decimal("1850"),
                "area_unit": "SQ_FT",
                "bedrooms": 3,
                "bathrooms": 3,
                "floor_number": 12,
                "total_floors": 25,
                "listed_price": Decimal("18500000"),
                "price_per_unit": Decimal("10000"),
                "price_unit": "SQ_FT",
                "is_negotiable": True,
                "status": "APPROVED",
                "amenity_ids": [created_amenities[0].id, created_amenities[1].id, created_amenities[2].id, created_amenities[3].id]
            },
            {
                "property_code": "RD-PROP-002",
                "title": "Modern 2BHK in IT Hub",
                "description": "Well-designed apartment near major IT companies. Perfect for working professionals.",
                "property_type_id": created_types[0].id,
                "address": "Hinjewadi Phase 2",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411057",
                "latitude": Decimal("18.5912"),
                "longitude": Decimal("73.7389"),
                "total_area": Decimal("1200"),
                "area_unit": "SQ_FT",
                "bedrooms": 2,
                "bathrooms": 2,
                "floor_number": 8,
                "total_floors": 15,
                "listed_price": Decimal("7500000"),
                "price_per_unit": Decimal("6250"),
                "price_unit": "SQ_FT",
                "is_negotiable": True,
                "status": "PENDING",
                "amenity_ids": [created_amenities[1].id, created_amenities[4].id]
            },
            {
                "property_code": "RD-PROP-003",
                "title": "Independent Villa with Garden",
                "description": "Spacious villa with private garden and parking. Ideal for families.",
                "property_type_id": created_types[1].id,
                "address": "Koregaon Park",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411001",
                "latitude": Decimal("18.5362"),
                "longitude": Decimal("73.8939"),
                "total_area": Decimal("3500"),
                "area_unit": "SQ_FT",
                "bedrooms": 4,
                "bathrooms": 4,
                "floor_number": None,
                "total_floors": 2,
                "listed_price": Decimal("35000000"),
                "price_per_unit": Decimal("10000"),
                "price_unit": "SQ_FT",
                "is_negotiable": False,
                "status": "DRAFT",
                "amenity_ids": [created_amenities[2].id, created_amenities[7].id]
            }
        ]
        
        created_properties = []
        for prop_data in properties_data:
            amenity_ids = prop_data.pop("amenity_ids")
            prop = db.query(RDProperty).filter_by(
                title=prop_data["title"],
                company_id=company_id
            ).first()
            if not prop:
                prop = RDProperty(
                    company_id=company_id,
                    partner_profile_id=approved_profile.id,
                    created_by_id=1,
                    **prop_data
                )
                if prop_data["status"] == "APPROVED":
                    prop.approved_by_id = 1
                    prop.approved_at = datetime.utcnow()
                db.add(prop)
                db.flush()
                
                # Add amenities via junction table
                for am_id in amenity_ids:
                    prop_amenity = RDPropertyAmenity(
                        property_id=prop.id,
                        amenity_id=am_id
                    )
                    db.add(prop_amenity)
                
                print(f"   Created: {prop.title} [{prop.status}]")
            else:
                print(f"   Exists: {prop.title}")
            created_properties.append(prop)
        
        # Step 8: Create Leads and Deals
        print("\n[8/8] Creating Leads and Follow-ups...")
        approved_property = created_properties[0]  # Use the approved property
        
        leads_data = [
            {
                "property": approved_property,
                "lead_code": "RD-LEAD-001",
                "customer_name": "Vikram Mehta",
                "mobile_1": "9988776655",
                "email": "vikram.mehta@gmail.com",
                "budget_min": Decimal("15000000"),
                "budget_max": Decimal("20000000"),
                "preferred_location": "Navi Mumbai",
                "status": "SITE_VISIT",
                "lead_source": "WEBSITE"
            },
            {
                "property": approved_property,
                "lead_code": "RD-LEAD-002",
                "customer_name": "Sneha Reddy",
                "mobile_1": "9988776656",
                "email": "sneha.reddy@gmail.com",
                "budget_min": Decimal("17000000"),
                "budget_max": Decimal("19000000"),
                "preferred_location": "Mumbai",
                "status": "NEGOTIATION",
                "lead_source": "REFERRAL"
            },
            {
                "property": approved_property,
                "lead_code": "RD-LEAD-003",
                "customer_name": "Arjun Singh",
                "mobile_1": "9988776657",
                "email": "arjun.singh@gmail.com",
                "budget_min": Decimal("16000000"),
                "budget_max": Decimal("18500000"),
                "preferred_location": "Navi Mumbai",
                "status": "DEAL_CLOSED",
                "lead_source": "REFERRAL"
            }
        ]
        
        created_leads = []
        for lead_data in leads_data:
            prop = lead_data.pop("property")
            lead = db.query(RDLead).filter_by(
                lead_code=lead_data["lead_code"],
                company_id=company_id
            ).first()
            if not lead:
                lead = RDLead(
                    company_id=company_id,
                    property_id=prop.id,
                    partner_profile_id=approved_profile.id,
                    assigned_to_employee_id=1,
                    lead_date=datetime.utcnow().date(),
                    lead_type="PROPERTY_INQUIRY",
                    **lead_data
                )
                db.add(lead)
                db.flush()
                
                # Add follow-up for active leads
                if lead.status in ["SITE_VISIT", "NEGOTIATION"]:
                    followup = RDLeadFollowup(
                        lead_id=lead.id,
                        followup_date=datetime.utcnow().date(),
                        followup_type="CALL",
                        notes=f"Initial discussion with {lead.customer_name}",
                        outcome="Interested",
                        next_action="Schedule site visit",
                        created_by_id=1
                    )
                    db.add(followup)
                
                print(f"   Created Lead: {lead.customer_name} [{lead.status}]")
            else:
                print(f"   Exists Lead: {lead.customer_name}")
            created_leads.append(lead)
        
        # Create a Deal for the closed lead
        closed_lead = [l for l in created_leads if l.status == "DEAL_CLOSED"][0] if created_leads else None
        if closed_lead:
            deal = db.query(RDDeal).filter_by(lead_id=closed_lead.id).first()
            if not deal:
                deal = RDDeal(
                    company_id=company_id,
                    deal_code="RD-DEAL-001",
                    lead_id=closed_lead.id,
                    property_id=approved_property.id,
                    partner_profile_id=approved_profile.id,
                    buyer_name=closed_lead.customer_name,
                    buyer_phone=closed_lead.mobile_1,
                    buyer_email=closed_lead.email,
                    deal_amount=Decimal("18200000"),
                    booking_amount_paid=Decimal("500000"),
                    payment_mode="BANK_TRANSFER",
                    deal_date=datetime.utcnow().date(),
                    commission_amount=Decimal("455000"),
                    commission_status="CALCULATED",
                    status="COMPLETED",
                    rvz_approved_by_id=1,
                    rvz_approved_at=datetime.utcnow(),
                    created_by_id=1
                )
                db.add(deal)
                print(f"   Created Deal: Rs. {deal.deal_amount} [COMPLETED]")
        
        db.commit()
        
        print("\n" + "=" * 60)
        print("SEEDING COMPLETE!")
        print("=" * 60)
        print(f"\nTest Company: {test_company.company_name} (ID: {company_id})")
        print(f"Official Partners: {len(created_partners)}")
        print(f"RD Partner Profiles: {len(created_profiles)}")
        print(f"Properties: {len(created_properties)}")
        print(f"Leads: {len(created_leads)}")
        print("\nYou can now test the complete flow from frontend!")
        print("\nNavigation Guide:")
        print("  1. Partner Master: /staff/partners/master")
        print("  2. Real Dreams Partners: /rvz/real-dreams/partners")
        print("  3. Real Dreams Properties: /rvz/real-dreams/properties")
        print("  4. Real Dreams CRM/Leads: /rvz/crm/leads")
        print("  5. Public Marketplace: /real-dreams/marketplace")
        
        return company_id
        
    except Exception as e:
        db.rollback()
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_real_dreams_data()
