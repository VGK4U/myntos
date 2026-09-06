"""
Facebook Lead Ads Integration Service — Multi-Page Production Edition
DC Protocol Mar 2026: Multi-Page, Database-Driven Multi-Tenant Form Routing, Fail-Closed Security,
Complete Cursor Pagination, Exponential Backoff & Database Idempotency.

Features:
- Multi-page support: stores per-page tokens in facebook_pages DB table (AES-256-GCM)
- Database-driven form-to-tenant routing (meta_form_mappings table) — 100% extensible without code changes
- Webhook verification & Fail-Closed HMAC-SHA256 signature validation
- Lead fetch from Graph API v24.0 using per-page tokens with retry/backoff
- Complete cursor pagination for historical pull/backfill
- DB-enforced duplicate prevention via indexed MetaLeadsAttribution.meta_lead_id
- Bulk page sync + subscription from User Token
"""

import os
import json
import time
import random
import hmac
import hashlib
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List
import pytz
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)
GRAPH_API_VERSION = "v24.0"


def get_indian_time():
    indian_tz = pytz.timezone('Asia/Kolkata')
    return datetime.now(indian_tz).replace(tzinfo=None)


# ── Error Classification ──────────────────────────────────────────────────────
class MetaErrorCategory:
    AUTHENTICATION = "AUTHENTICATION"
    AUTHORIZATION  = "AUTHORIZATION"
    RATE_LIMIT     = "RATE_LIMIT"
    TRANSIENT      = "TRANSIENT"
    PERMANENT      = "PERMANENT"
    VALIDATION     = "VALIDATION"
    DUPLICATE      = "DUPLICATE"
    DATABASE       = "DATABASE"
    CONFIGURATION  = "CONFIGURATION"


def classify_meta_error(status_code: int, error_data: Dict[str, Any]) -> str:
    """Classify Meta Graph API errors into standardized operational categories."""
    code = error_data.get("code")
    subcode = error_data.get("error_subcode")
    msg = (error_data.get("message") or "").lower()

    if status_code in (401, 403) or code in (190, 102, 104) or "token" in msg or "permission" in msg:
        return MetaErrorCategory.AUTHORIZATION if status_code == 403 else MetaErrorCategory.AUTHENTICATION
    if status_code == 429 or code in (4, 17, 32, 613):
        return MetaErrorCategory.RATE_LIMIT
    if status_code in (500, 502, 503, 504) or code in (1, 2):
        return MetaErrorCategory.TRANSIENT
    if code in (100, 10):
        return MetaErrorCategory.VALIDATION
    return MetaErrorCategory.PERMANENT


# ── Auto-detect CRM segment from FB page category / page name ─────────────────
CATEGORY_SEGMENT_MAP = [
    (['property', 'real estate', 'realty', 'real dream', 'realdream'], 'REAL_ESTATE'),
    (['electric vehicle', 'ev ', 'e-vehicle', 'e-bikes', 'ebike', 'electrical bike',
      'evs hub', 'ev spares', 'ev dealership', 'new vehicles', 'motorcycle',
      'motor cycle', 'bike zone', 'e-bikes', 'royalev', 'mantra ev'], 'EV_SPARES'),
    (['solar', 'renewable', 'har ghar solar', 'energy'], 'SOLAR'),
    (['insurance'], 'INSURANCE'),
]


def detect_segment(category: str, page_name: str) -> str:
    combined = f"{(category or '').lower()} {(page_name or '').lower()}"
    for keywords, segment in CATEGORY_SEGMENT_MAP:
        for kw in keywords:
            if kw in combined:
                return segment
    return 'GENERAL'


class FacebookLeadsService:
    """
    Multi-page Facebook Lead Ads service.
    DC Protocol: Credentials from env vars; page tokens stored in facebook_pages DB table.
    """

    def __init__(self):
        self.app_secret    = os.getenv('FACEBOOK_APP_SECRET')
        self.verify_token  = os.getenv('FACEBOOK_WEBHOOK_VERIFY_TOKEN', 'myntreal_fb_leads_2026')
        self.api_version   = GRAPH_API_VERSION
        self._legacy_token = os.getenv('FACEBOOK_PAGE_ACCESS_TOKEN')

    def is_configured(self) -> bool:
        return bool(self.app_secret)

    # ── Webhook security (Fail-Closed) ─────────────────────────────────────────

    def verify_webhook_token(self, mode: str, token: str) -> bool:
        return mode == 'subscribe' and token == self.verify_token

    def verify_webhook_signature(self, payload: bytes, signature_header: Optional[str]) -> bool:
        """
        Fail-closed HMAC-SHA256 signature verification.
        Returns True only if secret is present and signature matches in constant time.
        """
        if not self.app_secret:
            logger.error("[SECURITY] Meta Webhook Rejected: FACEBOOK_APP_SECRET is not configured on server.")
            return False
        if not signature_header or not signature_header.startswith("sha256="):
            logger.warning("[SECURITY] Meta Webhook Rejected: Missing or malformed X-Hub-Signature-256 header.")
            return False
        try:
            expected_hash = hmac.new(
                self.app_secret.encode('utf-8'), payload, hashlib.sha256
            ).hexdigest()
            sig = signature_header.split("sha256=")[1].strip()
            return hmac.compare_digest(expected_hash, sig)
        except Exception as e:
            logger.error(f"[SECURITY] Webhook signature verification error: {e}")
            return False

    # ── Per-page token & segment lookup from DB ────────────────────────────────

    def get_page_token(self, page_id: str, db: Optional[Session] = None) -> Optional[str]:
        if db and page_id:
            try:
                from app.core.security_encryption import decrypt_credential_safe
                row = db.execute(
                    text("SELECT access_token FROM facebook_pages WHERE page_id = :pid AND is_active = TRUE"),
                    {'pid': str(page_id)}
                ).fetchone()
                if row and row[0]:
                    return decrypt_credential_safe(row[0])
            except Exception as e:
                logger.warning(f"DB token lookup failed for page {page_id}: {e}")
        return self._legacy_token

    def get_page_info(self, page_id: str, db: Optional[Session] = None) -> Dict[str, Any]:
        """Returns {'token': ..., 'segment': ..., 'name': ..., 'company_id': ...} for a page."""
        info = {'token': self._legacy_token or '', 'segment': 'GENERAL', 'name': '', 'company_id': None}
        if db and page_id:
            try:
                from app.core.security_encryption import decrypt_credential_safe
                row = db.execute(
                    text("SELECT access_token, crm_segment, page_name, company_id FROM facebook_pages WHERE page_id = :pid AND is_active = TRUE"),
                    {'pid': str(page_id)}
                ).fetchone()
                if row:
                    raw_token = row[0] or info['token']
                    info['token']      = decrypt_credential_safe(raw_token) if raw_token else ''
                    info['segment']    = row[1] or 'GENERAL'
                    info['name']       = row[2] or ''
                    info['page_name']  = row[2] or ''
                    info['company_id'] = row[3]
            except Exception as e:
                logger.warning(f"Page info lookup failed for page {page_id}: {e}")
        return info

    # ── Database-Driven Form Routing Lookup ───────────────────────────────────

    def get_form_routing(
        self,
        form_id: Optional[str],
        page_id: Optional[str] = None,
        db: Optional[Session] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Dynamically resolves form-to-tenant routing from the database table `meta_form_mappings`.
        Enables adding new forms via database configuration with zero code modification.
        """
        if db and form_id:
            try:
                row = db.execute(text("""
                    SELECT company_id, category_id, crm_segment, segment_tag, looking_for, is_active
                    FROM meta_form_mappings
                    WHERE form_id = :fid AND is_active = TRUE
                """), {'fid': str(form_id)}).fetchone()
                if row:
                    return {
                        'company_id': row[0],
                        'category_id': row[1],
                        'crm_segment': row[2] or 'GENERAL',
                        'segment_tag': row[3] or 'facebook_lead',
                        'looking_for': row[4],
                        'is_active': row[5]
                    }
            except Exception as e:
                logger.warning(f"Error querying meta_form_mappings for form {form_id}: {e}")

        # Fallback to page-level configuration in facebook_pages
        if db and page_id:
            try:
                p_row = db.execute(text("""
                    SELECT company_id, crm_segment, page_name
                    FROM facebook_pages
                    WHERE page_id = :pid AND is_active = TRUE
                """), {'pid': str(page_id)}).fetchone()
                if p_row and p_row[0]:
                    return {
                        'company_id': p_row[0],
                        'category_id': None,
                        'crm_segment': p_row[1] or 'GENERAL',
                        'segment_tag': 'facebook_lead',
                        'looking_for': None,
                        'is_active': True
                    }
            except Exception as pe:
                logger.warning(f"Error querying facebook_pages for page {page_id}: {pe}")

        return None

    def register_or_update_form_mapping(
        self,
        db: Session,
        page_id: str,
        form_id: str,
        company_id: int,
        category_id: Optional[int] = None,
        form_name: Optional[str] = None,
        crm_segment: str = 'GENERAL',
        segment_tag: Optional[str] = None,
        looking_for: Optional[str] = None,
        is_active: bool = True
    ) -> Dict[str, Any]:
        """
        Persistently register or update a Meta Form routing mapping in PostgreSQL.
        """
        db.execute(text("""
            INSERT INTO meta_form_mappings
                (page_id, form_id, form_name, company_id, category_id, crm_segment, segment_tag, looking_for, is_active, updated_at)
            VALUES
                (:pid, :fid, :fname, :cid, :catid, :seg, :tag, :look, :act, NOW())
            ON CONFLICT (form_id) DO UPDATE SET
                page_id = EXCLUDED.page_id,
                form_name = EXCLUDED.form_name,
                company_id = EXCLUDED.company_id,
                category_id = EXCLUDED.category_id,
                crm_segment = EXCLUDED.crm_segment,
                segment_tag = EXCLUDED.segment_tag,
                looking_for = EXCLUDED.looking_for,
                is_active = EXCLUDED.is_active,
                updated_at = NOW()
        """), {
            'pid': str(page_id),
            'fid': str(form_id),
            'fname': form_name,
            'cid': company_id,
            'catid': category_id,
            'seg': crm_segment,
            'tag': segment_tag,
            'look': looking_for,
            'act': is_active
        })
        db.commit()
        return {
            'success': True,
            'page_id': str(page_id),
            'form_id': str(form_id),
            'company_id': company_id,
            'category_id': category_id,
            'crm_segment': crm_segment,
            'segment_tag': segment_tag
        }

    # ── Duplicate check ───────────────────────────────────────────────────────

    def lead_already_exists(self, fb_lead_id: str, db: Session) -> bool:
        """
        Check if this Facebook lead_id was already imported into CRM.
        DC Protocol: Queries indexed MetaLeadsAttribution first (O(1)), then fallback.
        """
        if not fb_lead_id:
            return False
        try:
            from app.models.meta_attribution import MetaLeadsAttribution
            att = db.query(MetaLeadsAttribution.id).filter(
                MetaLeadsAttribution.meta_lead_id == str(fb_lead_id)
            ).first()
            if att:
                return True

            row = db.execute(
                text("SELECT id FROM crm_leads WHERE source IN ('Online - M', 'Facebook Lead Ads', 'Social Media') AND source_details LIKE :pattern LIMIT 1"),
                {'pattern': f"%'lead_id': '{fb_lead_id}'%"}
            ).fetchone()
            return row is not None
        except Exception as e:
            logger.warning(f"Error checking lead existence for {fb_lead_id}: {e}")
            return False

    # ── Graph API Execution with Retry / Backoff ──────────────────────────────

    def _execute_graph_api_request(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        timeout: int = 15,
        max_retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Execute Graph API request with exponential backoff & jitter for transient errors.
        """
        attempt = 0
        while attempt < max_retries:
            try:
                if method.upper() == "POST":
                    resp = requests.post(url, data=data, params=params, timeout=timeout)
                else:
                    resp = requests.get(url, params=params, timeout=timeout)

                if resp.status_code == 200:
                    return resp.json()

                error_json = {}
                try:
                    error_json = resp.json().get('error', {})
                except Exception:
                    pass

                category = classify_meta_error(resp.status_code, error_json)
                logger.warning(
                    f"Meta Graph API error [{category}] status={resp.status_code}: {error_json.get('message') or resp.text[:200]}"
                )

                if category in (MetaErrorCategory.TRANSIENT, MetaErrorCategory.RATE_LIMIT) and attempt < max_retries - 1:
                    sleep_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                    logger.info(f"Retrying Meta Graph API request in {sleep_time:.2f}s (attempt {attempt+1}/{max_retries})...")
                    time.sleep(sleep_time)
                    attempt += 1
                    continue
                else:
                    return None

            except requests.exceptions.RequestException as req_err:
                logger.warning(f"Network error calling Meta Graph API: {req_err}")
                if attempt < max_retries - 1:
                    sleep_time = (2 ** attempt) + random.uniform(0.5, 1.0)
                    time.sleep(sleep_time)
                    attempt += 1
                    continue
                return None

        return None

    # ── Graph API calls ────────────────────────────────────────────────────────

    def fetch_lead_data(self, lead_id: str, access_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        token = access_token or self._legacy_token
        if not token:
            logger.error(f"No access token available to fetch lead {lead_id}")
            return None
        url = f"https://graph.facebook.com/{self.api_version}/{lead_id}"
        params = {
            'access_token': token,
            'fields': 'id,created_time,field_data,form_id,page_id,ad_id,adset_id,campaign_id'
        }
        return self._execute_graph_api_request(url, params=params, timeout=15)

    def fetch_form_leads(self, form_id: str, access_token: str, max_leads: int = 500) -> List[Dict]:
        """
        Fetch leads from a specific form with complete cursor pagination (paging.next).
        """
        all_leads: List[Dict] = []
        url = f"https://graph.facebook.com/{self.api_version}/{form_id}/leads"
        params: Optional[Dict[str, Any]] = {
            'access_token': access_token,
            'fields': 'id,created_time,field_data,form_id,page_id,ad_id,adset_id,campaign_id',
            'limit': 100
        }

        page_count = 0
        max_safety_pages = 50

        while url and len(all_leads) < max_leads and page_count < max_safety_pages:
            data = self._execute_graph_api_request(url, params=params, timeout=20)
            if not data:
                break

            items = data.get('data', [])
            all_leads.extend(items)

            if len(all_leads) >= max_leads:
                all_leads = all_leads[:max_leads]
                break

            # Follow cursor pagination
            paging = data.get('paging', {})
            next_url = paging.get('next')
            if next_url:
                url = next_url
                params = None  # next URL includes query params
                page_count += 1
            else:
                break

        logger.info(f"Fetched {len(all_leads)} leads for form {form_id} across {page_count+1} pages.")
        return all_leads

    def subscribe_page_to_webhook(self, page_id: str, page_token: str) -> Dict[str, Any]:
        """Subscribe a page to receive leadgen webhook events."""
        url = f"https://graph.facebook.com/{self.api_version}/{page_id}/subscribed_apps"
        resp = self._execute_graph_api_request(
            url,
            method="POST",
            data={
                'access_token': page_token,
                'subscribed_fields': 'leadgen'
            },
            timeout=15
        )
        if resp and resp.get('success'):
            return {'success': True}
        return {'success': False, 'error': str(resp.get('error', resp)) if resp else 'Unknown error'}

    # ── Bulk page sync from User Token ─────────────────────────────────────────

    def sync_pages_from_user_token(self, user_token: str, db: Session, company_id: int = 1) -> Dict[str, Any]:
        """
        Fetch all pages the user manages, store tokens in DB, subscribe each to leadgen.
        DC Protocol Mar 2026: Call this when a new User Token is generated.
        Safe to re-run — uses UPSERT, won't create duplicates.
        """
        url = f"https://graph.facebook.com/{self.api_version}/me/accounts"
        params: Dict[str, Any] = {'access_token': user_token, 'fields': 'id,name,access_token,category', 'limit': 100}
        pages = []
        
        # Follow cursor pagination for pages
        page_iter = 0
        while url and page_iter < 10:
            data = self._execute_graph_api_request(url, params=params, timeout=20)
            if not data:
                break
            pages.extend(data.get('data', []))
            paging = data.get('paging', {})
            next_url = paging.get('next')
            if next_url:
                url = next_url
                params = None
                page_iter += 1
            else:
                break

        # Also attempt direct page token fetch for known active pages if missing from me/accounts
        existing_pids = set(p.get('id') for p in pages)
        known_pids = ['894208310452980', '1081963148335244', '1005465332641372', '1019684831223211', '442395068958730']
        for kpid in known_pids:
            if kpid not in existing_pids:
                dp_url = f"https://graph.facebook.com/{self.api_version}/{kpid}"
                dp_params = {'fields': 'id,name,access_token,category', 'access_token': user_token}
                dp_data = self._execute_graph_api_request(dp_url, params=dp_params, timeout=10)
                if dp_data and dp_data.get('access_token'):
                    pages.append(dp_data)

        results = {'total': len(pages), 'stored': 0, 'subscribed': 0, 'failed_subscription': [], 'errors': []}

        for p in pages:
            pid    = p.get('id', '')
            pname  = p.get('name', '')
            pcat   = p.get('category', '')
            ptoken = p.get('access_token', '')
            seg    = detect_segment(pcat, pname)

            if not pid or not ptoken:
                continue

            from app.core.security_encryption import encrypt_credential
            enc_ptoken = encrypt_credential(ptoken)

            # Preserve existing company_id if already configured in DB
            target_cid = company_id
            existing_row = db.execute(
                text("SELECT company_id FROM facebook_pages WHERE page_id = :pid"),
                {'pid': pid}
            ).fetchone()
            if existing_row and existing_row[0]:
                target_cid = existing_row[0]

            # Upsert into facebook_pages
            try:
                db.execute(text("""
                    INSERT INTO facebook_pages
                        (company_id, page_id, page_name, page_category, access_token,
                         crm_segment, is_active, leads_subscribed, updated_at)
                    VALUES (:cid, :pid, :pname, :pcat, :ptoken, :seg, TRUE, FALSE, NOW())
                    ON CONFLICT (page_id) DO UPDATE SET
                        page_name     = EXCLUDED.page_name,
                        page_category = EXCLUDED.page_category,
                        access_token  = EXCLUDED.access_token,
                        crm_segment   = EXCLUDED.crm_segment,
                        updated_at    = NOW()
                """), {'cid': target_cid, 'pid': pid, 'pname': pname,
                       'pcat': pcat, 'ptoken': enc_ptoken, 'seg': seg})
                db.commit()
                results['stored'] += 1
            except Exception as e:
                db.rollback()
                results['errors'].append(f"Store [{pname}]: {e}")
                continue

            # Subscribe to leadgen webhook
            sub = self.subscribe_page_to_webhook(pid, ptoken)
            if sub.get('success'):
                try:
                    db.execute(text(
                        "UPDATE facebook_pages SET leads_subscribed=TRUE, subscription_error=NULL WHERE page_id=:pid"
                    ), {'pid': pid})
                    db.commit()
                    results['subscribed'] += 1
                except Exception:
                    db.rollback()
            else:
                err = sub.get('error', 'unknown')[:300]
                try:
                    db.execute(text(
                        "UPDATE facebook_pages SET leads_subscribed=FALSE, subscription_error=:err WHERE page_id=:pid"
                    ), {'pid': pid, 'err': err})
                    db.commit()
                except Exception:
                    db.rollback()
                results['failed_subscription'].append({'page': pname, 'error': err})

        results['success'] = True
        return results

    # ── CRM lead field mapping ─────────────────────────────────────────────────

    def parse_lead_fields(self, lead_data: Dict) -> Dict[str, str]:
        field_map = {}
        for field in lead_data.get('field_data', []):
            name   = field.get('name', '').lower().strip()
            values = field.get('values', [])
            field_map[name] = values[0] if values else ''
        return field_map

    def map_to_crm_lead(self, lead_data: Dict, company_id: Optional[int] = None,
                        category_id: Optional[int] = None,
                        page_segment: str = 'GENERAL',
                        page_name: str = '',
                        form_id: Optional[str] = None,
                        page_id: Optional[str] = None,
                        db: Optional[Session] = None) -> Optional[Dict[str, Any]]:

        fields = self.parse_lead_fields(lead_data)

        name = (fields.get('full_name') or fields.get('name') or
                f"{fields.get('first_name', '')} {fields.get('last_name', '')}".strip()
                or 'Facebook Lead')
        email   = fields.get('email') or None
        phone   = fields.get('phone_number') or fields.get('phone') or None
        city    = fields.get('city') or fields.get('location') or None
        state   = fields.get('state') or None
        pincode = fields.get('post_code') or fields.get('zip_code') or fields.get('pincode') or None
        looking = (fields.get('looking_for') or fields.get('interest') or
                   fields.get('enquiry_type') or None)
        req     = (fields.get('requirements') or fields.get('message') or
                   fields.get('comments') or None)
        budget  = fields.get('budget') or fields.get('budget_range') or None

        # Auto-resolve State and City from 6-digit Pincode/ZIP code via India Post Lookup
        if pincode:
            clean_pin = str(pincode).strip().replace(" ", "")[:6]
            if clean_pin.isdigit() and len(clean_pin) == 6:
                pincode = clean_pin
                try:
                    from app.services.staff_accounts_service import PinCodeLookupService
                    pin_info = PinCodeLookupService.lookup_pincode(clean_pin)
                    if pin_info:
                        if not city or str(city).lower() in ['', 'none', 'null', 'not specified']:
                            city = pin_info.get('city') or pin_info.get('district') or pin_info.get('division')
                        if not state or str(state).lower() in ['', 'none', 'null', 'not specified']:
                            state = pin_info.get('state')
                except Exception as _pin_err:
                    logger.warning(f"Pincode lookup error for {pincode}: {_pin_err}")

        # Parse Meta created_time to IST datetime
        meta_created_str = lead_data.get('created_time')
        meta_created_dt = None
        if meta_created_str:
            try:
                dt_utc = datetime.fromisoformat(meta_created_str.replace('+0000', '+00:00'))
                indian_tz = pytz.timezone('Asia/Kolkata')
                meta_created_dt = dt_utc.astimezone(indian_tz).replace(tzinfo=None)
            except Exception as dt_err:
                logger.warning(f"Could not parse Meta created_time {meta_created_str}: {dt_err}")

        # Capture Facebook form extra fields & questions
        electricity_bill = (
            fields.get('what_is_your_monthly_electricity_bill?') or
            fields.get('electricity_bill') or
            fields.get('monthly_electricity_bill') or
            fields.get('bill_amount') or None
        )
        property_type = (
            fields.get('type_of_property') or
            fields.get('property_type') or None
        )
        investment_capacity = (
            fields.get('what_is_your_investment_capacity') or
            fields.get('investment_capacity') or
            fields.get('investment_range') or
            fields.get('investment capacity') or None
        )
        planning_start = (
            fields.get('when_are_you_planning_to_start') or
            fields.get('planning_start') or
            fields.get('planned_start') or None
        )
        full_time_business = (
            fields.get('are_you_planning_this_as_a_full-time_business') or
            fields.get('full_time_business') or
            fields.get('business_type') or None
        )

        _known_fb_keys = {
            'full_name', 'name', 'first_name', 'last_name',
            'email', 'phone_number', 'phone', 'city', 'location', 'state', 'post_code', 'zip_code', 'pincode',
            'looking_for', 'interest', 'enquiry_type',
            'requirements', 'message', 'comments',
            'budget', 'budget_range',
            'what_is_your_monthly_electricity_bill?', 'electricity_bill', 'monthly_electricity_bill', 'bill_amount',
            'type_of_property', 'property_type',
            'what_is_your_investment_capacity', 'investment_capacity',
            'investment_range', 'investment capacity',
            'when_are_you_planning_to_start', 'planning_start', 'planned_start',
            'are_you_planning_this_as_a_full-time_business', 'full_time_business',
            'business_type', 'phone_number_verified'
        }
        _extra_fields = {k: v for k, v in fields.items()
                         if k not in _known_fb_keys and v}

        resolved_form_id = form_id or lead_data.get('form_id')
        resolved_page_id = page_id or lead_data.get('page_id')

        source_details = {
            'lead_id':      lead_data.get('id'),
            'form_id':      resolved_form_id,
            'page_id':      resolved_page_id,
            'page_name':    page_name,
            'page_segment': page_segment,
            'ad_id':        lead_data.get('ad_id'),
            'adset_id':     lead_data.get('adset_id'),
            'campaign_id':  lead_data.get('campaign_id'),
            'created_time': meta_created_str,
            'raw_fields':   fields,
        }

        desc_parts = [f"Facebook Lead — {page_name}" if page_name else "Online - M Lead"]
        if electricity_bill:     desc_parts.append(f"Monthly Electricity Bill: {electricity_bill}")
        if property_type:        desc_parts.append(f"Property Type: {property_type}")
        if looking:              desc_parts.append(f"Looking for: {looking}")
        if req:                  desc_parts.append(f"Message: {req}")
        if budget:               desc_parts.append(f"Budget: {budget}")
        if investment_capacity:  desc_parts.append(f"Investment Capacity: {investment_capacity}")
        if planning_start:       desc_parts.append(f"Planning to Start: {planning_start}")
        if full_time_business:   desc_parts.append(f"Full-Time Business: {full_time_business}")
        for _k, _v in _extra_fields.items():
            if _v:
                _lbl = _k.replace('_', ' ').replace('-', ' ').title()
                desc_parts.append(f"{_lbl}: {_v}")

        seg_tag = {
            'REAL_ESTATE': 'real_estate',
            'EV_SPARES':   'ev_spares',
            'SOLAR':       'solar',
        }.get(page_segment, 'facebook_lead')

        # ── Deterministic Tenant Routing Resolution ───────────────────────────
        target_company_id = None
        target_category_id = category_id

        # 1. Check persistent database-driven registry (meta_form_mappings)
        db_routing = self.get_form_routing(resolved_form_id, page_id=resolved_page_id, db=db)
        if db_routing:
            target_company_id = db_routing['company_id']
            if db_routing.get('category_id'):
                target_category_id = db_routing['category_id']
            if db_routing.get('segment_tag'):
                seg_tag = db_routing['segment_tag']
            if db_routing.get('looking_for') and not looking:
                looking = db_routing['looking_for']
            logger.info(f"[ROUTING-DB-REGISTRY] Form {resolved_form_id} routed to company {target_company_id} (Category: {target_category_id})")
        elif company_id is not None and int(company_id) > 0:
            # 2. Known page with explicitly configured company_id
            target_company_id = int(company_id)
            logger.info(f"[ROUTING-PAGE-DEFAULT] Form {resolved_form_id} routed to page default company {target_company_id}")
        else:
            # 3. Unmapped form and unmapped page -> STRICT REJECTION (Zero cross-tenant contamination)
            logger.warning(
                f"[META-ROUTING-REJECT] Ingestion rejected: Unrecognized/unmapped Meta Form {resolved_form_id} "
                f"from unknown/unmapped Page {resolved_page_id}. No global fallback permitted."
            )
            return None

        if not target_company_id or target_company_id <= 0:
            logger.warning(f"[META-WEBHOOK-REJECT] Lead dropped: Invalid company_id={target_company_id}")
            return None

        crm = {
            'company_id':          target_company_id,
            'category_id':         target_category_id,
            'name':                name[:200],
            'email':               email[:200] if email else None,
            'phone':               phone[:20]  if phone else None,
            'source':              'Social Media',
            'source_details':      json.dumps(source_details)[:1000],
            'status':              'new',
            'priority':            'high',
            'handler_type':        'unassigned',
            'city':                city[:100]  if city  else None,
            'state':               state[:100] if state else None,
            'pincode':             pincode[:20] if pincode else None,
            'description':         '\n'.join(desc_parts)[:2000],
            'looking_for':         looking[:500]             if looking else None,
            'requirements':        req[:1000]                if req    else None,
            'investment_capacity': investment_capacity[:100] if investment_capacity else None,
            'tags':                seg_tag,
            'created_by_type':     'system',
            'created_by_id':       'facebook_webhook',
        }
        if meta_created_dt:
            crm['created_at'] = meta_created_dt
            crm['updated_at'] = meta_created_dt
        if target_category_id:
            crm['category_id'] = target_category_id
        return crm


facebook_leads_service = FacebookLeadsService()
