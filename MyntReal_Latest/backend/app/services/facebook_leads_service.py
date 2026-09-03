"""
Facebook Lead Ads Integration Service — Multi-Page Edition
DC Protocol Mar 2026: All pages, all forms, all leads → CRM automatically

Features:
- Multi-page support: stores per-page tokens in facebook_pages DB table
- Auto segment mapping from page category and page name
- Webhook verification & HMAC signature validation
- Lead fetch from Graph API using correct per-page token
- Duplicate prevention via Facebook lead_id
- Bulk page sync + subscription from a User Token
"""

import os
import json
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

    # ── Webhook security ───────────────────────────────────────────────────────

    def verify_webhook_token(self, mode: str, token: str) -> bool:
        return mode == 'subscribe' and token == self.verify_token

    def verify_webhook_signature(self, payload: bytes, signature_header: str) -> bool:
        if not signature_header or not self.app_secret:
            return False
        try:
            expected = hmac.new(
                self.app_secret.encode('utf-8'), payload, hashlib.sha256
            ).hexdigest()
            sig = signature_header.replace('sha256=', '')
            return hmac.compare_digest(expected, sig)
        except Exception as e:
            logger.error(f"Signature verify error: {e}")
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
                logger.warning(f"DB token lookup failed: {e}")
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
                logger.warning(f"Page info lookup failed: {e}")
        return info

    # ── Duplicate check ───────────────────────────────────────────────────────

    def lead_already_exists(self, fb_lead_id: str, db: Session) -> bool:
        """
        Check if this Facebook lead_id was already imported into CRM.
        DC Protocol: Prevents duplicates on webhook retries or backfill reruns.
        """
        try:
            row = db.execute(
                text("SELECT id FROM crm_leads WHERE source IN ('Online - M', 'Facebook Lead Ads') AND source_details LIKE :pattern LIMIT 1"),
                {'pattern': f"%'lead_id': '{fb_lead_id}'%"}
            ).fetchone()
            return row is not None
        except Exception:
            return False

    # ── Graph API calls ────────────────────────────────────────────────────────

    def fetch_lead_data(self, lead_id: str, access_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        token = access_token or self._legacy_token
        if not token:
            logger.error("No access token available to fetch lead")
            return None
        url = f"https://graph.facebook.com/{self.api_version}/{lead_id}"
        params = {
            'access_token': token,
            'fields': 'id,created_time,field_data,form_id,page_id,ad_id,adset_id,campaign_id'
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Fetch lead {lead_id} failed: {e}")
            return None

    def fetch_form_leads(self, form_id: str, access_token: str, limit: int = 100) -> List[Dict]:
        """Fetch historical leads from a specific form (for backfill)."""
        url = f"https://graph.facebook.com/{self.api_version}/{form_id}/leads"
        params = {
            'access_token': access_token,
            'fields': 'id,created_time,field_data,form_id,page_id,ad_id,adset_id,campaign_id',
            'limit': min(limit, 100)
        }
        try:
            resp = requests.get(url, params=params, timeout=20)
            resp.raise_for_status()
            return resp.json().get('data', [])
        except Exception as e:
            logger.error(f"Fetch form leads {form_id} failed: {e}")
            return []

    def subscribe_page_to_webhook(self, page_id: str, page_token: str) -> Dict[str, Any]:
        """Subscribe a page to receive leadgen webhook events."""
        url = f"https://graph.facebook.com/{self.api_version}/{page_id}/subscribed_apps"
        try:
            resp = requests.post(url, data={
                'access_token': page_token,
                'subscribed_fields': 'leadgen'
            }, timeout=15)
            data = resp.json()
            if data.get('success'):
                return {'success': True}
            return {'success': False, 'error': str(data.get('error', data))}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ── Bulk page sync from User Token ─────────────────────────────────────────

    def sync_pages_from_user_token(self, user_token: str, db: Session, company_id: int = 1) -> Dict[str, Any]:
        """
        Fetch all pages the user manages, store tokens in DB, subscribe each to leadgen.
        DC Protocol Mar 2026: Call this when a new User Token is generated.
        Safe to re-run — uses UPSERT, won't create duplicates.
        """
        url = f"https://graph.facebook.com/{self.api_version}/me/accounts"
        params = {'access_token': user_token, 'fields': 'id,name,access_token,category', 'limit': 200}
        pages = []
        try:
            resp = requests.get(url, params=params, timeout=20)
            if resp.status_code == 200:
                pages = resp.json().get('data', [])
        except Exception as e:
            logger.warning(f"me/accounts fetch error: {e}")

        # Also attempt direct page token fetch for active pages (e.g. Har Ghar Solar 894208310452980)
        existing_pids = set(p.get('id') for p in pages)
        known_pids = ['894208310452980', '1081963148335244', '1005465332641372', '1019684831223211']
        for kpid in known_pids:
            if kpid not in existing_pids:
                try:
                    dp_url = f"https://graph.facebook.com/{self.api_version}/{kpid}?fields=id,name,access_token,category&access_token={user_token}"
                    dp_resp = requests.get(dp_url, timeout=10)
                    if dp_resp.status_code == 200:
                        dp_data = dp_resp.json()
                        if dp_data.get('access_token'):
                            pages.append(dp_data)
                except Exception as ex:
                    logger.warning(f"Direct page token fetch for {kpid} failed: {ex}")

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
                """), {'cid': company_id, 'pid': pid, 'pname': pname,
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

    def map_to_crm_lead(self, lead_data: Dict, company_id: int,
                        category_id: Optional[int] = None,
                        page_segment: str = 'GENERAL',
                        page_name: str = '') -> Dict[str, Any]:

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

        source_details = {
            'lead_id':      lead_data.get('id'),
            'form_id':      lead_data.get('form_id'),
            'page_id':      lead_data.get('page_id'),
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

        # Multi-Tenant Strict Resolution: Never fallback to default company 4
        if not company_id:
            logger.warning(f"[META-WEBHOOK-REJECT] Lead dropped: No valid company_id resolved for page_id={source_details.get('page_id')}")
            return None

        target_company_id = company_id
        target_category_id = category_id

        # Detect ETC / EV Career & Trading Leads and Route to Zynovia Company (Company ID 2)
        ad_name = str(lead_data.get('ad_name') or '')
        form_name = str(lead_data.get('form_name') or page_name or '')
        campaign_name = str(lead_data.get('campaign_name') or '')
        all_text = f"{form_name} {ad_name} {campaign_name} {looking or ''} {req or ''}".lower()

        if any(k in all_text for k in ['etc', 'ev career', 'career & trading', 'training', 'zynova', 'zynovia']):
            target_company_id = 2  # Zynova Mobility Pvt Ltd (Zynovia)
            looking = looking or 'ETC Training'
            target_category_id = 16  # ETC Training
            seg_tag = 'etc_training'

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
        if category_id:
            crm['category_id'] = category_id
        return crm


facebook_leads_service = FacebookLeadsService()
