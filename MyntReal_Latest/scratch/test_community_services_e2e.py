import sys
import os
import random
from datetime import date, datetime, timedelta
from decimal import Decimal

# Ensure python path is correct
sys.path.append("/Users/viswanathkari/Documents/Mynt OS/MyntReal_Latest/backend")

from app.core.database import SessionLocal
from app.models.community_service import CommunityService, CommunityRegistration, CommunityCommission
from app.models.staff_accounts import OfficialPartner, VGKTeamCommissionConfig, VGKTeamIncomeEntry
from app.models.crm import CRMLead
from app.services.vgk_commission import calculate_vgk_commissions
from app.api.v1.endpoints.community_services import get_community_member_earnings

def run_e2e_test():
    db = SessionLocal()
    
    # Generate unique codes for this run
    rand_id = random.randint(10000, 99999)
    short_name = f"Seva{rand_id}"
    partner_code = f"COM{rand_id}"
    l1_code = f"L1{rand_id}"
    l2_code = f"L2{rand_id}"
    l5_code = f"L5{rand_id}"
    
    created_entities = {
        "services": [],
        "registrations": [],
        "partners": [],
        "leads": [],
        "commissions": [],
        "income_entries": []
    }
    
    try:
        print(f"Starting E2E run with short_name: {short_name}, partner_code: {partner_code}")

        # 1. Query an active commission category to use
        config = db.query(VGKTeamCommissionConfig).filter(VGKTeamCommissionConfig.is_active == True).first()
        if not config:
            # Create a dummy config if none exists
            config = VGKTeamCommissionConfig(
                category_id=1,
                company_id=1,
                level1_pct=Decimal('10.00'),
                level2_pct=Decimal('5.00'),
                level3_pct=Decimal('2.00'),
                level4_pct=Decimal('1.00'),
                comm_sev_deduction_l1_type='AMOUNT',
                comm_sev_deduction_l1_val=Decimal('1000.00'),
                comm_sev_deduction_l2_type='AMOUNT',
                comm_sev_deduction_l2_val=Decimal('500.00'),
                comm_sev_deduction_l5_type='AMOUNT',
                comm_sev_deduction_l5_val=Decimal('500.00'),
                is_active=True
            )
            db.add(config)
            db.commit()
            db.refresh(config)
        
        category_id = config.category_id
        company_id = config.company_id or 1
        print(f"Using category_id: {category_id}, company_id: {company_id}")

        # 2. Create Community Service
        service = CommunityService(
            service_name="Test Seva Service",
            short_name=short_name,
            description="Testing E2E Seva",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            applicable_verticals=["Solar"],
            status="ACTIVE"
        )
        db.add(service)
        db.commit()
        db.refresh(service)
        created_entities["services"].append(service.id)
        print(f"Created CommunityService ID: {service.id}")

        # 3. Create Community Partner login account
        partner = OfficialPartner(
            company_id=company_id,
            partner_code=partner_code,
            partner_name="Test Community Organisation",
            phone="9876543210",
            category="VGK_TEAM",
            vgk_role="COMMUNITY",
            is_active=True,
            vgk_points_balance=Decimal('0')
        )
        db.add(partner)
        db.commit()
        db.refresh(partner)
        created_entities["partners"].append(partner.id)
        print(f"Created OfficialPartner ID: {partner.id} with vgk_role: {partner.vgk_role}")

        # 4. Create Community Registration linked to the partner
        reg = CommunityRegistration(
            community_service_id=service.id,
            primary_name="Test Community Organisation",
            primary_phone_1="9876543210",
            area="Kukatpally",
            pin_code="500072",
            district="Hyderabad",
            state="Telangana",
            status="APPROVED",
            user_id=partner.id
        )
        db.add(reg)
        db.commit()
        db.refresh(reg)
        created_entities["registrations"].append(reg.id)
        print(f"Created CommunityRegistration ID: {reg.id} linked to partner user_id: {reg.user_id}")

        # 5. Create upline members (L1, L2, L5) to receive and deduct commission
        l1_partner = OfficialPartner(
            company_id=company_id,
            partner_code=l1_code,
            partner_name="Test L1 Upline",
            phone=f"90000{rand_id}",
            category="VGK_TEAM",
            is_active=True,
            vgk_points_balance=Decimal('10000.00')
        )
        db.add(l1_partner)
        db.commit()
        db.refresh(l1_partner)
        created_entities["partners"].append(l1_partner.id)

        l2_partner = OfficialPartner(
            company_id=company_id,
            partner_code=l2_code,
            partner_name="Test L2 Upline",
            phone=f"90001{rand_id}",
            category="VGK_TEAM",
            is_active=True,
            vgk_points_balance=Decimal('10000.00')
        )
        db.add(l2_partner)
        db.commit()
        db.refresh(l2_partner)
        created_entities["partners"].append(l2_partner.id)
        
        l1_partner.parent_partner_id = l2_partner.id
        db.commit()

        l5_partner = OfficialPartner(
            company_id=company_id,
            partner_code=l5_code,
            partner_name="Test L5 Upline",
            phone=f"90002{rand_id}",
            category="VGK_TEAM",
            is_active=True,
            vgk_points_balance=Decimal('10000.00')
        )
        db.add(l5_partner)
        db.commit()
        db.refresh(l5_partner)
        created_entities["partners"].append(l5_partner.id)
        print("Created upline members: L1, L2, L5.")

        # 6. Create CRMLead linked to this community
        lead = CRMLead(
            company_id=company_id,
            name="Test Customer Lead",
            phone="8888888888",
            is_vgk_program=True,
            category_id=category_id,
            community_id=reg.id,
            primary_owner_type="partner",
            primary_owner_id=l1_partner.id,
            vgk_field_support_id=l5_partner.id,
            deal_value_total=Decimal('20000.00'),
            deal_value_received=Decimal('0.00'),
            deal_value_balance=Decimal('20000.00'),
            status="approved"
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)
        created_entities["leads"].append(lead.id)
        print(f"Created CRMLead ID: {lead.id} linked to community_id: {lead.community_id}")

        # 7. Verify no community commissions or deductions exist initially
        initial_comm = db.query(CommunityCommission).filter(CommunityCommission.lead_id == lead.id).all()
        assert len(initial_comm) == 0, "Initial community commissions should be zero"

        # 8. Simulate First Payment/Milestone Approval (transaction amount = 5000.0)
        lead.deal_value_received = Decimal('5000.00')
        lead.deal_value_balance = Decimal('15000.00')
        db.commit()

        success = calculate_vgk_commissions(db, lead_id=lead.id, transaction_id=111111, revenue_amount=5000.00)
        assert success, "Commission calculation failed"
        print("First payment commission calculated.")

        # Track commissions and income entries created so far
        comms = db.query(CommunityCommission).filter(CommunityCommission.lead_id == lead.id).all()
        for c in comms:
            created_entities["commissions"].append(c.id)
        
        income_ents = db.query(VGKTeamIncomeEntry).filter(VGKTeamIncomeEntry.source_lead_id == lead.id).all()
        for ie in income_ents:
            created_entities["income_entries"].append(ie.id)

        # Verify Community Seva Contribution Payout was immediately released
        assert len(comms) == 1, f"Expected 1 community commission entry, got {len(comms)}"
        assert comms[0].status == 'RELEASED', "Commission status should be RELEASED"
        expected_seva = config.comm_sev_deduction_l1_val + config.comm_sev_deduction_l2_val + config.comm_sev_deduction_l5_val
        assert comms[0].amount == expected_seva, f"Expected seva amount {expected_seva}, got {comms[0].amount}"
        print(f"Verified Community Seva Contribution released immediately: Amount = {comms[0].amount}")

        # Verify no negative deduction entries exist yet (since balance is still 15000.0 > 0)
        deductions = db.query(VGKTeamIncomeEntry).filter(
            VGKTeamIncomeEntry.source_lead_id == lead.id,
            VGKTeamIncomeEntry.commission_amount < 0
        ).all()
        assert len(deductions) == 0, f"Expected 0 deductions when balance > 0, got {len(deductions)}"
        print("Verified zero upline deductions applied prior to final payment.")

        # 9. Simulate Final Payment Completion (transaction amount = 15000.0, balance = 0.0)
        lead.deal_value_received = Decimal('20000.00')
        lead.deal_value_balance = Decimal('0.00')
        db.commit()

        success = calculate_vgk_commissions(db, lead_id=lead.id, transaction_id=222222, revenue_amount=15000.00)
        assert success, "Final payment commission calculation failed"
        print("Final payment commission calculated.")

        # Track new income entries
        income_ents = db.query(VGKTeamIncomeEntry).filter(VGKTeamIncomeEntry.source_lead_id == lead.id).all()
        for ie in income_ents:
            if ie.id not in created_entities["income_entries"]:
                created_entities["income_entries"].append(ie.id)

        # Verify upline member deductions applied
        deductions = db.query(VGKTeamIncomeEntry).filter(
            VGKTeamIncomeEntry.source_lead_id == lead.id,
            VGKTeamIncomeEntry.commission_amount < 0
        ).all()
        assert len(deductions) == 3, f"Expected 3 negative deduction entries, got {len(deductions)}"
        
        # Verify specific amounts
        l1_ded = [d for d in deductions if d.partner_id == l1_partner.id and d.level == 1]
        l2_ded = [d for d in deductions if d.partner_id == l2_partner.id and d.level == 2]
        l5_ded = [d for d in deductions if d.partner_id == l5_partner.id and d.level == 4]
        
        assert len(l1_ded) == 1 and l1_ded[0].commission_amount == -config.comm_sev_deduction_l1_val, "L1 deduction mismatch"
        assert len(l2_ded) == 1 and l2_ded[0].commission_amount == -config.comm_sev_deduction_l2_val, "L2 deduction mismatch"
        assert len(l5_ded) == 1 and l5_ded[0].commission_amount == -config.comm_sev_deduction_l5_val, "L5 deduction mismatch"
        print("Verified upline deductions (L1, L2, L4) applied correctly at final payment.")

        # 10. Call /my-earnings API controller programmatically to verify it returns the correct earnings and tagged leads
        res = get_community_member_earnings(db=db, partner=partner)
        assert res["success"] is True, "my-earnings endpoint failed"
        assert res["community_name"] == "Test Community Organisation", "Community name mismatch"
        assert res["total_seva_earned"] == float(expected_seva), f"Total seva earned mismatch: expected {expected_seva}, got {res['total_seva_earned']}"
        assert len(res["commissions"]) == 1, "Expected 1 commission entry in API response"
        assert res["commissions"][0]["amount"] == float(expected_seva), "Commission amount in API response mismatch"
        assert len(res["leads"]) == 1, "Expected 1 tagged lead in API response"
        assert res["leads"][0]["customer_name"] == "Test Customer Lead", "Lead customer name mismatch"
        print("Verified /my-earnings API endpoint returns correct data structure and content.")

        print("\n>>> ALL TESTS PASSED SUCCESSFULLY! <<<\n")

    except Exception as e:
        print(f"Error during E2E test execution: {e}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        print("Cleaning up created entities...")
        try:
            # Delete in dependency order
            if created_entities["income_entries"]:
                db.query(VGKTeamIncomeEntry).filter(VGKTeamIncomeEntry.id.in_(created_entities["income_entries"])).delete(synchronize_session=False)
            if created_entities["commissions"]:
                db.query(CommunityCommission).filter(CommunityCommission.id.in_(created_entities["commissions"])).delete(synchronize_session=False)
            if created_entities["leads"]:
                db.query(CRMLead).filter(CRMLead.id.in_(created_entities["leads"])).delete(synchronize_session=False)
            if created_entities["registrations"]:
                db.query(CommunityRegistration).filter(CommunityRegistration.id.in_(created_entities["registrations"])).delete(synchronize_session=False)
            if created_entities["partners"]:
                # Remove parent references first to avoid foreign key errors on self-references
                db.query(OfficialPartner).filter(OfficialPartner.id.in_(created_entities["partners"])).update({OfficialPartner.parent_partner_id: None}, synchronize_session=False)
                db.flush()
                db.query(OfficialPartner).filter(OfficialPartner.id.in_(created_entities["partners"])).delete(synchronize_session=False)
            if created_entities["services"]:
                db.query(CommunityService).filter(CommunityService.id.in_(created_entities["services"])).delete(synchronize_session=False)
            db.commit()
            print("Cleanup completed successfully.")
        except Exception as cleanup_err:
            print(f"Error during cleanup: {cleanup_err}")
            db.rollback()
        db.close()

if __name__ == "__main__":
    run_e2e_test()
