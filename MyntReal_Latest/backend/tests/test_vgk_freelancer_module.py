"""
Authoritative Test Suite: VGK4U Freelancer Segment Architecture & Business Rules
--------------------------------------------------------------------------------
Verifies all locked invariants:
 1. Freelancer Creation & Code Sequence (FL08180001, FL08180002...)
 2. Invariant: parent_partner_id IS NULL, partner_type == 'FREELANCER', 0 points
 3. Support ID Validation: Must be active Channel Partner, cannot be another Freelancer
 4. Member Search Endpoint: purpose='ground_source' includes FL, purpose='referrer' excludes FL
 5. Member Registry Endpoint: GET /api/v1/vgk/members excludes FL
 6. Tree View Endpoint: GET /api/v1/vgk/members/{id}/tree rejects FL with 400
 7. Upline Protection: Regular member cannot have a Freelancer as parent_partner_id
 8. Single Ground Source Attribution: crm_leads.associated_partner_id supports Freelancer
 9. Commission Engine Guard: calculate_vgk_commissions generates 0 commissions for FL leads
10. Waterfall Engine Guard: calculate_commission_structure generates 0 allocations for FL producer
11. Advance Pipeline Guard: check_and_create_advance returns eligible=False for FL leads
12. Automated Communication Gate: WITHOUT_COMMUNICATION suppresses WhatsApp automated triggers
13. Support ID Reassignment & Audit Trail: PlatformChangeScopeLog records reassignment
"""

import os
import sys
import unittest
from datetime import datetime
from decimal import Decimal

# Rule 1: No hardcoded absolute paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from app.models.staff import StaffEmployee
from app.models.staff_accounts import OfficialPartner, VGKTeamIncomeEntry, PlatformChangeScopeLog
from app.models.crm import CRMLead
from app.api.v1.endpoints.vgk_team import (
    _next_freelancer_code,
    create_freelancer,
    list_freelancers,
    get_freelancer_detail,
    update_freelancer,
    search_vgk_members,
    list_vgk_members,
    get_vgk_member_tree,
    create_vgk_member,
    FreelancerCreate,
    FreelancerUpdate,
    VGKMemberCreate
)
from app.services.vgk_commission import calculate_vgk_commissions
from app.services.vgk4u_waterfall_engine import VGK4UWaterfallEngine
from app.services.vgk_solar_advance import check_and_create_advance
from app.services.whatsapp_auto_service import send_auto_whatsapp, send_lead_welcome
from fastapi import HTTPException


class TestVGKFreelancerModule(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        cls.admin_staff = cls.db.query(StaffEmployee).filter(StaffEmployee.role_id.isnot(None)).first()
        if not cls.admin_staff:
            cls.admin_staff = cls.db.query(StaffEmployee).first()

        sample_lead = cls.db.query(CRMLead).first()
        cls.company_id = sample_lead.company_id if sample_lead else 4

        # Clean up any lingering test records
        cls.db.query(CRMLead).filter(CRMLead.phone.like('912345%')).delete(synchronize_session=False)
        cls.db.query(PlatformChangeScopeLog).filter(PlatformChangeScopeLog.target_module == 'VGK_FREELANCER').delete(synchronize_session=False)
        cls.db.query(OfficialPartner).filter(OfficialPartner.phone.like('912345%')).delete(synchronize_session=False)
        cls.db.commit()

        # Find or create a valid active Channel Partner to serve as VGK Support ID
        cls.support_partner = cls.db.query(OfficialPartner).filter(
            OfficialPartner.category == 'VGK_TEAM',
            OfficialPartner.partner_type != 'FREELANCER',
            OfficialPartner.is_active == True
        ).first()

        if not cls.support_partner:
            cls.support_partner = OfficialPartner(
                partner_code='VGK99999',
                partner_name='Support Partner Test CP',
                phone='9888877771',
                category='VGK_TEAM',
                partner_type='CHANNEL_PARTNER',
                designation_tier='CHANNEL PARTNER',
                is_active=True
            )
            cls.db.add(cls.support_partner)
            cls.db.commit()
            cls.db.refresh(cls.support_partner)

        cls.support_partner_2 = cls.db.query(OfficialPartner).filter(
            OfficialPartner.category == 'VGK_TEAM',
            OfficialPartner.partner_type != 'FREELANCER',
            OfficialPartner.is_active == True,
            OfficialPartner.id != cls.support_partner.id
        ).first()

        if not cls.support_partner_2:
            cls.support_partner_2 = OfficialPartner(
                partner_code='VGK99998',
                partner_name='Second Support CP',
                phone='9888877772',
                category='VGK_TEAM',
                partner_type='CHANNEL_PARTNER',
                designation_tier='CHANNEL PARTNER',
                is_active=True
            )
            cls.db.add(cls.support_partner_2)
            cls.db.commit()
            cls.db.refresh(cls.support_partner_2)

        cls.created_freelancer_ids = []
        cls.created_lead_ids = []

    @classmethod
    def tearDownClass(cls):
        # Clean up created leads and freelancers safely
        if cls.created_lead_ids:
            cls.db.query(CRMLead).filter(CRMLead.id.in_(cls.created_lead_ids)).delete(synchronize_session=False)
            cls.db.commit()

        if cls.created_freelancer_ids:
            cls.db.query(PlatformChangeScopeLog).filter(
                PlatformChangeScopeLog.target_module == "VGK_FREELANCER"
            ).delete(synchronize_session=False)
            cls.db.query(OfficialPartner).filter(
                OfficialPartner.id.in_(cls.created_freelancer_ids)
            ).delete(synchronize_session=False)
            cls.db.commit()

        cls.db.close()

    def test_01_freelancer_creation_and_code_generation(self):
        """Rule: Code must start with FL0818 and have 4-digit zero-padded sequence."""
        code1 = _next_freelancer_code(self.db)
        self.assertTrue(code1.startswith("FL0818"))
        num1 = int(code1[6:])
        self.assertGreaterEqual(num1, 1)

        payload = FreelancerCreate(
            partner_name="Test Freelancer Alpha",
            phone="9123450001",
            alternate_phone="9123450099",
            vgk_support_id=self.support_partner.id,
            freelancer_classification="WITH_COMMUNICATION",
            email="fl_alpha@test.com",
            area="Banjara Hills",
            city="Hyderabad",
            district="Hyderabad",
            state="Telangana",
            pincode="500034",
            address="Plot 101, Road No 12"
        )
        res = create_freelancer(payload=payload, current_user=self.admin_staff, db=self.db)
        self.assertTrue(res["success"])
        fl = res["data"]
        self.created_freelancer_ids.append(fl["id"])

        self.assertEqual(fl["partner_code"], code1)
        self.assertEqual(fl["partner_type"], "FREELANCER")
        self.assertEqual(fl["category"], "VGK_TEAM")
        self.assertIsNone(fl["parent_partner_id"])
        self.assertEqual(fl["vgk_support_id"], self.support_partner.id)
        self.assertEqual(fl["freelancer_classification"], "WITH_COMMUNICATION")
        self.assertEqual(fl["alternate_phone"], "9123450099")
        self.assertEqual(fl["area"], "Banjara Hills")
        self.assertEqual(fl["city"], "Hyderabad")
        self.assertEqual(fl["district"], "Hyderabad")
        self.assertEqual(fl["state"], "Telangana")
        self.assertEqual(fl["pincode"], "500034")

        # Invariant: points must be strictly 0
        db_fl = self.db.query(OfficialPartner).filter(OfficialPartner.id == fl["id"]).first()
        self.assertEqual(int(db_fl.vgk_points_balance or 0), 0)
        self.assertEqual(db_fl.alternate_phone, "9123450099")
        self.assertEqual(db_fl.area, "Banjara Hills")
        self.assertEqual(db_fl.district, "Hyderabad")
        self.assertEqual(db_fl.pincode, "500034")

    def test_02_sequential_code_increment(self):
        """Rule: Consecutive creations generate incremented sequence (e.g. FL08180002)."""
        payload = FreelancerCreate(
            partner_name="Test Freelancer Beta",
            phone="9123450002",
            vgk_support_id=self.support_partner.id,
            freelancer_classification="WITHOUT_COMMUNICATION"
        )
        res = create_freelancer(payload=payload, current_user=self.admin_staff, db=self.db)
        self.assertTrue(res["success"])
        fl = res["data"]
        self.created_freelancer_ids.append(fl["id"])

        prev_id = self.created_freelancer_ids[0]
        prev_fl = self.db.query(OfficialPartner).filter(OfficialPartner.id == prev_id).first()
        prev_num = int(prev_fl.partner_code[6:])
        cur_num = int(fl["partner_code"][6:])
        self.assertEqual(cur_num, prev_num + 1)
        self.assertEqual(fl["freelancer_classification"], "WITHOUT_COMMUNICATION")

    def test_03_support_id_validation_rules(self):
        """Rule: Reject non-existent support ID, and reject another Freelancer as support ID."""
        # Non-existent support ID
        bad_payload = FreelancerCreate(
            partner_name="Invalid Support FL",
            phone="9123450003",
            vgk_support_id=999999999,
            freelancer_classification="WITH_COMMUNICATION"
        )
        with self.assertRaises(HTTPException) as ctx:
            create_freelancer(payload=bad_payload, current_user=self.admin_staff, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("not found", ctx.exception.detail.lower())

        # Another Freelancer as support ID
        fl_as_support = FreelancerCreate(
            partner_name="FL Support Attempt",
            phone="9123450004",
            vgk_support_id=self.created_freelancer_ids[0],
            freelancer_classification="WITH_COMMUNICATION"
        )
        with self.assertRaises(HTTPException) as ctx:
            create_freelancer(payload=fl_as_support, current_user=self.admin_staff, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("cannot be assigned as a support id", ctx.exception.detail.lower())

    def test_04_member_search_purpose_filtering(self):
        """Rule: purpose='ground_source' includes FL; purpose='referrer'/sponsor/freelancer_support excludes FL."""
        fl_id = self.created_freelancer_ids[0]
        fl = self.db.query(OfficialPartner).filter(OfficialPartner.id == fl_id).first()

        # Search for ground_source: must find the freelancer
        res_gs = search_vgk_members(q=fl.partner_code, purpose="ground_source", db=self.db)
        found_ids_gs = [p["id"] for p in res_gs["data"]]
        self.assertIn(fl.id, found_ids_gs)

        # Search for referrer/sponsor: must EXCLUDE the freelancer
        res_ref = search_vgk_members(q=fl.partner_code, purpose="referrer", db=self.db)
        found_ids_ref = [p["id"] for p in res_ref["data"]]
        self.assertNotIn(fl.id, found_ids_ref)

        # Search for freelancer_support: must find Channel Partner, but EXCLUDE Freelancers and staff/influencers
        res_supp = search_vgk_members(q=self.support_partner.partner_code, purpose="freelancer_support", db=self.db)
        found_ids_supp = [p["id"] for p in res_supp["data"]]
        self.assertIn(self.support_partner.id, found_ids_supp)

        res_supp_fl = search_vgk_members(q=fl.partner_code, purpose="freelancer_support", db=self.db)
        found_ids_supp_fl = [p["id"] for p in res_supp_fl["data"]]
        self.assertNotIn(fl.id, found_ids_supp_fl)

    def test_05_member_registry_excludes_freelancers(self):
        """Rule: GET /api/v1/vgk/members must strictly exclude Freelancers."""
        fl_id = self.created_freelancer_ids[0]
        fl = self.db.query(OfficialPartner).filter(OfficialPartner.id == fl_id).first()

        res = list_vgk_members(search=fl.partner_code, db=self.db, current_user=self.admin_staff)
        member_ids = [m["id"] for m in res["data"]]
        self.assertNotIn(fl_id, member_ids)

    def test_06_tree_endpoint_blocks_freelancers(self):
        """Rule: Freelancers have no tree/downline hierarchy; tree call must return 400."""
        fl_id = self.created_freelancer_ids[0]
        with self.assertRaises(HTTPException) as ctx:
            get_vgk_member_tree(member_id=fl_id, current_user=self.admin_staff, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Freelancers do not participate", ctx.exception.detail)

    def test_07_upline_creation_guard(self):
        """Rule: Regular member creation must reject a Freelancer as parent_partner_id."""
        fl_id = self.created_freelancer_ids[0]
        payload = VGKMemberCreate(
            phone="9123450099",
            first_name="Downline",
            parent_partner_id=fl_id,
            password="testpassword123"
        )
        with self.assertRaises(HTTPException) as ctx:
            create_vgk_member(payload=payload, current_user=self.admin_staff, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("cannot be an upline", ctx.exception.detail)

    def test_08_ground_source_crm_lead_attribution(self):
        """Rule: CRM leads can be originated by a Freelancer (associated_partner_id)."""
        fl_id = self.created_freelancer_ids[0]
        lead = CRMLead(
            name="Solar Rooftop Prospect",
            company_id=self.company_id,
            phone="9123459999",
            associated_partner_id=fl_id,
            status="new"
        )
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        self.created_lead_ids.append(lead.id)

        self.assertEqual(lead.associated_partner_id, fl_id)

    def test_09_vgk_commission_engine_guard(self):
        """Rule: calculate_vgk_commissions creates 0 entries if Ground Source is a Freelancer."""
        fl_id = self.created_freelancer_ids[0]
        lead = CRMLead(
            name="Deal for Commission Test",
            company_id=self.company_id,
            phone="9123458888",
            associated_partner_id=fl_id,
            is_vgk_program=True,
            status="won"
        )
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        self.created_lead_ids.append(lead.id)

        # Count income entries before
        entries_before = self.db.query(VGKTeamIncomeEntry).filter(
            VGKTeamIncomeEntry.source_lead_id == lead.id
        ).count()

        success = calculate_vgk_commissions(
            db=self.db,
            lead_id=lead.id,
            transaction_id=1,
            revenue_amount=200000.0
        )
        self.assertTrue(success)

        entries_after = self.db.query(VGKTeamIncomeEntry).filter(
            VGKTeamIncomeEntry.source_lead_id == lead.id
        ).count()
        self.assertEqual(entries_after - entries_before, 0)

    def test_10_vgk4u_waterfall_engine_guard(self):
        """Rule: calculate_commission_structure returns 0 allocations if producer is a Freelancer."""
        fl_id = self.created_freelancer_ids[0]
        res = VGK4UWaterfallEngine.calculate_commission_structure(
            db=self.db,
            producer_partner_id=fl_id,
            deal_value=Decimal('50000.0'),
            category_slug="solar"
        )
        self.assertTrue(res.get("skipped"))
        self.assertEqual(len(res.get("allocations", [])), 0)

    def test_11_solar_advance_pipeline_guard(self):
        """Rule: check_and_create_advance returns eligible=False for Freelancer Ground Source."""
        fl_id = self.created_freelancer_ids[0]
        lead = CRMLead(
            name="Advance Test Lead",
            company_id=self.company_id,
            phone="9123457777",
            associated_partner_id=fl_id,
            status="new"
        )
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        self.created_lead_ids.append(lead.id)

        adv_res = check_and_create_advance(
            db=self.db,
            lead_id=lead.id
        )
        self.assertFalse(adv_res.get("eligible", True))
        self.assertIn("Freelancer", adv_res.get("reason", ""))

    def test_12_communication_gate_enforcement(self):
        """Rule: WITHOUT_COMMUNICATION suppresses automated WhatsApp messages."""
        fl_without = self.db.query(OfficialPartner).filter(
            OfficialPartner.id == self.created_freelancer_ids[1]
        ).first()
        self.assertEqual(fl_without.freelancer_classification, "WITHOUT_COMMUNICATION")

        lead = CRMLead(
            name="Quiet Customer Lead",
            company_id=self.company_id,
            phone="9123456666",
            associated_partner_id=fl_without.id,
            status="new"
        )
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        self.created_lead_ids.append(lead.id)

        # Trigger send_auto_whatsapp: must be suppressed
        wa_res = send_auto_whatsapp(
            db=self.db,
            event_key="lead_welcome",
            phone=lead.phone,
            context={"customer_name": lead.name},
            lead_id=lead.id
        )
        self.assertFalse(wa_res.get("sent", True))
        self.assertIn("suppressed_by_freelancer_without_communication", wa_res.get("reason", ""))

        # Trigger send_lead_welcome: must also be suppressed
        welcome_res = send_lead_welcome(
            db=self.db,
            phone=lead.phone,
            lead_name=lead.name,
            lead_id=lead.id
        )
        self.assertFalse(welcome_res.get("success", True))
        self.assertIn("suppressed_by_freelancer_setting", welcome_res.get("reason", ""))

    def test_13_support_id_reassignment_and_audit_trail(self):
        """Rule: Reassigning vgk_support_id logs an audit record in PlatformChangeScopeLog."""
        fl_id = self.created_freelancer_ids[0]
        fl_before = self.db.query(OfficialPartner).filter(OfficialPartner.id == fl_id).first()
        old_support_id = fl_before.vgk_support_id

        new_support_id = self.support_partner_2.id
        self.assertNotEqual(old_support_id, new_support_id)

        update_payload = FreelancerUpdate(
            vgk_support_id=new_support_id,
            notes="Reassigned to second channel partner for mentoring"
        )
        res = update_freelancer(
            freelancer_id=fl_id,
            payload=update_payload,
            current_user=self.admin_staff,
            db=self.db
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["data"]["vgk_support_id"], new_support_id)

        # Verify audit log exists
        audit_log = self.db.query(PlatformChangeScopeLog).filter(
            PlatformChangeScopeLog.target_module == "VGK_FREELANCER",
            PlatformChangeScopeLog.change_title == f"Updated Freelancer {fl_before.partner_code}"
        ).order_by(PlatformChangeScopeLog.id.desc()).first()

        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.old_value.get("support_id"), old_support_id)
        self.assertEqual(audit_log.new_value.get("support_id"), new_support_id)

    def test_14_alternate_contact_and_pincode_address_fields(self):
        """Rule: Alternate contact, pincode, area, district, state update and detail retrieval."""
        from app.api.v1.endpoints.vgk_team import get_freelancer_detail, list_freelancers

        fl_id = self.created_freelancer_ids[0]
        update_payload = FreelancerUpdate(
            alternate_phone="9876543210",
            pincode="500081",
            area="HITEC City",
            city="Hyderabad",
            district="Ranga Reddy",
            state="Telangana",
            address="Building 4, Mindspace"
        )
        res = update_freelancer(
            freelancer_id=fl_id,
            payload=update_payload,
            current_user=self.admin_staff,
            db=self.db
        )
        self.assertTrue(res["success"])
        d = res["data"]
        self.assertEqual(d["alternate_phone"], "9876543210")
        self.assertEqual(d["pincode"], "500081")
        self.assertEqual(d["area"], "HITEC City")
        self.assertEqual(d["district"], "Ranga Reddy")
        self.assertEqual(d["state"], "Telangana")
        self.assertEqual(d["address"], "Building 4, Mindspace")

        # Verify get_freelancer_detail returns the updated fields
        detail_res = get_freelancer_detail(freelancer_id=fl_id, current_user=self.admin_staff, db=self.db)
        self.assertTrue(detail_res["success"])
        detail_data = detail_res["data"]
        self.assertEqual(detail_data["alternate_phone"], "9876543210")
        self.assertEqual(detail_data["pincode"], "500081")
        self.assertEqual(detail_data["area"], "HITEC City")
        self.assertEqual(detail_data["district"], "Ranga Reddy")
        self.assertEqual(detail_data["state"], "Telangana")
        self.assertEqual(detail_data["address"], "Building 4, Mindspace")

        # Verify list_freelancers includes the fields
        list_res = list_freelancers(page=1, page_size=10, current_user=self.admin_staff, db=self.db)
        self.assertTrue(list_res["success"])
        matched = [item for item in list_res["items"] if item["id"] == fl_id]
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["alternate_phone"], "9876543210")
        self.assertEqual(matched[0]["pincode"], "500081")
        self.assertEqual(matched[0]["area"], "HITEC City")
        self.assertEqual(matched[0]["district"], "Ranga Reddy")


if __name__ == '__main__':
    unittest.main()

