from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
import json

from app.core.database import get_db
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.models.staff import StaffEmployee
from app.models.staff_accounts import OfficialPartner, VGKTeamIncomeEntry, VGKTeamCommissionConfig
from app.models.crm import CRMLead
from app.models.community_service import CommunityService, CommunityRegistration, CommunityCommission
from app.services.universal_upload_service import UniversalUploadService
from app.models.base import get_indian_time
from app.api.v1.endpoints.vgk_auth import get_current_vgk_member
from app.core.timezone import normalize_date_input, get_indian_today


router = APIRouter()


# ──────────────────────────────────────────────────────────────────────
# 1. PUBLIC ENDPOINTS (In-Memory 60s Cached to Protect RDS Connections)
# ──────────────────────────────────────────────────────────────────────

_COMMUNITY_HEADERS_CACHE = (0.0, None)
_COMMUNITY_POPUP_CACHE = (0.0, None)
_COMMUNITY_CACHE_TTL = 60.0  # 60 seconds

def invalidate_community_services_cache():
    """Invalidate community services in-memory cache on admin mutation"""
    global _COMMUNITY_HEADERS_CACHE, _COMMUNITY_POPUP_CACHE
    _COMMUNITY_HEADERS_CACHE = (0.0, None)
    _COMMUNITY_POPUP_CACHE = (0.0, None)

@router.get("/public/active-headers")
def get_active_headers(db: Session = Depends(get_db)):
    """
    Query currently Active community services within validity range and count approved projects.
    Cached in-memory for 60s to prevent RDS connection starvation on public homepage.
    """
    global _COMMUNITY_HEADERS_CACHE
    import time
    now = time.time()
    if _COMMUNITY_HEADERS_CACHE[1] is not None and (now - _COMMUNITY_HEADERS_CACHE[0]) < _COMMUNITY_CACHE_TTL:
        return _COMMUNITY_HEADERS_CACHE[1]

    today = get_indian_time().date()
    active_services = db.query(CommunityService).filter(
        or_(CommunityService.status == 'ACTIVE', CommunityService.status == 'active'),
        or_(CommunityService.start_date.is_(None), CommunityService.start_date <= today),
        or_(CommunityService.end_date.is_(None), CommunityService.end_date >= today)
    ).all()

    if not active_services:
        active_services = db.query(CommunityService).filter(
            or_(CommunityService.status == 'ACTIVE', CommunityService.status == 'active')
        ).all()
    
    total_approved = db.query(CommunityRegistration).filter(
        CommunityRegistration.status == 'APPROVED'
    ).count()
    
    display_label = f"{max(18, total_approved)}+ Projects Registered"
    
    service_list = [
        {
            "id": s.id,
            "service_name": s.service_name,
            "short_name": s.short_name,
            "description": s.description or "",
            "banner_image": (s.banner_images[0] if (isinstance(s.banner_images, list) and len(s.banner_images) > 0) else None) if s.banner_images else None,
            "banner_images": s.banner_images or []
        } for s in active_services
    ]
    
    result = {
        "success": True,
        "status": "success",
        "services": service_list,
        "active_services": service_list,
        "total_approved_registrations": total_approved,
        "total_registered_projects": total_approved,
        "display_registered_label": display_label
    }
    _COMMUNITY_HEADERS_CACHE = (now, result)
    return result

@router.get("/public/homepage-popup")
def get_active_homepage_popup(db: Session = Depends(get_db)):
    """
    Get the active homepage popup banner configuration.
    Cached in-memory for 60s to prevent RDS connection starvation on public homepage.
    """
    global _COMMUNITY_POPUP_CACHE
    import time
    now = time.time()
    if _COMMUNITY_POPUP_CACHE[1] is not None and (now - _COMMUNITY_POPUP_CACHE[0]) < _COMMUNITY_CACHE_TTL:
        return _COMMUNITY_POPUP_CACHE[1]

    today = get_indian_time().date()
    # Query all active services
    active_services = db.query(CommunityService).filter(
        CommunityService.status == 'ACTIVE'
    ).all()
    
    for s in active_services:
        settings_dict = s.settings or {}
        show_popup = settings_dict.get('show_homepage_popup')
        popup_image = settings_dict.get('homepage_popup_image')
        till_date_str = settings_dict.get('homepage_popup_till_date')
        
        if show_popup in (True, 'yes', 'true') and popup_image and till_date_str:
            try:
                till_date = datetime.strptime(till_date_str, "%Y-%m-%d").date()
                if today <= till_date:
                    result = {
                        "success": True,
                        "has_popup": True,
                        "image_url": popup_image,
                        "short_name": s.short_name,
                        "service_name": s.service_name,
                        "till_date": till_date_str
                    }
                    _COMMUNITY_POPUP_CACHE = (now, result)
                    return result
            except Exception:
                continue
                
    result = {
        "success": True,
        "has_popup": False
    }
    _COMMUNITY_POPUP_CACHE = (now, result)
    return result

@router.get("/public/services/{short_name}")
def get_public_service_details(short_name: str, db: Session = Depends(get_db)):
    """
    Get dynamic public landing page details by short_name.
    """
    target = short_name.strip()
    service = db.query(CommunityService).filter(
        CommunityService.short_name.ilike(target),
        CommunityService.status == 'ACTIVE'
    ).first()
    if not service and target.lower() in ('camgan', 'guc', 'ganesh', 'ganesh-utsav', 'comgan'):
        service = db.query(CommunityService).filter(
            or_(
                CommunityService.short_name.ilike('camgan'),
                CommunityService.short_name.ilike('guc'),
                CommunityService.short_name.ilike('ganesh%'),
                CommunityService.service_name.ilike('%ganesh%')
            ),
            CommunityService.status == 'ACTIVE'
        ).first()
    if not service:
        if target.lower() in ('camgan', 'guc', 'ganesh', 'ganesh-utsav'):
            from datetime import timedelta
            service = CommunityService(
                service_name="విశాఖపట్నం జిల్లా గణేష్ ఉత్సవ సమితి",
                short_name="camgan",
                description="సామూహిక గణేష్ ఉత్సవాలు జరుపుకొనుటకు నమోదు పత్రం (Application Form for Organizing Collective Ganesh Utsav)",
                start_date=get_indian_today(),
                end_date=get_indian_today() + timedelta(days=90),
                status="ACTIVE",
                applicable_verticals=["Solar", "Real Estate"],
                settings={"show_homepage_popup": False}
            )
            db.add(service)
            db.commit()
            db.refresh(service)
        else:
            raise HTTPException(status_code=404, detail="Community Service not found or inactive")
    return {
        "success": True,
        "data": service.to_dict()
    }

@router.get("/public/registrations/{reg_id}")
def get_registration_public(reg_id: int, db: Session = Depends(get_db)):
    """
    Public / Staff read endpoint for a single community registration by ID.
    Enables VIEW / EDIT across Web, /mobile, Android, iOS.
    """
    from fastapi.encoders import jsonable_encoder
    reg = db.query(CommunityRegistration).filter(CommunityRegistration.id == reg_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    data = reg.to_dict()
    data['kyc_documents'] = reg.kyc_uploads or []
    data['service_name'] = reg.service.service_name if reg.service else 'Ganesh Utsav Committee'
    data['service_short_name'] = reg.service.short_name if reg.service else 'guc'
    return {"success": True, "data": jsonable_encoder(data)}


@router.post("/public/register")
async def register_community(
    community_service_id: Optional[int] = Form(None),
    association_name: Optional[str] = Form(None),
    primary_name: Optional[str] = Form(None),
    primary_phone_1: Optional[str] = Form(None),
    primary_phone_2: Optional[str] = Form(None),
    secondary_name: Optional[str] = Form(None),
    secondary_phone_1: Optional[str] = Form(None),
    secondary_phone_2: Optional[str] = Form(None),
    area: Optional[str] = Form(None),
    pin_code: Optional[str] = Form(None),
    district: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    google_location: Optional[str] = Form(None),
    ref1_member_id: Optional[int] = Form(None),
    ref2_member_id: Optional[int] = Form(None),
    referral_type: Optional[str] = Form(None),
    referral_code: Optional[str] = Form(None),
    aadhar_first_front: Optional[UploadFile] = File(None),
    aadhar_first_back: Optional[UploadFile] = File(None),
    aadhar_second_front: Optional[UploadFile] = File(None),
    aadhar_second_back: Optional[UploadFile] = File(None),
    police_permission: Optional[UploadFile] = File(None),
    cultural_pamphlet: Optional[UploadFile] = File(None),
    signature_upload: Optional[UploadFile] = File(None),
    files: Optional[List[UploadFile]] = File(None),

    # GUC / Ganesh Utsav Committee Dedicated Form Fields
    registration_id: Optional[int] = Form(None),
    application_no: Optional[str] = Form(None),
    assembly_constituency: Optional[str] = Form("Pendurthi"),
    president_name: Optional[str] = Form(None),
    president_phone: Optional[str] = Form(None),
    secretary_name: Optional[str] = Form(None),
    secretary_phone: Optional[str] = Form(None),
    treasurer_name: Optional[str] = Form(None),
    treasurer_phone: Optional[str] = Form(None),
    mandap_location: Optional[str] = Form(None),
    location_category: Optional[str] = Form(None),
    location_owner_details: Optional[str] = Form(None),
    idol_height: Optional[str] = Form(None),
    utsav_start_date: Optional[str] = Form(None),
    utsav_end_date: Optional[str] = Form(None),
    visarjan_date: Optional[str] = Form(None),
    visarjan_time: Optional[str] = Form(None),
    visarjan_phone: Optional[str] = Form(None),
    mandap_volunteers: Optional[str] = Form(None),
    cultural_programs: Optional[str] = Form(None),
    sound_system_details: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    formatted_address: Optional[str] = Form(None),
    applicant_signature: Optional[str] = Form(None),
    registered_from: Optional[str] = Form(None),
    landmark: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Submit community registration form with structured KYC uploads, location picker,
    and GUC (Ganesh Utsav Committee) physical form reproduction.
    Supports CREATE, SAVE, EDIT, and VIEW across Web, /mobile, Android, iOS.
    """
    import random
    import string
    import logging
    from decimal import Decimal
    from datetime import timedelta
    from app.core.security import SecurityManager
    from app.api.v1.endpoints.vgk_team import _next_vgk_partner_code
    from app.utils.phone_otp import normalize_phone_10

    logger = logging.getLogger("community_services")

    # 1. Resolve community_service_id if not provided (default to GUC service)
    if not community_service_id:
        svc = db.query(CommunityService).filter(
            or_(
                CommunityService.short_name.ilike('guc'),
                CommunityService.short_name.ilike('ganesh%'),
                CommunityService.service_name.ilike('%ganesh%')
            )
        ).first()
        if not svc:
            svc = db.query(CommunityService).filter(CommunityService.status == 'ACTIVE').first()
        if not svc:
            svc = CommunityService(
                service_name="విశాఖపట్నం జిల్లా గణేష్ ఉత్సవ సమితి",
                short_name="guc",
                description="సామూహిక గణేష్ ఉత్సవాలు జరుపుకొనుటకు నమోదు పత్రం (Application Form for Organizing Collective Ganesh Utsav)",
                start_date=get_indian_today(),
                end_date=get_indian_today() + timedelta(days=90),
                status="ACTIVE",
                applicable_verticals=["Solar", "Real Estate"],
                settings={"show_homepage_popup": False}
            )
            db.add(svc)
            db.commit()
            db.refresh(svc)
        community_service_id = svc.id

    # 2. Resolve field values with sensible defaults / fallbacks
    resolved_primary_name = (primary_name or president_name or association_name or "Ganesh Utsav Committee").strip()
    resolved_primary_phone = (primary_phone_1 or president_phone or "9999999999").strip()
    resolved_secondary_name = (secondary_name or secretary_name or "").strip()
    resolved_secondary_phone = (secondary_phone_1 or secretary_phone or "").strip()
    resolved_association_name = (association_name or mandap_location or "గణేష్ ఉత్సవ కమిటీ").strip()
    resolved_area = (area or mandap_location or "Pendurthi").strip()
    resolved_constituency = (assembly_constituency or "Pendurthi").strip()

    # Resolve registered_from origin: 'Ganesh Utsav Committee' vs 'Community Service'
    if not registered_from:
        if (application_no and any(k in application_no.lower() for k in ('guc', 'camgan'))) or (svc and svc.short_name and svc.short_name.lower() in ('camgan', 'guc', 'ganesh-utsav')):
            resolved_registered_from = 'Ganesh Utsav Committee'
        else:
            resolved_registered_from = 'Community Service'
    else:
        resolved_registered_from = registered_from.strip()

    # 3. Parse Dates
    parsed_start_date = None
    if utsav_start_date:
        d_norm = normalize_date_input(utsav_start_date)
        if d_norm:
            try:
                parsed_start_date = datetime.strptime(d_norm, "%Y-%m-%d").date()
            except Exception:
                pass

    parsed_end_date = None
    if utsav_end_date:
        d_norm = normalize_date_input(utsav_end_date)
        if d_norm:
            try:
                parsed_end_date = datetime.strptime(d_norm, "%Y-%m-%d").date()
            except Exception:
                pass

    parsed_visarjan_date = None
    if visarjan_date:
        d_norm = normalize_date_input(visarjan_date)
        if d_norm:
            try:
                parsed_visarjan_date = datetime.strptime(d_norm, "%Y-%m-%d").date()
            except Exception:
                pass

    # 4. Parse Volunteers (JSON or text)
    parsed_volunteers = []
    if mandap_volunteers:
        if isinstance(mandap_volunteers, list):
            parsed_volunteers = mandap_volunteers
        elif isinstance(mandap_volunteers, str):
            try:
                parsed_volunteers = json.loads(mandap_volunteers)
            except Exception:
                parsed_volunteers = [{"name": line.strip(), "phone": ""} for line in mandap_volunteers.splitlines() if line.strip()]

    # 5. Parse Cultural Programs (JSON or text)
    parsed_cultural = []
    if cultural_programs:
        if isinstance(cultural_programs, list):
            parsed_cultural = cultural_programs
        elif isinstance(cultural_programs, str):
            try:
                parsed_cultural = json.loads(cultural_programs)
            except Exception:
                parsed_cultural = [line.strip() for line in cultural_programs.splitlines() if line.strip()]

    # 6. Map Link
    if not google_location and latitude and longitude:
        google_location = f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"

    # 7. Check if EDIT mode (registration_id passed)
    reg = None
    if registration_id:
        reg = db.query(CommunityRegistration).filter(CommunityRegistration.id == registration_id).first()

    if not reg:
        if not application_no:
            application_no = f"GUC-2026-{random.randint(10000, 99999)}"

        reg = CommunityRegistration(
            community_service_id=community_service_id,
            association_name=resolved_association_name,
            primary_name=resolved_primary_name,
            primary_phone_1=resolved_primary_phone,
            primary_phone_2=primary_phone_2,
            secondary_name=resolved_secondary_name or None,
            secondary_phone_1=resolved_secondary_phone or None,
            secondary_phone_2=secondary_phone_2,
            area=resolved_area,
            pin_code=pin_code or "530051",
            district=district or "Visakhapatnam",
            state=state or "Andhra Pradesh",
            google_location=google_location,
            ref1_member_id=ref1_member_id,
            ref2_member_id=ref2_member_id,
            referral_type=referral_type or 'direct',
            referral_code=referral_code,

            # GUC dedicated fields
            application_no=application_no,
            assembly_constituency=resolved_constituency,
            president_name=president_name or resolved_primary_name,
            president_phone=president_phone or resolved_primary_phone,
            secretary_name=secretary_name or resolved_secondary_name or None,
            secretary_phone=secretary_phone or resolved_secondary_phone or None,
            treasurer_name=treasurer_name,
            treasurer_phone=treasurer_phone,
            mandap_location=mandap_location or resolved_area,
            location_category=location_category,
            location_owner_details=location_owner_details,
            idol_height=idol_height,
            utsav_start_date=parsed_start_date,
            utsav_end_date=parsed_end_date,
            visarjan_date=parsed_visarjan_date,
            visarjan_time=visarjan_time,
            visarjan_phone=visarjan_phone,
            mandap_volunteers=parsed_volunteers,
            cultural_programs=parsed_cultural,
            sound_system_details=sound_system_details,
            latitude=latitude,
            longitude=longitude,
            formatted_address=formatted_address or resolved_area,
            applicant_signature=applicant_signature,
            registered_from=resolved_registered_from,
            landmark=landmark,

            kyc_uploads=[],
            status='PENDING',
            created_at=get_indian_time(),
            updated_at=get_indian_time()
        )
        db.add(reg)
        db.commit()
        db.refresh(reg)
    else:
        # Update existing registration
        reg.association_name = resolved_association_name
        reg.primary_name = resolved_primary_name
        reg.primary_phone_1 = resolved_primary_phone
        if primary_phone_2 is not None: reg.primary_phone_2 = primary_phone_2
        if resolved_secondary_name: reg.secondary_name = resolved_secondary_name
        if resolved_secondary_phone: reg.secondary_phone_1 = resolved_secondary_phone
        if secondary_phone_2 is not None: reg.secondary_phone_2 = secondary_phone_2
        reg.area = resolved_area
        if pin_code: reg.pin_code = pin_code
        if district: reg.district = district
        if state: reg.state = state
        if google_location: reg.google_location = google_location
        if ref1_member_id: reg.ref1_member_id = ref1_member_id
        if ref2_member_id: reg.ref2_member_id = ref2_member_id
        if referral_type: reg.referral_type = referral_type
        if referral_code: reg.referral_code = referral_code

        # GUC fields update
        if application_no: reg.application_no = application_no
        reg.assembly_constituency = resolved_constituency
        reg.president_name = president_name or resolved_primary_name
        reg.president_phone = president_phone or resolved_primary_phone
        if secretary_name is not None: reg.secretary_name = secretary_name
        if secretary_phone is not None: reg.secretary_phone = secretary_phone
        if treasurer_name is not None: reg.treasurer_name = treasurer_name
        if treasurer_phone is not None: reg.treasurer_phone = treasurer_phone
        if mandap_location is not None: reg.mandap_location = mandap_location
        if location_category is not None: reg.location_category = location_category
        if location_owner_details is not None: reg.location_owner_details = location_owner_details
        if idol_height is not None: reg.idol_height = idol_height
        if parsed_start_date is not None: reg.utsav_start_date = parsed_start_date
        if parsed_end_date is not None: reg.utsav_end_date = parsed_end_date
        if parsed_visarjan_date is not None: reg.visarjan_date = parsed_visarjan_date
        if visarjan_time is not None: reg.visarjan_time = visarjan_time
        if visarjan_phone is not None: reg.visarjan_phone = visarjan_phone
        if mandap_volunteers is not None: reg.mandap_volunteers = parsed_volunteers
        if cultural_programs is not None: reg.cultural_programs = parsed_cultural
        if sound_system_details is not None: reg.sound_system_details = sound_system_details
        if latitude is not None: reg.latitude = latitude
        if longitude is not None: reg.longitude = longitude
        if formatted_address is not None: reg.formatted_address = formatted_address
        if applicant_signature is not None: reg.applicant_signature = applicant_signature
        if registered_from is not None: reg.registered_from = resolved_registered_from
        if landmark is not None: reg.landmark = landmark

        reg.updated_at = get_indian_time()
        db.commit()
        db.refresh(reg)

    # 8. Generate / Resolve login credentials
    partner_code = None
    raw_password = None
    clean_phone = normalize_phone_10(resolved_primary_phone) or resolved_primary_phone.strip()

    if not reg.user_id:
        existing_partner = db.query(OfficialPartner).filter(
            OfficialPartner.category == 'VGK_TEAM',
            or_(
                OfficialPartner.phone == clean_phone,
                OfficialPartner.phone == resolved_primary_phone.strip()
            )
        ).first()

        if existing_partner:
            partner = existing_partner
            partner_code = existing_partner.partner_code
            if clean_phone and existing_partner.phone != clean_phone:
                existing_partner.phone = clean_phone
                db.commit()
        else:
            raw_password = "".join(random.choices(string.ascii_letters + string.digits, k=8))
            password_hash = SecurityManager.get_password_hash(raw_password)
            company_id = 1
            partner_code = _next_vgk_partner_code(db, company_id)

            VGK_DEFAULT_ROOT = 'VGK07102207'
            default_root = db.query(OfficialPartner).filter(
                OfficialPartner.partner_code == VGK_DEFAULT_ROOT,
                OfficialPartner.category == 'VGK_TEAM'
            ).first()
            default_root_id = default_root.id if default_root else None

            parent_id = ref1_member_id if referral_type == 'vgk_member' and ref1_member_id else default_root_id
            reg_by = referral_code.strip().upper() if referral_type == 'staff' and referral_code else VGK_DEFAULT_ROOT

            partner = OfficialPartner(
                company_id=company_id,
                partner_code=partner_code,
                partner_name=resolved_primary_name,
                phone=clean_phone,
                email=None,
                category='VGK_TEAM',
                is_active=False,
                vgk_role='COMMUNITY',
                parent_partner_id=parent_id,
                registered_by_emp_code=reg_by,
                vgk_points_balance=Decimal('0'),
                password_hash=password_hash,
                created_at=get_indian_time(),
                updated_at=get_indian_time()
            )
            db.add(partner)
            db.commit()
            db.refresh(partner)

        reg.user_id = partner.id
        db.commit()
    else:
        partner = db.query(OfficialPartner).filter(OfficialPartner.id == reg.user_id).first()
        partner_code = partner.partner_code if partner else None

    # 9. Handle uploads (Aadhaar, Permission, Cultural Pamphlet, Signature)
    kyc_paths = list(reg.kyc_uploads or [])

    upload_map = [
        ("1st Contact Aadhaar Front", aadhar_first_front),
        ("1st Contact Aadhaar Back", aadhar_first_back),
        ("2nd Contact Aadhaar Front", aadhar_second_front),
        ("2nd Contact Aadhaar Back", aadhar_second_back),
        ("Police Permission Letter", police_permission),
        ("Cultural Programs Pamphlet", cultural_pamphlet),
        ("Applicant Signature", signature_upload),
    ]

    for label, file_obj in upload_map:
        if file_obj and file_obj.filename:
            try:
                upload_res = await UniversalUploadService.handle_upload(
                    file=file_obj,
                    table_name="community_registrations",
                    record_id=reg.id,
                    uploaded_by_id=0,
                    uploaded_by_type="user",
                    storage_dir="community_kyc",
                    db=db
                )
                if upload_res.get("file_path"):
                    fpath = upload_res["file_path"]
                    kyc_paths.append(fpath)
                    if label == "Applicant Signature" and not reg.applicant_signature:
                        reg.applicant_signature = fpath
            except Exception as e:
                logger.error("File upload error for %s: %s", label, e)

    if files:
        for file in files:
            if file and file.filename:
                try:
                    upload_res = await UniversalUploadService.handle_upload(
                        file=file,
                        table_name="community_registrations",
                        record_id=reg.id,
                        uploaded_by_id=0,
                        uploaded_by_type="user",
                        storage_dir="community_kyc",
                        db=db
                    )
                    if upload_res.get("file_path"):
                        kyc_paths.append(upload_res["file_path"])
                except Exception as e:
                    logger.error("File upload error for extra file: %s", e)

    if kyc_paths:
        reg.kyc_uploads = kyc_paths
        db.commit()
        db.refresh(reg)

    return {
        "success": True,
        "message": "Registration submitted successfully! Upline / Admin verification is pending.",
        "registration_id": reg.id,
        "application_no": reg.application_no,
        "data": reg.to_dict(),
        "credentials": {
            "partner_code": partner_code,
            "raw_password": raw_password,
            "phone": resolved_primary_phone
        }
    }


# ──────────────────────────────────────────────────────────────────────
# 2. ADMIN ENDPOINTS
# ──────────────────────────────────────────────────────────────────────

@router.get("/admin/services")
def list_services_admin(db: Session = Depends(get_db), current_user: StaffEmployee = Depends(get_current_staff_user)):
    """
    List all community services for admin panel configuration.
    """
    services = db.query(CommunityService).filter(CommunityService.status != 'DELETED').order_by(desc(CommunityService.created_at)).all()
    return {
        "success": True,
        "data": [s.to_dict() for s in services]
    }

def extract_text_from_file(file: UploadFile) -> str:
    content = ""
    filename = file.filename.lower()
    try:
        if filename.endswith(".txt"):
            content = file.file.read().decode("utf-8", errors="ignore")
        elif filename.endswith(".pdf"):
            try:
                import pypdf
                reader = pypdf.PdfReader(file.file)
                text_pages = []
                for page in reader.pages:
                    text_pages.append(page.extract_text() or "")
                content = "\n".join(text_pages)
            except Exception:
                try:
                    import PyPDF2
                    reader = PyPDF2.PdfReader(file.file)
                    text_pages = []
                    for page in reader.pages:
                        text_pages.append(page.extract_text() or "")
                    content = "\n".join(text_pages)
                except Exception:
                    file.file.seek(0)
                    raw = file.file.read()
                    content = "".join([chr(b) if 32 <= b < 127 or b in [10, 13] else " " for b in raw])
        elif filename.endswith(".docx"):
            try:
                import docx
                doc = docx.Document(file.file)
                content = "\n".join([p.text for p in doc.paragraphs])
            except Exception:
                file.file.seek(0)
                raw = file.file.read()
                content = "".join([chr(b) if 32 <= b < 127 or b in [10, 13] else " " for b in raw])
        else:
            content = file.file.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"Error extracting text: {e}")
    return content

def generate_community_seva_landing_page(document_text: str, service_name: str, short_name: str, ai_prompt: Optional[str] = None, banner_images: Optional[List[str]] = None, settings: Optional[dict] = None) -> str:
    import re
    from datetime import datetime
    
    settings = settings or {}

    # Helper function to get embeddable youtube url
    def get_youtube_embed_url(url: str) -> Optional[str]:
        if not url:
            return None
        video_id = None
        if "youtube.com/embed/" in url:
            return url
        elif "youtu.be/" in url:
            video_id = url.split("youtu.be/")[-1].split("?")[0].split("&")[0]
        elif "v=" in url:
            video_id = url.split("v=")[-1].split("&")[0].split("?")[0]
        elif "youtube.com/watch" in url:
            video_id = url.split("watch/")[-1].split("?")[0].split("&")[0]
        if video_id:
            return f"https://www.youtube.com/embed/{video_id}"
        return url

    # 1. Concept & Keyword Parsing & Filtering (ignoring generic legal/collections text)
    raw_lines = [line.strip() for line in document_text.split("\n") if line.strip()]
    filtered_lines = []
    legalese_keywords = [
        "confidential", "internal use only", "proprietary", "all rights reserved", "subject to contract", 
        "draft version", "classification:", "page:", "reconciliation", "invoice", "bank statement", 
        "ledger", "arrears", "overdue", "collections", "payment history", "outstanding", "billing record", 
        "receipt", "dun & bradstreet", "cibil check", "credit check", "accounting reference"
    ]
    for line in raw_lines:
        if any(kw in line.lower() for kw in legalese_keywords):
            continue
        filtered_lines.append(line)
        
    title = settings.get("custom_title")
    if not title:
        for line in filtered_lines:
            if any(line.lower().startswith(p) for p in ["title:", "campaign:", "project:", "name:"]):
                title = line.split(":", 1)[1].strip()
                break
        if not title:
            for line in filtered_lines[:3]:
                if not any(line.lower().startswith(p) for p in ["tagline:", "motto:", "slogan:", "tag line:"]):
                    title = line
                    break
        if not title or len(title) < 5 or len(title) > 80:
            title = service_name

    tagline = settings.get("custom_tagline")
    if not tagline:
        for line in filtered_lines:
            if any(line.lower().startswith(p) for p in ["tagline:", "motto:", "slogan:", "tag line:"]):
                tagline = line.split(":", 1)[1].strip()
                break
        if not tagline:
            for line in filtered_lines[:6]:
                if any(w in line.lower() for w in ["go solar", "support your", "empower", "welfare", "sustainable"]):
                    tagline = line
                    break

    # Main Financial/Contribution Callout
    financial_callout = settings.get("contribution_callout")
    if not financial_callout:
        rupee_pattern = re.compile(r'(?:₹|Rs\.?)\s?\d+(?:,\d+)*')
        for line in filtered_lines:
            match = rupee_pattern.search(line)
            if match and any(w in line.lower() for w in ["contribut", "payout", "earn", "reward", "incentive", "give", "seva"]):
                financial_callout = line
                break
        if not financial_callout:
            for line in filtered_lines:
                match = rupee_pattern.search(line)
                if match:
                    financial_callout = f"FOR EVERY ELIGIBLE CUSTOMER, {match.group(0)} IS CONTRIBUTED TO YOUR COMMUNITY!"
                    break
        if not financial_callout:
            financial_callout = "FOR EVERY ELIGIBLE SOLAR CUSTOMER, ₹5,000 IS CONTRIBUTED DIRECTLY TO YOUR REGISTERED MANDAPAM!"

    # Step-by-Step Workflow Steps
    steps = []
    cashflow_steps = settings.get("cashflow_steps")
    if cashflow_steps and isinstance(cashflow_steps, list) and len(cashflow_steps) >= 4:
        for idx, step_text in enumerate(cashflow_steps[:4]):
            steps.append({"num": f"0{idx+1}", "text": step_text})
    else:
        step_pattern = re.compile(r'^(?:step|phase|stage)?\s?(\d+)[:.)]?\s+(.+)$', re.IGNORECASE)
        for line in filtered_lines:
            match = step_pattern.match(line)
            if match:
                steps.append({"num": f"0{match.group(1)}"[-2:], "text": match.group(2).strip()})
            elif line.lower().startswith(("first:", "second:", "third:", "then:", "next:", "finally:")):
                parts = line.split(":", 1)
                steps.append({"num": f"0{len(steps)+1}"[-2:], "text": parts[1].strip()})
                
        if len(steps) < 3:
            for line in filtered_lines:
                clean = line.lstrip("-*•0123456789. ")
                if clean and (line.startswith(("-", "*", "•")) or line[0].isdigit()) and len(clean) > 10 and len(clean) < 150:
                    if any(w in line.lower() for w in ["register", "sign up", "submit", "share", "refer", "install", "payout", "verify", "check", "approve"]):
                        steps.append({"num": f"0{len(steps)+1}"[-2:], "text": clean})
                        if len(steps) >= 6:
                            break

    # Target Audience Benefit Groups
    cust_benefits = []
    comm_benefits = []
    partner_benefits = []
    
    if settings.get("benefits_customers"):
        cust_benefits = [b.strip() for b in settings["benefits_customers"].split("\n") if b.strip()]
    if settings.get("benefits_community"):
        comm_benefits = [b.strip() for b in settings["benefits_community"].split("\n") if b.strip()]
    if settings.get("benefits_partners"):
        partner_benefits = [b.strip() for b in settings["benefits_partners"].split("\n") if b.strip()]

    if not cust_benefits or not comm_benefits or not partner_benefits:
        for line in filtered_lines:
            clean = line.lstrip("-*•0123456789. ")
            if len(clean) < 10 or len(clean) > 200:
                continue
            lower_line = line.lower()
            if not cust_benefits and any(w in lower_line for w in ["customer", "homeowner", "consumer", "resident"]):
                cust_benefits.append(clean)
            elif not comm_benefits and any(w in lower_line for w in ["committee", "community", "mandapam", "seva samithi", "village", "society"]):
                comm_benefits.append(clean)
            elif not partner_benefits and any(w in lower_line for w in ["member", "partner", "referrer", "cp", "agent"]):
                partner_benefits.append(clean)

    # 2. Dynamic Service-Based Theme Generator (with Regex word boundary checks)
    text_to_scan = (document_text + " " + service_name + " " + short_name + " " + (ai_prompt or "")).lower()
    
    is_festival = any(re.search(rf"\b{kw}\b", text_to_scan) for kw in ["puja", "ganesh", "durga", "utsav", "festival", "diwali", "navratri", "mandapam", "seva samithi", "celebration", "temple"])
    is_eco = any(re.search(rf"\b{kw}\b", text_to_scan) for kw in ["solar", "green", "tree", "trees", "plantation", "energy", "environment", "clean", "water", "panel", "eco", "ecology", "nature"])
    is_health = any(re.search(rf"\b{kw}\b", text_to_scan) for kw in ["blood", "health", "clinic", "medical", "education", "school", "social", "donation", "patient", "charity"])
    
    if is_festival:
        theme = "festive"
    elif is_eco:
        theme = "eco"
    else:
        theme = "health"

    if theme == "festive":
        gradient_bg = "linear-gradient(135deg, rgba(254, 243, 199, 0.15) 0%, rgba(253, 230, 138, 0.15) 50%, rgba(255, 255, 255, 1) 100%)"
        text_color = "#0f172a"
        subtext_color = "#334155"
        accent_primary = "#dc2626"
        accent_secondary = "#d97706"
        accent_tertiary = "#1e3a8a"
        card_bg = "background: rgba(255, 255, 255, 0.6); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border: 1.5px solid rgba(217, 119, 6, 0.15);"
        badge_bg = "rgba(217, 119, 6, 0.1)"
        badge_border = "1px solid #d97706"
        badge_text = "#d97706"
        icon_main = "fa-om"
        icon_payout = "fa-hands-holding-circle"
        glow_shadow = "rgba(217, 119, 6, 0.2)"
        
        if not tagline:
            tagline = f"Go Solar. Support Your {title} Mandapam."
        if not financial_callout:
            financial_callout = "FOR EVERY ELIGIBLE SOLAR CUSTOMER, ₹5,000 IS CONTRIBUTED DIRECTLY TO YOUR REGISTERED MANDAPAM!"
            
        if not steps:
            steps = [
                {"num": "01", "text": "Register your local Seva Mandapam / Committee on our portal."},
                {"num": "02", "text": "Submit energy bills or refer local residential solar leads."},
                {"num": "03", "text": "VGK surveyors verify solar installation feasibility."},
                {"num": "04", "text": "Customer completes the first milestone advance payment."},
                {"num": "05", "text": "₹5,000 Seva Contribution is instantly released to the Mandapam."}
            ]
        
        if not cust_benefits:
            cust_benefits = ["Up to 40% savings on monthly electricity bills", "Zero-upfront solar installation options", "Free home survey and government subsidy guidance"]
        if not comm_benefits:
            comm_benefits = ["Direct financial contribution of ₹5,000 per install", "Green certification and public recognition", "Free solar illumination for mandapam main halls"]
        if not partner_benefits:
            partner_benefits = ["L1, L2, L5 upline partner commission shares", "Direct verification tracking via partner app", "Exclusive festive marketing support kits"]

        svg_graphic = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 380" style="width: 100%; height: 100%; border-radius: 16px; background: linear-gradient(135deg, #78350f 0%, #451a03 50%, #1c1917 100%);">
            <defs>
                <radialGradient id="sunGlow" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stop-color="#fbbf24" stop-opacity="0.4"/>
                    <stop offset="100%" stop-color="#78350f" stop-opacity="0"/>
                </radialGradient>
            </defs>
            <rect width="100%" height="100%" fill="#1c1917" />
            <circle cx="400" cy="190" r="180" fill="url(#sunGlow)"/>
            <circle cx="400" cy="190" r="120" fill="none" stroke="#d97706" stroke-width="1.5" stroke-dasharray="10 5" opacity="0.4"/>
            <!-- Lord Ganesha Geometric Motif -->
            <g transform="translate(400, 190) scale(1.2)">
                <path d="M 0,-40 C 15,-40 25,-25 25,-10 C 25,15 -25,15 -25,-10 C -25,-25 -15,-40 0,-40 Z" fill="none" stroke="#fbbf24" stroke-width="2" />
                <path d="M 0,-25 L 0,10 C 0,25 15,35 15,45" fill="none" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round" />
                <circle cx="0" cy="-15" r="4" fill="#ef4444" />
                <path d="M -15,-10 Q 0,-20 15,-10" fill="none" stroke="#fbbf24" stroke-width="2" />
            </g>
        </svg>"""
    
    elif theme == "eco":
        gradient_bg = "linear-gradient(135deg, rgba(209, 250, 229, 0.15) 0%, rgba(167, 243, 208, 0.15) 50%, rgba(255, 255, 255, 1) 100%)"
        text_color = "#0f172a"
        subtext_color = "#334155"
        accent_primary = "#15803d"
        accent_secondary = "#0d9488"
        accent_tertiary = "#0f766e"
        card_bg = "background: rgba(255, 255, 255, 0.6); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border: 1.5px solid rgba(21, 128, 61, 0.15);"
        badge_bg = "rgba(16, 185, 129, 0.1)"
        badge_border = "1px solid #10b981"
        badge_text = "#047857"
        icon_main = "fa-leaf"
        icon_payout = "fa-solar-panel"
        glow_shadow = "rgba(16, 185, 129, 0.2)"
        
        if not tagline:
            tagline = f"Support Community Welfare. Drive Green Energy Adoption via {title}."
        if not financial_callout:
            financial_callout = "FOR EVERY ELIGIBLE GREEN CONVERSION, ₹5,000 IS DIRECTLY CONTRIBUTED TO YOUR WELFARE FUND!"
            
        if not steps:
            steps = [
                {"num": "01", "text": "Register your local housing society or eco-welfare association."},
                {"num": "02", "text": "Submit details of households willing to explore rooftop solar setup."},
                {"num": "03", "text": "Free assessment and technical feasibility audits conducted by VGK."},
                {"num": "04", "text": "Milestone approval upon verification of customer deposit validation."},
                {"num": "05", "text": "₹5,000 contribution released directly to the association's development fund."}
            ]
        
        if not cust_benefits:
            cust_benefits = ["Lower green tariffs and 30-40% savings on bills", "Eco-friendly rooftop panels with 25-year warranty", "Hassle-free application for government subsidies"]
        if not comm_benefits:
            comm_benefits = ["₹5,000 welfare fund contribution per connection", "Sustainable development index credit for the village/society", "Solar-powered community streetlighting support"]
        if not partner_benefits:
            partner_benefits = ["Direct tracking and payouts via referral dashboard", "Dedicated field support advisor for local campaigns", "High conversion rates backed by VGK brand authority"]

        svg_graphic = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 380" style="width: 100%; height: 100%; border-radius: 16px; background: linear-gradient(135deg, #064e3b 0%, #022c22 50%, #0c0a09 100%);">
            <defs>
                <linearGradient id="panelGlow" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#10b981" stop-opacity="0.3"/>
                    <stop offset="100%" stop-color="#022c22" stop-opacity="0"/>
                </linearGradient>
            </defs>
            <rect width="100%" height="100%" fill="#0c0a09" />
            <polygon points="200,380 300,100 500,100 600,380" fill="url(#panelGlow)" />
            <g transform="translate(400, 190) scale(1.3)">
                <rect x="-40" y="-20" width="80" height="40" rx="4" fill="#0f766e" stroke="#34d399" stroke-width="2" />
                <line x1="-40" y1="0" x2="40" y2="0" stroke="#34d399" stroke-width="1.5" />
                <line x1="-20" y1="-20" x2="-20" y2="20" stroke="#34d399" stroke-width="1.5" />
                <line x1="20" y1="-20" x2="20" y2="20" stroke="#34d399" stroke-width="1.5" />
                <line x1="0" y1="-20" x2="0" y2="20" stroke="#34d399" stroke-width="1.5" />
            </g>
        </svg>"""

    else: # health
        gradient_bg = "linear-gradient(135deg, rgba(254, 226, 226, 0.15) 0%, rgba(254, 202, 202, 0.15) 50%, rgba(255, 255, 255, 1) 100%)"
        text_color = "#0f172a"
        subtext_color = "#334155"
        accent_primary = "#dc2626"
        accent_secondary = "#4f46e5"
        accent_tertiary = "#312e81"
        card_bg = "background: rgba(255, 255, 255, 0.6); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border: 1.5px solid rgba(220, 38, 38, 0.15);"
        badge_bg = "rgba(239, 68, 68, 0.1)"
        badge_border = "1px solid #ef4444"
        badge_text = "#b91c1c"
        icon_main = "fa-hand-holding-heart"
        icon_payout = "fa-heart-circle-check"
        glow_shadow = "rgba(239, 68, 68, 0.2)"
        
        if not tagline:
            tagline = f"Support Health & Wellness. Drive Community Progress via {title}."
        if not financial_callout:
            financial_callout = "FOR EVERY VALID HEALTH REGISTRATION, ₹5,000 IS DIRECTLY CONTRIBUTED TO YOUR HEALTH FUND!"
            
        if not steps:
            steps = [
                {"num": "01", "text": "Register your local welfare wing, NGO, or charity association."},
                {"num": "02", "text": "Conduct checkup campaigns and log community enrollment interest."},
                {"num": "03", "text": "VGK health advisors verify and validate individual member profiles."},
                {"num": "04", "text": "Approval of eligible profiles upon verification of registration criteria."},
                {"num": "05", "text": "₹5,000 social welfare contribution is credited to the registered organization."}
            ]
        
        if not cust_benefits:
            cust_benefits = ["Access to free health checkups and diagnostic counseling", "Subsidised healthcare packages and family coverage guidance", "Direct support lines for emergency medical queries"]
        if not comm_benefits:
            comm_benefits = ["Direct aid of ₹5,000 per family validation", "Free health camp hosting for mandapam halls or local clinics", "Public certificate of contribution to healthcare wellness"]
        if not partner_benefits:
            partner_benefits = ["Instant partner commission structures mapped automatically", "Digital dashboard tracking for leads and approvals", "Full assistance with patient files and onboarding documentation"]

        svg_graphic = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 380" style="width: 100%; height: 100%; border-radius: 16px; background: linear-gradient(135deg, #7f1d1d 0%, #450a0a 50%, #1c0505 100%);">
            <rect width="100%" height="100%" fill="#1c0505" />
            <path d="M400 240 C360 190, 310 190, 310 130 C310 80, 370 80, 400 120 C430 80, 490 80, 490 130 C490 190, 440 240, 400 270 Z" fill="#ef4444" opacity="0.8" />
        </svg>"""

    # 3. Build Gallery Grid HTML (uploaded + dynamic fallback graphics cards)
    fallback_cards = [
        # Card 1: Ganesha / Festive Fallback Widescreen Poster
        f'''<div class="gallery-card" style="border-radius: 12px; overflow: hidden; border: 1.5px solid rgba(217, 119, 6, 0.2); max-height: 220px; height: 220px; background: linear-gradient(135deg, #78350f 0%, #451a03 100%); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; text-align: center; padding: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); transition: all 0.3s ease; position: relative;">
            <div style="position: absolute; inset: 0; background: url('https://images.unsplash.com/photo-1567591974584-e18552911a58?auto=format&fit=crop&w=400&q=80') center; background-size: cover; opacity: 0.15;"></div>
            <i class="fas fa-om" style="font-size: 36px; color: #fbbf24; z-index: 1;"></i>
            <span style="font-size: 12px; font-weight: 800; color: #fde68a; text-transform: uppercase; letter-spacing: 1px; z-index: 1;">Ganesh Green Seva</span>
        </div>''',
        # Card 2: Solar Panel / Clean Energy Fallback Widescreen Poster
        f'''<div class="gallery-card" style="border-radius: 12px; overflow: hidden; border: 1.5px solid rgba(16, 185, 129, 0.2); max-height: 220px; height: 220px; background: linear-gradient(135deg, #064e3b 0%, #022c22 100%); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; text-align: center; padding: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); transition: all 0.3s ease; position: relative;">
            <div style="position: absolute; inset: 0; background: url('https://images.unsplash.com/photo-1508514177221-188b1cf16e9d?auto=format&fit=crop&w=400&q=80') center; background-size: cover; opacity: 0.15;"></div>
            <i class="fas fa-solar-panel" style="font-size: 36px; color: #34d399; z-index: 1;"></i>
            <span style="font-size: 12px; font-weight: 800; color: #a7f3d0; text-transform: uppercase; letter-spacing: 1px; z-index: 1;">Rooftop Solar Panel</span>
        </div>''',
        # Card 3: Health Wellness / Support Fallback Widescreen Poster
        f'''<div class="gallery-card" style="border-radius: 12px; overflow: hidden; border: 1.5px solid rgba(239, 68, 68, 0.2); max-height: 220px; height: 220px; background: linear-gradient(135deg, #7f1d1d 0%, #450a0a 100%); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; text-align: center; padding: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); transition: all 0.3s ease; position: relative;">
            <div style="position: absolute; inset: 0; background: url('https://images.unsplash.com/photo-1576091160550-2173dba999ef?auto=format&fit=crop&w=400&q=80') center; background-size: cover; opacity: 0.15;"></div>
            <i class="fas fa-hand-holding-heart" style="font-size: 36px; color: #fca5a5; z-index: 1;"></i>
            <span style="font-size: 12px; font-weight: 800; color: #fecaca; text-transform: uppercase; letter-spacing: 1px; z-index: 1;">Community Wellness</span>
        </div>'''
    ]

    display_images = [img for img in (banner_images or []) if img]
    gallery_cards_html = ""
    for img in display_images[:4]:
        gallery_cards_html += f"""        <div class="gallery-card" style="border-radius: 12px; overflow: hidden; border: 1px solid rgba(255,255,255,0.15); max-height: 220px; height: 220px; box-shadow: 0 12px 30px rgba(0,0,0,0.25); transition: all 0.3s ease; position: relative;">
            <img src="/storage/{img}" style="width: 100%; height: 100%; object-fit: cover;" alt="Campaign Widescreen Poster" />
            <div style="position: absolute; inset: 0; background: linear-gradient(to top, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0) 50%);"></div>
        </div>
"""
    
    needed = max(3, len(display_images))
    idx_fallback = 0
    while (len(display_images) + idx_fallback) < needed:
        gallery_cards_html += "        " + fallback_cards[idx_fallback % len(fallback_cards)] + "\n"
        idx_fallback += 1

    gallery_section_html = f"""
    <!-- Cinematic Gallery Showcase (Award-Winning Page Centerpiece) -->
    <section style="margin-bottom: 36px; margin-top: 10px;">
        <h4 style="font-size: 14px; font-weight: 900; color: {accent_tertiary} !important; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 20px; display: flex; align-items: center; gap: 8px; border-bottom: 1.5px solid rgba(0,0,0,0.06); padding-bottom: 8px;">
            <i class="fas fa-camera-retro" style="color: {accent_secondary};"></i>
            Campaign Gallery & Highlights
        </h4>
        <div class="seva-gallery-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 24px;">
{gallery_cards_html}        </div>
    </section>
"""

    # Section 8 YouTube Video Player
    video_embed_url = get_youtube_embed_url(settings.get("youtube_video_url"))
    video_section_html = ""
    if video_embed_url:
        video_section_html = f"""
        <div class="video-container" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); margin-top: 24px; margin-bottom: 24px;">
            <iframe src="{video_embed_url}" style="position: absolute; top:0; left:0; width:100%; height:100%; border:0;" allowfullscreen></iframe>
        </div>
        """

    # 4. HTML Articulation & Custom Styles
    style_block = f"""
    <style>
        .seva-articulator {{
            font-family: 'Outfit', sans-serif;
            color: {text_color} !important;
            padding: 15px;
            background: {gradient_bg};
            border-radius: 20px;
        }}
        .seva-articulator h2, 
        .seva-articulator h3, 
        .seva-articulator h4, 
        .seva-articulator h5, 
        .seva-articulator p, 
        .seva-articulator li, 
        .seva-articulator span {{
            color: {text_color} !important;
        }}
        .workflow-step-card {{
            {card_bg}
            padding: 20px;
            border-radius: 16px;
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.03);
            transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
        }}
        .workflow-step-card:hover {{
            transform: translateY(-6px);
            border-color: {accent_primary} !important;
            box-shadow: 0 12px 30px {glow_shadow} !important;
        }}
        .benefit-group-card {{
            {card_bg}
            padding: 24px;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.03);
            transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
        }}
        .benefit-group-card:hover {{
            transform: translateY(-6px);
            border-color: {accent_secondary} !important;
            box-shadow: 0 12px 30px {glow_shadow} !important;
        }}
        .gallery-card {{
            transition: transform 0.4s cubic-bezier(0.165, 0.84, 0.44, 1), box-shadow 0.4s ease;
        }}
        .gallery-card:hover {{
            transform: scale(1.05) translateY(-4px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.3) !important;
            cursor: pointer;
        }}
    </style>
    """

    # Build Workflow HTML
    workflow_html = ""
    for step in steps:
        workflow_html += f"""        <div class="workflow-step-card">
            <div style="width: 36px; height: 36px; border-radius: 50%; background: {accent_primary}; color: #fff !important; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 900; margin-bottom: 12px; box-shadow: 0 4px 10px {glow_shadow};">
                <span style="color: #fff !important;">{step['num']}</span>
            </div>
            <p style="font-size: 12px; line-height: 1.5; margin: 0; font-weight: 700; text-align: center;">
                {step['text']}
            </p>
        </div>
"""

    # Build Benefits lists
    cust_benefits_html = ""
    for cb in cust_benefits[:4]:
        cust_benefits_html += f"""            <li style="position: relative; padding-left: 20px; margin-bottom: 10px; font-size: 12.5px; line-height: 1.5; display: flex; align-items: flex-start; gap: 8px;">
                <i class="fas fa-check-circle" style="color: {accent_primary}; font-size: 14px; margin-top: 3px; flex-shrink: 0;"></i>
                <span>{cb}</span>
            </li>
"""
    comm_benefits_html = ""
    for cmb in comm_benefits[:4]:
        comm_benefits_html += f"""            <li style="position: relative; padding-left: 20px; margin-bottom: 10px; font-size: 12.5px; line-height: 1.5; display: flex; align-items: flex-start; gap: 8px;">
                <i class="fas fa-check-circle" style="color: {accent_primary}; font-size: 14px; margin-top: 3px; flex-shrink: 0;"></i>
                <span>{cmb}</span>
            </li>
"""
    partner_benefits_html = ""
    for pb in partner_benefits[:4]:
        partner_benefits_html += f"""            <li style="position: relative; padding-left: 20px; margin-bottom: 10px; font-size: 12.5px; line-height: 1.5; display: flex; align-items: flex-start; gap: 8px;">
                <i class="fas fa-check-circle" style="color: {accent_primary}; font-size: 14px; margin-top: 3px; flex-shrink: 0;"></i>
                <span>{pb}</span>
            </li>
"""

    # Build JSON-LD Structured SEO Schema
    json_ld = f"""
    <script type="application/ld+json" id="seva-jsonld-data">
    {{
        "@context": "https://schema.org",
        "@type": "Event",
        "name": "{title}",
        "description": "{tagline}",
        "startDate": "{datetime.now().strftime('%Y-%m-%d')}",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "eventStatus": "https://schema.org/EventScheduled",
        "organizer": {{
            "@type": "Organization",
            "name": "VGK4U Platform",
            "url": "https://vgk4u.com"
        }}
    }}
    </script>
    """

    # Cinematic split-screen hero layout
    hero_html = f"""
    <!-- Cinematic Full-Bleed Hero Banner -->
    <div class="hero-poster-container" style="position: relative; margin-bottom: 32px; border-radius: 20px; overflow: hidden; box-shadow: 0 15px 35px rgba(0,0,0,0.15); border: 2px solid {badge_border.split()[-1]}; height: 380px;">
        <div id="dynamic-poster-placeholder" style="width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; overflow: hidden;">
            {svg_graphic}
        </div>
        <div style="position: absolute; inset: 0; background: linear-gradient(to top, rgba(15, 23, 42, 0.95) 0%, rgba(15, 23, 42, 0.6) 50%, rgba(15, 23, 42, 0) 100%); display: flex; flex-direction: column; justify-content: flex-end; padding: 32px; text-align: left;">
            <div style="background: {accent_primary}; color: #fff !important; padding: 6px 12px; border-radius: 6px; font-size: 11px; font-weight: 900; text-transform: uppercase; letter-spacing: 1.5px; display: inline-block; margin-bottom: 12px; width: fit-content; box-shadow: 0 4px 10px rgba(0,0,0,0.2);">
                <span style="color: #fff !important;">{short_name} Campaign</span>
            </div>
            <h2 style="font-size: 28px; font-weight: 900; color: #fff !important; margin: 0 0 10px 0; line-height: 1.15; text-shadow: 0 4px 8px rgba(0,0,0,0.6); font-family: 'Outfit', sans-serif; letter-spacing: 0.5px;">
                {title}
            </h2>
            <p style="font-size: 15px; color: #e2e8f0 !important; margin: 0; font-weight: 600; text-shadow: 0 2px 4px rgba(0,0,0,0.6); max-width: 650px; line-height: 1.4;">
                {tagline}
            </p>
        </div>
    </div>
    """

    html = f"""{style_block}{json_ld}
<article class="seva-articulator {theme}" data-theme="{theme}" data-tagline="{tagline}" data-yt-embed="{video_embed_url or ''}">
    
    {hero_html}

    {gallery_section_html}

    {video_section_html}

    <!-- High-Contrast Cinematic Callout Banner -->
    <div style="background: {gradient_bg}; border-left: 6px solid {accent_primary}; border-radius: 12px; padding: 24px; margin-bottom: 32px; box-shadow: 0 8px 30px rgba(0,0,0,0.05); position: relative; overflow: hidden; border-top: 1px solid rgba(0,0,0,0.05); border-right: 1px solid rgba(0,0,0,0.05); border-bottom: 1px solid rgba(0,0,0,0.05);">
        <div style="position: absolute; top: -10px; right: -10px; font-size: 80px; color: {accent_secondary}; opacity: 0.08; pointer-events: none;">
            <i class="fas {icon_payout}"></i>
        </div>
        <h4 style="font-size: 12px; font-weight: 900; color: {accent_primary} !important; text-transform: uppercase; letter-spacing: 2px; margin: 0 0 8px 0;">
            Core Campaign Benefit Rule
        </h4>
        <p style="font-size: 16.5px; font-weight: 900; color: {accent_tertiary} !important; margin: 0; line-height: 1.5; font-family: 'Outfit', sans-serif; letter-spacing: 0.2px;">
            {financial_callout.upper()}
        </p>
    </div>

    <!-- Dynamic Step-by-Step "How It Works" Flow -->
    <section style="margin-bottom: 36px;">
        <h4 style="font-size: 14px; font-weight: 900; color: {accent_tertiary} !important; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 20px; display: flex; align-items: center; gap: 8px; border-bottom: 1.5px solid rgba(0,0,0,0.06); padding-bottom: 8px;">
            <i class="fas fa-map-signs" style="color: {accent_secondary};"></i>
            How It Works
        </h4>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(145px, 1fr)); gap: 16px;">
{workflow_html}        </div>
    </section>

    <!-- Multi-Column Audience Benefits Grid -->
    <section style="margin-bottom: 20px;">
        <h4 style="font-size: 14px; font-weight: 900; color: {accent_tertiary} !important; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 20px; display: flex; align-items: center; gap: 8px; border-bottom: 1.5px solid rgba(0,0,0,0.06); padding-bottom: 8px;">
            <i class="fas fa-trophy" style="color: {accent_secondary};"></i>
            Campaign Benefits Breakdown
        </h4>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px;">
            
            <!-- Customers Card -->
            <div class="benefit-group-card">
                <h5 style="font-size: 14px; font-weight: 800; color: {accent_tertiary} !important; margin: 0 0 16px 0; border-bottom: 2px solid {accent_primary}; padding-bottom: 8px; display: flex; align-items: center; gap: 8px;">
                    <i class="fas fa-user-check" style="color: {accent_secondary};"></i>
                    For Customers
                </h5>
                <ul style="list-style-type: none; padding-left: 0; margin: 0;">
{cust_benefits_html}                </ul>
            </div>

            <!-- Community Card -->
            <div class="benefit-group-card">
                <h5 style="font-size: 14px; font-weight: 800; color: {accent_tertiary} !important; margin: 0 0 16px 0; border-bottom: 2px solid {accent_primary}; padding-bottom: 8px; display: flex; align-items: center; gap: 8px;">
                    <i class="fas fa-hotel" style="color: {accent_secondary};"></i>
                    For Community
                </h5>
                <ul style="list-style-type: none; padding-left: 0; margin: 0;">
{comm_benefits_html}                </ul>
            </div>

            <!-- Partners Card -->
            <div class="benefit-group-card">
                <h5 style="font-size: 14px; font-weight: 800; color: {accent_tertiary} !important; margin: 0 0 16px 0; border-bottom: 2px solid {accent_primary}; padding-bottom: 8px; display: flex; align-items: center; gap: 8px;">
                    <i class="fas fa-user-group" style="color: {accent_secondary};"></i>
                    For VGK Members
                </h5>
                <ul style="list-style-type: none; padding-left: 0; margin: 0;">
{partner_benefits_html}                </ul>
            </div>

        </div>
    </section>

</article>"""
    return html



@router.post("/admin/services")
async def create_service_admin(
    service_name: str = Form(...),
    short_name: str = Form(...),
    description: Optional[str] = Form(None),
    start_date: str = Form(...),
    end_date: str = Form(...),
    applicable_verticals: str = Form(...),
    status: str = Form("ACTIVE"),
    ai_prompt: Optional[str] = Form(None),
    settings: Optional[str] = Form(None),
    files: List[UploadFile] = File(None),
    project_document: Optional[UploadFile] = File(None),
    homepage_popup_banner: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    existing = db.query(CommunityService).filter(CommunityService.short_name.ilike(short_name), CommunityService.status != 'DELETED').first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Short Name '{short_name}' is already taken.")
    try:
        verticals_list = json.loads(applicable_verticals)
    except Exception:
        verticals_list = [applicable_verticals]

    try:
        settings_dict = json.loads(settings) if settings else {}
    except Exception:
        settings_dict = {}

    service = CommunityService(
        service_name=service_name,
        short_name=short_name,
        description=description,
        start_date=datetime.strptime(start_date, "%Y-%m-%d").date(),
        end_date=datetime.strptime(end_date, "%Y-%m-%d").date(),
        applicable_verticals=verticals_list,
        status=status,
        banner_images=[],
        ai_prompt=ai_prompt,
        settings=settings_dict,
        created_at=get_indian_time(),
        updated_at=get_indian_time()
    )
    db.add(service)
    db.commit()
    db.refresh(service)

    banner_paths = []
    if files:
        for file in files:
            try:
                upload_res = await UniversalUploadService.handle_upload(
                    file=file,
                    table_name="community_services",
                    record_id=service.id,
                    uploaded_by_id=current_user.id,
                    uploaded_by_type="staff",
                    storage_dir="community_banners",
                    db=db
                )
                if upload_res.get("file_path"):
                    banner_paths.append(upload_res["file_path"])
            except Exception as e:
                print(f"Banner upload error: {e}")

    doc_text = ""
    if project_document and project_document.filename:
        try:
            doc_text = extract_text_from_file(project_document)
            settings_dict['extracted_doc_text'] = doc_text
            await UniversalUploadService.handle_upload(
                file=project_document,
                table_name="community_services",
                record_id=service.id,
                uploaded_by_id=current_user.id,
                uploaded_by_type="staff",
                storage_dir="community_documents",
                db=db
            )
        except Exception as de:
            print(f"Doc upload error: {de}")

    if homepage_popup_banner and homepage_popup_banner.filename:
        try:
            popup_upload_res = await UniversalUploadService.handle_upload(
                file=homepage_popup_banner,
                table_name="community_services",
                record_id=service.id,
                uploaded_by_id=current_user.id,
                uploaded_by_type="staff",
                storage_dir="community_popup_banners",
                db=db
            )
            if popup_upload_res.get("file_path"):
                settings_dict['homepage_popup_image'] = popup_upload_res["file_path"]
        except Exception as e:
            print(f"Popup banner upload error: {e}")

    service.settings = settings_dict
    db.commit()

    # Regenerate page description with banners, prompt, and settings
    input_text = doc_text or ai_prompt or ""
    if input_text.strip() or banner_paths or settings_dict:
        if not input_text.strip():
            input_text = service_name
        service.description = generate_community_seva_landing_page(
            input_text, service_name, short_name, ai_prompt, banner_paths, settings=settings_dict
        )
        service.banner_images = banner_paths
        db.commit()
        db.refresh(service)

    return {"success": True, "message": "Community Service created successfully!", "data": service.to_dict()}


@router.put("/admin/services/{service_id}")
async def edit_service_admin(
    service_id: int,
    service_name: str = Form(...),
    short_name: str = Form(...),
    description: Optional[str] = Form(None),
    start_date: str = Form(...),
    end_date: str = Form(...),
    applicable_verticals: str = Form(...),
    status: str = Form(...),
    existing_banners: Optional[str] = Form(None),
    ai_prompt: Optional[str] = Form(None),
    settings: Optional[str] = Form(None),
    files: List[UploadFile] = File(None),
    project_document: Optional[UploadFile] = File(None),
    homepage_popup_banner: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    service = db.query(CommunityService).filter(CommunityService.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    dup = db.query(CommunityService).filter(
        CommunityService.short_name.ilike(short_name),
        CommunityService.id != service_id,
        CommunityService.status != 'DELETED'
    ).first()
    if dup:
        raise HTTPException(status_code=400, detail=f"Short Name '{short_name}' is already taken.")
    try:
        verticals_list = json.loads(applicable_verticals)
    except Exception:
        verticals_list = [applicable_verticals]
    try:
        banner_list = json.loads(existing_banners) if existing_banners else []
    except Exception:
        banner_list = service.banner_images or []

    try:
        settings_dict = json.loads(settings) if settings else {}
    except Exception:
        settings_dict = {}

    # If new files are uploaded, process them first
    if files:
        for file in files:
            try:
                upload_res = await UniversalUploadService.handle_upload(
                    file=file,
                    table_name="community_services",
                    record_id=service.id,
                    uploaded_by_id=current_user.id,
                    uploaded_by_type="staff",
                    storage_dir="community_banners",
                    db=db
                )
                if upload_res.get("file_path"):
                    banner_list.append(upload_res["file_path"])
            except Exception as e:
                print(f"Banner upload error: {e}")

    doc_text = ""
    if project_document and project_document.filename:
        try:
            doc_text = extract_text_from_file(project_document)
            settings_dict['extracted_doc_text'] = doc_text
            await UniversalUploadService.handle_upload(
                file=project_document,
                table_name="community_services",
                record_id=service.id,
                uploaded_by_id=current_user.id,
                uploaded_by_type="staff",
                storage_dir="community_documents",
                db=db
            )
        except Exception as de:
            print(f"Doc upload error: {de}")
    else:
        # Fall back to previously extracted document text if present and preserve it in settings_dict
        existing_doc_text = service.settings.get('extracted_doc_text') if service.settings else None
        if existing_doc_text:
            doc_text = existing_doc_text
            settings_dict['extracted_doc_text'] = existing_doc_text

    # Preserve existing homepage popup image if not overwritten by a new upload
    if service.settings and 'homepage_popup_image' in service.settings and 'homepage_popup_image' not in settings_dict:
        settings_dict['homepage_popup_image'] = service.settings['homepage_popup_image']

    if homepage_popup_banner and homepage_popup_banner.filename:
        try:
            popup_upload_res = await UniversalUploadService.handle_upload(
                file=homepage_popup_banner,
                table_name="community_services",
                record_id=service.id,
                uploaded_by_id=current_user.id,
                uploaded_by_type="staff",
                storage_dir="community_popup_banners",
                db=db
            )
            if popup_upload_res.get("file_path"):
                settings_dict['homepage_popup_image'] = popup_upload_res["file_path"]
        except Exception as e:
            print(f"Popup banner upload error: {e}")

    service.service_name = service_name
    service.short_name = short_name
    service.start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    service.end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    service.applicable_verticals = verticals_list
    service.status = status
    service.ai_prompt = ai_prompt
    service.settings = settings_dict
    service.banner_images = banner_list
    service.updated_at = get_indian_time()

    # Regenerate page description with prompt, existing/new banners, and settings
    input_text = doc_text or ai_prompt or ""
    if not input_text.strip():
        input_text = service_name
    service.description = generate_community_seva_landing_page(
        input_text, service_name, short_name, ai_prompt, banner_list, settings=settings_dict
    )

    db.commit()
    db.refresh(service)
    invalidate_community_services_cache()
    return {"success": True, "message": "Service updated successfully!", "data": service.to_dict()}


@router.post("/admin/services/{service_id}/status")
def update_service_status(
    service_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    service = db.query(CommunityService).filter(CommunityService.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    status_val = payload.get("status", "ACTIVE").upper()
    if status_val not in ["ACTIVE", "PAUSED"]:
        raise HTTPException(status_code=400, detail="Invalid status value")
    service.status = status_val
    service.updated_at = get_indian_time()
    db.commit()
    invalidate_community_services_cache()
    return {"success": True, "message": f"Service status updated to {status_val}"}

@router.delete("/admin/services/{service_id}")
def delete_service_admin(service_id: int, db: Session = Depends(get_db), current_user: StaffEmployee = Depends(get_current_staff_user)):
    """
    Soft-delete community service.
    """
    service = db.query(CommunityService).filter(CommunityService.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    service.status = 'DELETED'
    service.updated_at = get_indian_time()
    db.commit()
    invalidate_community_services_cache()
    return {"success": True, "message": "Service deleted successfully"}

@router.get("/admin/registrations")
def list_registrations_admin(db: Session = Depends(get_db), current_user: StaffEmployee = Depends(get_current_staff_user)):
    """
    List registered community records with associated service details.
    """
    regs = db.query(CommunityRegistration).order_by(desc(CommunityRegistration.created_at)).all()
    results = []
    for r in regs:
        d = r.to_dict()
        d['kyc_documents'] = r.kyc_uploads or []
        d['service_name'] = r.service.service_name if r.service else 'Unknown'
        
        # Initialize defaults from relationship
        ref1_name = r.ref1_member.partner_name if r.ref1_member else None
        ref1_code = r.ref1_member.partner_code if r.ref1_member else None
        
        # Resolve staff/influencer names if not resolved yet
        if not ref1_name and r.referral_type and r.referral_code:
            if r.referral_type == 'staff':
                from app.models.staff import StaffEmployee
                emp = db.query(StaffEmployee).filter(StaffEmployee.emp_code == r.referral_code).first()
                if emp:
                    ref1_name = emp.full_name
                    ref1_code = emp.emp_code
            elif r.referral_type == 'influencer':
                from app.models.promo import PromoInfluencer
                inf = db.query(PromoInfluencer).filter(PromoInfluencer.referral_code == r.referral_code).first()
                if inf:
                    ref1_name = inf.name
                    ref1_code = inf.referral_code
            elif r.referral_type == 'vgk_member':
                partner = db.query(OfficialPartner).filter(OfficialPartner.partner_code == r.referral_code).first()
                if partner:
                    ref1_name = partner.partner_name
                    ref1_code = partner.partner_code
                    
        d['ref1_name'] = ref1_name
        d['ref1_code'] = ref1_code or r.referral_code
        d['ref2_name'] = r.ref2_member.partner_name if r.ref2_member else None
        d['ref2_code'] = r.ref2_member.partner_code if r.ref2_member else None
        d['user_partner_code'] = r.user_partner.partner_code if r.user_partner else None
        results.append(d)
    return {"success": True, "data": results}


@router.post("/admin/registrations/{reg_id}/approve")
def approve_registration_endpoint(reg_id: int, db: Session = Depends(get_db), current_user: StaffEmployee = Depends(get_current_staff_user)):
    """
    Approve community service registration and auto-generate portal credentials.
    """
    reg = db.query(CommunityRegistration).filter(CommunityRegistration.id == reg_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg.status != 'PENDING':
        raise HTTPException(status_code=400, detail=f"Cannot approve registration with status: {reg.status}")

    # Check if partner already exists
    import random
    import string
    from app.core.security import SecurityManager
    from app.api.v1.endpoints.vgk_team import _next_vgk_partner_code

    partner = None
    if reg.user_id:
        partner = db.query(OfficialPartner).filter(OfficialPartner.id == reg.user_id).first()

    from app.utils.phone_otp import normalize_phone_10
    clean_phone = normalize_phone_10(reg.primary_phone_1) or (reg.primary_phone_1 or '').strip()

    if not partner and clean_phone:
        partner = db.query(OfficialPartner).filter(
            OfficialPartner.category == 'VGK_TEAM',
            or_(
                OfficialPartner.phone == clean_phone,
                OfficialPartner.phone == (reg.primary_phone_1 or '').strip()
            )
        ).first()
        if partner:
            reg.user_id = partner.id

    raw_password = "".join(random.choices(string.ascii_letters + string.digits, k=8))
    password_hash = SecurityManager.get_password_hash(raw_password)

    VGK_DEFAULT_ROOT = 'VGK07102207'
    default_root = db.query(OfficialPartner).filter(
        OfficialPartner.partner_code == VGK_DEFAULT_ROOT,
        OfficialPartner.category == 'VGK_TEAM'
    ).first()
    default_root_id = default_root.id if default_root else None

    parent_id = reg.ref1_member_id if reg.referral_type == 'vgk_member' and reg.ref1_member_id else default_root_id
    reg_by = reg.referral_code.strip().upper() if reg.referral_type == 'staff' and reg.referral_code else VGK_DEFAULT_ROOT

    if partner:
        # Activate and refresh password
        partner.is_active = True
        partner.password_hash = password_hash
        partner_code = partner.partner_code
        if not partner.parent_partner_id:
            partner.parent_partner_id = parent_id
        if not partner.registered_by_emp_code:
            partner.registered_by_emp_code = reg_by
        if clean_phone and partner.phone != clean_phone:
            partner.phone = clean_phone
        db.commit()
    else:
        # Create new partner (fallback)
        company_id = 1
        partner_code = _next_vgk_partner_code(db, company_id)
        
        partner = OfficialPartner(
            company_id=company_id,
            partner_code=partner_code,
            partner_name=reg.primary_name,
            phone=clean_phone,
            email=None,
            category='VGK_TEAM',
            is_active=True,
            vgk_role='COMMUNITY',
            parent_partner_id=parent_id,
            registered_by_emp_code=reg_by,
            vgk_points_balance=Decimal('0'),
            password_hash=password_hash,
            created_at=get_indian_time(),
            updated_at=get_indian_time()
        )
        db.add(partner)
        db.commit()
        db.refresh(partner)
        reg.user_id = partner.id

    reg.status = 'APPROVED'
    reg.updated_at = get_indian_time()
    db.commit()
    invalidate_community_services_cache()
    
    # WhatsApp welcome credentials
    try:
        from app.services.whatsapp_auto_service import send_auto_whatsapp
        send_auto_whatsapp(
            db=db,
            event_key="community_approved",
            phone=reg.primary_phone_1,
            context={
                "1": reg.primary_name,
                "2": partner_code,
                "3": raw_password,
                "4": "https://www.vgk4u.com/vgk/login"
            }
        )
    except Exception as wa_e:
        print(f"WhatsApp credentials trigger failed: {wa_e}")
        
    return {
        "success": True,
        "message": "Registration approved and credentials generated successfully!",
        "credentials": {
            "partner_code": partner_code,
            "raw_password": raw_password,
            "phone": reg.primary_phone_1
        }
    }

@router.post("/admin/registrations/{reg_id}/reject")
def reject_registration_endpoint(reg_id: int, db: Session = Depends(get_db), current_user: StaffEmployee = Depends(get_current_staff_user)):
    """
    Reject community service registration.
    """
    reg = db.query(CommunityRegistration).filter(CommunityRegistration.id == reg_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg.status != 'PENDING':
        raise HTTPException(status_code=400, detail=f"Cannot reject registration with status: {reg.status}")
    reg.status = 'REJECTED'
    reg.updated_at = get_indian_time()
    db.commit()
    return {"success": True, "message": "Registration rejected successfully"}

@router.put("/admin/registrations/{reg_id}")
def update_registration_fields(
    reg_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Update registration fields.
    """
    reg = db.query(CommunityRegistration).filter(CommunityRegistration.id == reg_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
        
    for k, v in payload.items():
        if hasattr(reg, k):
            setattr(reg, k, v)

    # Sync referral details to the associated OfficialPartner if approved/login exists
    if reg.user_id:
        partner = db.query(OfficialPartner).filter(OfficialPartner.id == reg.user_id).first()
        if partner:
            ref_type = payload.get('referral_type', reg.referral_type)
            ref_code = payload.get('referral_code', reg.referral_code)
            ref1_id = payload.get('ref1_member_id', reg.ref1_member_id)
            if ref_type == 'vgk_member':
                partner.parent_partner_id = ref1_id
                partner.registered_by_emp_code = None
            elif ref_type in ('staff', 'influencer'):
                partner.parent_partner_id = None
                partner.registered_by_emp_code = ref_code
            else:
                partner.parent_partner_id = None
                partner.registered_by_emp_code = None

    reg.updated_at = get_indian_time()
    db.commit()
    db.refresh(reg)
    return {"success": True, "message": "Registration fields updated successfully"}

@router.get("/admin/active-search")
def search_active_communities(q: str = "", db: Session = Depends(get_db), current_user: StaffEmployee = Depends(get_current_staff_user)):
    """
    Real-time typeahead searching (filters and displays active approved Community Registrations).
    """
    query = q.strip()
    if not query:
        return {"results": []}
    regs = db.query(CommunityRegistration).join(CommunityService).outerjoin(
        OfficialPartner, CommunityRegistration.user_id == OfficialPartner.id
    ).filter(
        CommunityRegistration.status == 'APPROVED',
        or_(
            CommunityRegistration.association_name.ilike(f"%{query}%"),
            CommunityRegistration.primary_name.ilike(f"%{query}%"),
            CommunityRegistration.area.ilike(f"%{query}%"),
            CommunityRegistration.district.ilike(f"%{query}%"),
            CommunityService.service_name.ilike(f"%{query}%"),
            CommunityService.short_name.ilike(f"%{query}%"),
            OfficialPartner.partner_code.ilike(f"%{query}%"),
            CommunityRegistration.id == int(query) if query.isdigit() else False
        )
    ).limit(15).all()
    
    return {
        "results": [
            {
                "id": r.id,
                "display": f"{r.association_name or 'N/A'} - {r.primary_name} ({r.service.short_name} - {r.area}) [{r.user_partner.partner_code if r.user_partner else 'No Login'}]"
            } for r in regs
        ]
    }


# ──────────────────────────────────────────────────────────────────────
# 3. MEMBER PORTAL COMMUNITY DASHBOARD
# ──────────────────────────────────────────────────────────────────────

@router.get("/my-earnings")
def get_community_member_earnings(
    db: Session = Depends(get_db),
    partner: OfficialPartner = Depends(get_current_vgk_member)
):
    """
    Get community earnings and tagged leads for the logged-in community partner.
    """
    # Find registration linked to this partner
    reg = db.query(CommunityRegistration).filter(CommunityRegistration.user_id == partner.id).first()
    if not reg:
        return {
            "success": False,
            "message": "This partner account is not associated with any Community Registration.",
            "total_seva_earned": 0,
            "commissions": [],
            "leads": []
        }
        
    # Get all released commissions
    comms = db.query(CommunityCommission).filter(
        CommunityCommission.community_id == reg.id
    ).order_by(desc(CommunityCommission.created_at)).all()
    
    total_earned = sum(c.amount for c in comms)
    
    # Fetch tagged leads
    leads = db.query(CRMLead).filter(
        CRMLead.community_id == reg.id
    ).order_by(desc(CRMLead.created_at)).all()
    
    return {
        "success": True,
        "community_name": reg.primary_name,
        "service_name": reg.service.service_name if reg.service else 'Unknown',
        "total_seva_earned": float(total_earned),
        "commissions": [
            {
                "id": c.id,
                "lead_id": c.lead_id,
                "lead_name": db.query(CRMLead.name).filter(CRMLead.id == c.lead_id).scalar() or 'N/A',
                "amount": float(c.amount),
                "status": c.status,
                "payout_date": c.payout_date.isoformat() if c.payout_date else None,
                "created_at": c.created_at.isoformat()
            } for c in comms
        ],
        "leads": [
            {
                "id": l.id,
                "customer_name": l.name,
                "phone": l.phone,
                "status": l.status,
                "created_at": l.created_at.isoformat() if l.created_at else None
            } for l in leads
        ]
    }

@router.get("/member/my-earnings")
def get_community_partner_earnings(
    db: Session = Depends(get_db),
    partner: OfficialPartner = Depends(get_current_vgk_member)
):
    return get_community_member_earnings(db, partner)

@router.post("/admin/registrations/{reg_id}/reset-password")
def reset_registration_password_endpoint(
    reg_id: int, 
    db: Session = Depends(get_db), 
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Reset a community registration's login credentials password back to their username (partner code).
    """
    from app.core.security import SecurityManager
    reg = db.query(CommunityRegistration).filter(CommunityRegistration.id == reg_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if not reg.user_id:
        raise HTTPException(status_code=400, detail="Registration does not have a linked partner account.")
        
    partner = db.query(OfficialPartner).filter(OfficialPartner.id == reg.user_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Linked partner account not found")
        
    # Reset password to their partner_code (username)
    default_password = partner.partner_code
    partner.password_hash = SecurityManager.get_password_hash(default_password)
    partner.updated_at = get_indian_time()
    db.commit()
    
    return {
        "success": True,
        "message": "Password successfully reset to default (partner code)",
        "credentials": {
            "partner_code": partner.partner_code,
            "raw_password": default_password,
            "phone": partner.phone or reg.primary_phone_1
        }
    }



