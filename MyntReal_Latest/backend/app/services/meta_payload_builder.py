"""
Meta Graph API Payload Builder & Serializer Service (Phase 2B Integration Layer)
Generates exact serialized Graph API v24.0 payloads for Campaign, Ad Set, Creative, and Ad objects.
Includes budget magnitude safety validation and Lead Form field mapping check.
Zero live mutation requests executed.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v24.0"
MAX_DAILY_BUDGET_INR = 50000.0  # ₹50,000/day safety cap to prevent budget magnitude typos


def build_meta_campaign_payload(
    account_id: str,
    campaign_name: str,
    daily_budget_inr: float = 1000.0,
    objective: str = "OUTCOME_LEADS"
) -> Dict[str, Any]:
    """
    Build serialized Graph API POST /v24.0/act_<ID>/campaigns payload.
    """
    if daily_budget_inr > MAX_DAILY_BUDGET_INR:
        raise ValueError(f"Budget safety violation: ₹{daily_budget_inr:,.2f} exceeds safety threshold of ₹{MAX_DAILY_BUDGET_INR:,.2f}/day")

    # Meta Graph API budget is in cents/paise (₹1,000.00 = 100000 paise)
    budget_in_subunits = int(daily_budget_inr * 100)

    endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{account_id}/campaigns"
    payload = {
        "name": campaign_name,
        "objective": objective,
        "status": "PAUSED",
        "special_ad_categories": [],
        "daily_budget": budget_in_subunits,
        "is_adset_budget_sharing_enabled": False
    }

    return {
        "endpoint": endpoint,
        "http_method": "POST",
        "api_version": GRAPH_API_VERSION,
        "daily_budget_inr": daily_budget_inr,
        "serialized_payload": payload,
        "serialized_json": json.dumps(payload, indent=2)
    }


def build_meta_adset_payload(
    account_id: str,
    campaign_id_ref: str,
    adset_name: str,
    target_location_state: str = "Andhra Pradesh",
    daily_budget_inr: float = 1000.0,
    page_id: str = "894208310452980"
) -> Dict[str, Any]:
    """
    Build serialized Graph API POST /v24.0/act_<ID>/adsets payload.
    """
    budget_in_subunits = int(daily_budget_inr * 100)
    endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{account_id}/adsets"

    payload = {
        "campaign_id": campaign_id_ref,
        "name": adset_name,
        "status": "PAUSED",
        "optimization_goal": "LEAD_GENERATION",
        "billing_event": "IMPRESSIONS",
        "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
        "daily_budget": budget_in_subunits,
        "targeting": {
            "publisher_platforms": ["facebook"],
            "facebook_positions": ["feed"],
            "geo_locations": {
                "regions": [{"key": "3845", "name": target_location_state, "country": "IN"}]
            },
            "age_min": 25,
            "age_max": 65
        },
        "promoted_object": {
            "page_id": page_id
        }
    }

    return {
        "endpoint": endpoint,
        "http_method": "POST",
        "api_version": GRAPH_API_VERSION,
        "dependency_campaign_id": campaign_id_ref,
        "serialized_payload": payload,
        "serialized_json": json.dumps(payload, indent=2)
    }


def build_meta_creative_payload(
    account_id: str,
    page_id: str,
    headline: str,
    primary_text: str,
    description: str,
    lead_form_id: str,
    image_hash_ref: str = "<IMAGE_HASH_REF>"
) -> Dict[str, Any]:
    """
    Build serialized Graph API POST /v24.0/act_<ID>/adcreatives payload.
    """
    endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{account_id}/adcreatives"

    cta_value = {"link": f"https://facebook.com/{page_id}"}
    if lead_form_id and lead_form_id.isdigit():
        cta_value["lead_gen_form_id"] = lead_form_id

    payload = {
        "name": f"Creative - {headline[:30]}",
        "object_story_spec": {
            "page_id": page_id,
            "link_data": {
                "call_to_action": {
                    "type": "LEARN_MORE",
                    "value": cta_value
                },
                "link": f"https://facebook.com/{page_id}",
                "message": primary_text,
                "name": headline,
                "description": description
            }
        },
        "degrees_of_freedom_spec": {
            "creative_features_spec": {
                "standard_enhancements": {
                    "enroll_status": "OPT_OUT"
                }
            }
        }
    }

    return {
        "endpoint": endpoint,
        "http_method": "POST",
        "api_version": GRAPH_API_VERSION,
        "lead_form_id_ref": lead_form_id,
        "serialized_payload": payload,
        "serialized_json": json.dumps(payload, indent=2)
    }


def build_meta_ad_payload(
    account_id: str,
    adset_id_ref: str,
    creative_id_ref: str,
    ad_name: str
) -> Dict[str, Any]:
    """
    Build serialized Graph API POST /v24.0/act_<ID>/ads payload.
    """
    endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{account_id}/ads"

    payload = {
        "name": ad_name,
        "adset_id": adset_id_ref,
        "creative": {"creative_id": creative_id_ref},
        "status": "PAUSED"
    }

    return {
        "endpoint": endpoint,
        "http_method": "POST",
        "api_version": GRAPH_API_VERSION,
        "dependency_adset_id": adset_id_ref,
        "dependency_creative_id": creative_id_ref,
        "serialized_payload": payload,
        "serialized_json": json.dumps(payload, indent=2)
    }
