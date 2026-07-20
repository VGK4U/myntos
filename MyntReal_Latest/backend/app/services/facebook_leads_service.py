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
                row = db.execute(
                    text("SELECT access_token FROM facebook_pages WHERE page_id = :pid AND is_active = TRUE"),
                    {'pid': str(page_id)}
                ).fetchone()
                if row:
                    return row[0]
            except Exception as e:
                logger.warning(f"DB token lookup failed: {e}")
        return self._legacy_token

    def get_page_info(self, page_id: str, db: Optional[Session] = None) -> Dict[str, str]:
        """Returns {'token': ..., 'segment': ..., 'name': ...} for a page."""
        info = {'token': self._legacy_token or '', 'segment': 'GENERAL', 'name': ''}
        if db and page_id:
            try:
                row = db.execute(
                    text("SELECT access_token, crm_segment, page_name FROM facebook_pages WHERE page_id = :pid"),
                    {'pid': str(page_id)}
                ).fetchone()
                if row:
                    info['token']   = row[0] or info['token']
                    info['segment'] = row[1] or 'GENERAL'
                    info['name']    = row[2] or ''
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
        try:
            resp = requests.get(url, params=params, timeout=20)
            resp.raise_for_status()
            pages = resp.json().get('data', [])
        except Exception as e:
            return {'success': False, 'error': f"Could not fetch pages: {e}"}

        results = {'total': len(pages), 'stored': 0, 'subscribed': 0, 'failed_subscription': [], 'errors': []}

        for p in pages:
            pid    = p.get('id', '')
            pname  = p.get('name', '')
            pcat   = p.get('category', '')
            ptoken = p.get('access_token', '')
            seg    = detect_segment(pcat, pname)

            if not pid or not ptoken:
                continue

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
                       'pcat': pcat, 'ptoken': ptoken, 'seg': seg})
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
        looking = (fields.get('looking_for') or fields.get('interest') or
                   fields.get('enquiry_type') or None)
        req     = (fields.get('requirements') or fields.get('message') or
                   fields.get('comments') or None)
        budget  = fields.get('budget') or fields.get('budget_range') or None

        # DC Protocol Apr 2026: Capture Facebook form extra fields
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

        # Keys already extracted above — everything else is an "unknown" field
        _known_fb_keys = {
            'full_name', 'name', 'first_name', 'last_name',
            'email', 'phone_number', 'phone', 'city', 'location', 'state',
            'looking_for', 'interest', 'enquiry_type',
            'requirements', 'message', 'comments',
            'budget', 'budget_range',
            'what_is_your_investment_capacity', 'investment_capacity',
            'investment_range', 'investment capacity',
            'when_are_you_planning_to_start', 'planning_start', 'planned_start',
            'are_you_planning_this_as_a_full-time_business', 'full_time_business',
            'business_type',
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
            'created_time': lead_data.get('created_time'),
        }

        desc_parts = [f"Facebook Lead — {page_name}" if page_name else "Online - M Lead"]
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

        crm = {
            'company_id':          company_id,
            'name':                name[:200],
            'email':               email[:200] if email else None,
            'phone':               phone[:20]  if phone else None,
            'source':              'Online - M',
            'source_details':      str(source_details)[:1000],
            'status':              'new',
            'priority':            'high',
            'handler_type':        'unassigned',
            'city':                city[:100]  if city  else None,
            'state':               state[:100] if state else None,
            'description':         '\n'.join(desc_parts)[:2000],
            'looking_for':         looking[:500]             if looking else None,
            'requirements':        req[:1000]                if req    else None,
            'investment_capacity': investment_capacity[:100] if investment_capacity else None,
            'tags':                seg_tag,
            'created_by_type':     'system',
            'created_by_id':       'facebook_webhook',
        }
        if category_id:
            crm['category_id'] = category_id
        return crm


facebook_leads_service = FacebookLeadsService()
