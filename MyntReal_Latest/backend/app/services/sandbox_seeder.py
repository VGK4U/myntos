import logging
from decimal import Decimal
import datetime
from sqlalchemy.orm import Session
from app.models.community_service import CommunityService, CommunityRegistration
from app.models.staff_accounts import OfficialPartner, VGKTeamCommissionConfig
from app.models.crm import CRMLead
from app.models.base import get_indian_time

logger = logging.getLogger(__name__)

def seed_sandbox_data(db: Session):
    # 1. Seed Referrers: TEST_REF_01 and TEST_REF_02
    ref1 = db.query(OfficialPartner).filter_by(partner_code="TEST_REF_01").first()
    if not ref1:
        ref1 = OfficialPartner(
            company_id=1,
            partner_code="TEST_REF_01",
            partner_name="Test Referrer 1",
            phone="9999990003",
            email="ref1@test.com",
            category="VGK_TEAM",
            is_active=True,
            vgk_role="VGK_ASSOCIATE",
            vgk_points_balance=Decimal("10000"),
            is_paid_activation=True,
            created_at=get_indian_time().replace(tzinfo=None),
            updated_at=get_indian_time().replace(tzinfo=None)
        )
        db.add(ref1)
        db.flush()
        logger.info("Seeded TEST_REF_01 partner")
    else:
        ref1.is_active = True
        ref1.is_paid_activation = True
        db.flush()
    
    ref2 = db.query(OfficialPartner).filter_by(partner_code="TEST_REF_02").first()
    if not ref2:
        ref2 = OfficialPartner(
            company_id=1,
            partner_code="TEST_REF_02",
            partner_name="Test Referrer 2",
            phone="9999990004",
            email="ref2@test.com",
            category="VGK_TEAM",
            is_active=True,
            vgk_role="VGK_ASSOCIATE",
            vgk_points_balance=Decimal("10000"),
            is_paid_activation=True,
            parent_partner_id=None,
            created_at=get_indian_time().replace(tzinfo=None),
            updated_at=get_indian_time().replace(tzinfo=None)
        )
        db.add(ref2)
        db.flush()
        logger.info("Seeded TEST_REF_02 partner")
    else:
        ref2.is_active = True
        ref2.is_paid_activation = True
        db.flush()

    # Link ref1 to upline ref2 for cascading upline commission/deductions
    ref1.parent_partner_id = ref2.id
    db.flush()

    # 2. Seed Community Service: TEST_Ganesh_Seva_2026 (Short Name: TEST_Ganesh_Seva)
    html_desc = """<div class="seva-articulator-content">
  <div style="background: linear-gradient(135deg, rgba(217,119,6,0.2) 0%, rgba(185,28,28,0.2) 100%); border: 1px solid rgba(245,158,11,0.4); border-radius: 12px; padding: 20px; margin-bottom: 20px;">
    <h3 style="color: #fbbf24; font-size: 18px; font-weight: 800; margin-bottom: 8px;">
      <i class="fas fa-om me-2"></i>VGK4U Ganesh Green Seva Campaign 2026
    </h3>
    <p style="color: #d1d5db; font-size: 14px; margin: 0;">
      Go Solar. Support Your Ganesh Mandapam. For every eligible solar customer generated through this campaign, <strong>₹5,000</strong> will be contributed directly to your registered Ganesh Mandapam!
    </p>
  </div>

  <div style="margin-bottom: 20px;">
    <h4 style="color: #38bdf8; font-size: 15px; font-weight: 700; border-bottom: 1px solid #374151; padding-bottom: 6px; margin-bottom: 12px;">
      <i class="fas fa-star me-2" style="color: #f59e0b;"></i>Core Campaign Highlights
    </h4>
    <ul style="color: #9ca3af; font-size: 13.5px; padding-left: 20px;">
      <li style="margin-bottom: 8px;"><strong style="color: #f3f4f6;">₹5,000 Contribution:</strong> Directly awarded to the Mandapam upon qualifying milestone completion.</li>
      <li style="margin-bottom: 8px;"><strong style="color: #f3f4f6;">Hyperlocal Awareness:</strong> Connecting solar adoption directly with festival community gatherings.</li>
      <li style="margin-bottom: 8px;"><strong style="color: #f3f4f6;">VGK Ambassador Network:</strong> Managed locally through verified VGK channel partners and Mandapam committees.</li>
    </ul>
  </div>

  <div style="background: rgba(31, 41, 55, 0.6); border: 1px solid #374151; border-radius: 10px; padding: 16px;">
    <h4 style="color: #34d399; font-size: 14px; font-weight: 700; margin-bottom: 8px;">
      <i class="fas fa-check-circle me-2"></i>Eligibility & Rules
    </h4>
    <p style="color: #9ca3af; font-size: 13px; margin: 0;">
      Every lead is recorded and mapped to a single Mandapam and VGK member. Contributions trigger automatically once the first commercial payment milestone is verified by the company.
    </p>
  </div>
</div>"""

    service = db.query(CommunityService).filter_by(short_name="TEST_Ganesh_Seva").first()
    seeded_banners = [
        "community_banners/media__1785474896712.png",
        "community_banners/media__1785475046387.png",
        "community_banners/media__1785475821762.png"
    ]
    settings_dict = {
        "custom_title": "VGK4U Ganesh Green Seva 2026",
        "custom_tagline": "Go Solar. Support Your Ganesh Mandapam.",
        "contribution_callout": "₹5,000 Contribution per Eligible Successful Solar Installation",
        "campaign_rules": "Every customer must be uniquely registered in the CRM and mapped to only one VGK member and one Ganesh Mandapam. Existing company leads, duplicate registrations, cancelled orders and ineligible projects should not qualify.",
        "cashflow_steps": [
            "Mandapam Register",
            "Lead Submission",
            "Site Survey",
            "Seva Payout"
        ],
        "benefits_customers": "Gets access to premium rooftop solar solutions and applicable subsidy benefits.",
        "benefits_community": "Receives a ₹5,000 community contribution for every qualifying successful solar customer.",
        "benefits_partners": "Creates solar business opportunities while strengthening their local network under VGK incentive structure."
    }
    if not service:
        service = CommunityService(
            service_name="TEST_Ganesh_Seva_2026",
            short_name="TEST_Ganesh_Seva",
            description=html_desc,
            start_date=get_indian_time().date() - datetime.timedelta(days=1),
            end_date=get_indian_time().date() + datetime.timedelta(days=30),
            applicable_verticals=["Solar"],
            status="ACTIVE",
            banner_images=seeded_banners,
            settings=settings_dict,
            created_at=get_indian_time().replace(tzinfo=None),
            updated_at=get_indian_time().replace(tzinfo=None)
        )
        db.add(service)
        db.flush()
        logger.info("Seeded TEST_Ganesh_Seva community service")
    else:
        service.service_name = "TEST_Ganesh_Seva_2026"
        service.description = html_desc
        service.banner_images = seeded_banners
        service.settings = settings_dict
        service.status = "ACTIVE"
        db.flush()

    # 3. Seed TEST_COMM_01 OfficialPartner (representing approved community)
    partner_comm = db.query(OfficialPartner).filter_by(partner_code="TEST_COMM_01").first()
    if not partner_comm:
        from app.core.security import SecurityManager
        raw_password = "TestPassword123!"
        password_hash = SecurityManager.get_password_hash(raw_password)
        partner_comm = OfficialPartner(
            company_id=1,
            partner_code="TEST_COMM_01",
            partner_name="Test Seva Mandapam 2026",
            phone="9999990001",
            email="comm01@test.com",
            category="VGK_TEAM",
            is_active=True,
            vgk_role="COMMUNITY",
            vgk_points_balance=Decimal("0"),
            password_hash=password_hash,
            created_at=get_indian_time().replace(tzinfo=None),
            updated_at=get_indian_time().replace(tzinfo=None)
        )
        db.add(partner_comm)
        db.flush()
        logger.info("Seeded TEST_COMM_01 partner")
    else:
        partner_comm.is_active = True
        partner_comm.vgk_role = "COMMUNITY"
        db.flush()

    # 4. Seed Community Registration: Test Seva Mandapam 2026
    reg = db.query(CommunityRegistration).filter_by(primary_name="Test Seva Mandapam 2026").first()
    if not reg:
        reg = CommunityRegistration(
            community_service_id=service.id,
            primary_name="Test Seva Mandapam 2026",
            primary_phone_1="9999990001",
            area="Test Sandbox Area",
            pin_code="500001",
            district="Test District",
            state="Test State",
            ref1_member_id=ref1.id,
            ref2_member_id=ref2.id,
            status="APPROVED",
            user_id=partner_comm.id,
            created_at=get_indian_time().replace(tzinfo=None),
            updated_at=get_indian_time().replace(tzinfo=None)
        )
        db.add(reg)
        db.flush()
        logger.info("Seeded community registration for Test Seva Mandapam 2026")
    else:
        reg.community_service_id = service.id
        reg.ref1_member_id = ref1.id
        reg.ref2_member_id = ref2.id
        reg.user_id = partner_comm.id
        reg.status = "APPROVED"
        db.flush()

    # 5. Seed Commission Config (to ensure valid deductions configured)
    cfg = db.query(VGKTeamCommissionConfig).filter_by(category_id=6, is_active=True).first()
    if not cfg:
        cfg = VGKTeamCommissionConfig(
            company_id=1,
            category_id=6,
            level1_pct=5.0,
            level2_pct=3.0,
            level3_pct=1.0,
            level4_pct=1.0,
            is_active=True,
            is_paid_member=True,
            comm_sev_deduction_l1_val=1000.0,
            comm_sev_deduction_l2_val=500.0,
            comm_sev_deduction_l5_val=500.0,
            created_at=get_indian_time().replace(tzinfo=None),
            updated_at=get_indian_time().replace(tzinfo=None)
        )
        db.add(cfg)
        db.flush()

    # 6. Seed Lead: John Doe - Test Lead (TEST_LEAD_01)
    lead = db.query(CRMLead).filter_by(phone="TEST_LEAD_01").first()
    if not lead:
        lead = db.query(CRMLead).filter_by(name="John Doe - Test Lead").first()
        
    if not lead:
        lead = CRMLead(
            company_id=1,
            name="John Doe - Test Lead",
            phone="TEST_LEAD_01",
            category_id=6, # Solar
            status="new",
            solar_pipeline_status="documents_pending",
            community_id=reg.id,
            is_vgk_program=True,
            associated_partner_id=ref1.id,
            vgk_field_support_id=ref1.id,  # L5 support partner
            deal_value_total=100000.0,
            deal_value_received=0.0,
            deal_value_balance=100000.0,
            created_at=get_indian_time().replace(tzinfo=None),
            updated_at=get_indian_time().replace(tzinfo=None)
        )
        db.add(lead)
        db.flush()
        logger.info("Seeded TEST_LEAD_01 lead")
    else:
        lead.community_id = reg.id
        lead.is_vgk_program = True
        lead.associated_partner_id = ref1.id
        lead.vgk_field_support_id = ref1.id
        lead.deal_value_total = 100000.0
        db.flush()

    db.commit()
    return {
        "success": True,
        "message": "Sandbox test data seeded successfully",
        "data": {
            "service_id": service.id,
            "registration_id": reg.id,
            "ref1_partner_id": ref1.id,
            "ref2_partner_id": ref2.id,
            "community_partner_id": partner_comm.id,
            "lead_id": lead.id
        }
    }
