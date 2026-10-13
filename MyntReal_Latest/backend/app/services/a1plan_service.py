"""
A1PlanAPI Integration Service (https://a1planapi.com)
Provides live telecom HLR intelligence and recharge plan services:
1. Operator & Circle Fetch: Auto-resolves mobile number to operator and circle code.
2. R-Offer Check: Live HLR subscriber-specific special cashback and tariff offers.
3. Plan Fetch: Live categorized prepaid recharge plans (Recommended, Daily, Unlimited, Roaming).
Includes smart in-memory caching to avoid depleting paid plan query wallet balances.
"""
import logging
import time
import re
from typing import Dict, Any, List, Optional, Tuple
import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

# Operator Code Mappings
# A1PlanAPI: A (Airtel), RC (Jio), V (Vodafone), I (Idea), BT (BSNL Topup), BR (BSNL Recharge)
UI_TO_A1_OPERATOR: Dict[str, str] = {
    "airtel": "A",
    "jio": "RC",
    "reliance": "RC",
    "reliance - jio": "RC",
    "vi": "V",
    "vodafone": "V",
    "idea": "V",
    "bsnl": "BT",
    "bsnl - topup": "BT",
    "bsnl - special": "BR"
}

A1_TO_UI_OPERATOR: Dict[str, str] = {
    "A": "Airtel",
    "RC": "Jio",
    "V": "VI",
    "I": "VI",
    "BT": "BSNL",
    "BR": "BSNL"
}

# Standard Circle Codes from A1PlanAPI (Defaults to 49: Andhra Pradesh & Telangana)
DEFAULT_CIRCLE_CODE = "49"
DEFAULT_CIRCLE_NAME = "Andhra Pradesh"

# In-memory caches to protect wallet hits: (timestamp, data)
_plans_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_roffer_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_operator_circle_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}


def get_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Resolve A1PlanAPI username and password from environment settings."""
    user = getattr(settings, "A1PLANAPI_USERNAME", None) or getattr(settings, "A1TOPUP_USERNAME", None)
    pwd = getattr(settings, "A1PLANAPI_PASSWORD", None) or getattr(settings, "A1TOPUP_PASSWORD", None)
    return user, pwd


def normalize_operator_code(op: str) -> str:
    """Normalize operator string (name or code) to A1PlanAPI operator code."""
    if not op:
        return "A"
    clean = op.strip().lower()
    if clean in UI_TO_A1_OPERATOR:
        return UI_TO_A1_OPERATOR[clean]
    # Check if already a valid A1 code
    up = op.strip().upper()
    if up in ["A", "RC", "V", "I", "BT", "BR"]:
        return up
    # Fallback search
    for k, v in UI_TO_A1_OPERATOR.items():
        if k in clean:
            return v
    return "A"


def operator_code_to_ui(op_code: str) -> str:
    """Convert A1PlanAPI operator code to UI brand label."""
    if not op_code:
        return "Airtel"
    return A1_TO_UI_OPERATOR.get(op_code.strip().upper(), "Airtel")


def extract_data_benefit(desc: str) -> str:
    """Extract a clean data benefit string from a plan description."""
    if not desc:
        return "Voice & Data"
    # Look for patterns like "1.5GB/day", "2GB/day", "1GB/Day", "25GB", "Unlimited"
    m = re.search(r"(\d+(\.\d+)?\s*(GB|MB)\s*(/\s*day)?)", desc, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    if "unlimited" in desc.lower():
        return "Unlimited Calls"
    return "Data Pack"


# ── 1. OPERATOR & CIRCLE FETCH ─────────────────────────────────────────

def operator_circle_fetch(mobile: str) -> Dict[str, Any]:
    """
    Resolves a mobile number to its current operator and telecom circle.
    Endpoint: https://a1planapi.com/planapi/operatorCircleFetch
    """
    clean_mobile = re.sub(r"\D", "", mobile or "")
    if len(clean_mobile) == 12 and clean_mobile.startswith("91"):
        clean_mobile = clean_mobile[2:]
    if len(clean_mobile) != 10:
        return {
            "success": False,
            "error": "Invalid mobile number. Must be 10 digits.",
            "mobile": clean_mobile
        }

    # Check cache (24 hours TTL)
    now = time.time()
    cache_key = clean_mobile
    if cache_key in _operator_circle_cache:
        cached_time, cached_data = _operator_circle_cache[cache_key]
        if now - cached_time < 86400:
            return cached_data

    username, pwd = get_credentials()
    if not username or not pwd:
        # Fallback heuristic if credentials are not configured yet
        return _fallback_operator_circle(clean_mobile)

    base_url = getattr(settings, "A1PLANAPI_BASE_URL", "https://a1planapi.com/planapi")
    req_url = f"{base_url}/operatorCircleFetch"
    params = {
        "username": username,
        "pwd": pwd,
        "mobileno": clean_mobile
    }

    try:
        resp = requests.get(req_url, params=params, timeout=10)
        data = resp.json()
        logger.info(f"operatorCircleFetch for {clean_mobile}: {data}")

        # Success response check: ERROR="0"
        if str(data.get("ERROR", "")) == "0":
            op_code = data.get("OpCode", "A")
            res = {
                "success": True,
                "mobile": data.get("Mobile", clean_mobile),
                "operator": data.get("Operator", "AIRTEL"),
                "ui_operator": operator_code_to_ui(op_code),
                "operator_code": op_code,
                "circle": data.get("Circle", DEFAULT_CIRCLE_NAME),
                "circle_code": str(data.get("CircleCode", DEFAULT_CIRCLE_CODE)),
                "message": data.get("Message", "Successfully")
            }
            _operator_circle_cache[cache_key] = (now, res)
            return res
        else:
            err_msg = data.get("Message") or "Failed to resolve operator"
            logger.warning(f"operatorCircleFetch error: {err_msg}")
            # If authentication failure or error, fall back to prefix heuristic
            fallback = _fallback_operator_circle(clean_mobile)
            fallback["warning"] = f"A1PlanAPI: {err_msg}"
            return fallback

    except Exception as e:
        logger.error(f"operatorCircleFetch exception: {e}")
        return _fallback_operator_circle(clean_mobile)


def _fallback_operator_circle(clean_mobile: str) -> Dict[str, Any]:
    """Smart prefix-based fallback when external API is unreachable or auth is pending."""
    first_two = clean_mobile[:2]
    # General Indian mobile allocation heuristic:
    if first_two in ["98", "99", "97", "96", "81", "88", "85"]:
        op_ui = "Airtel"
        op_code = "A"
    elif first_two in ["70", "79", "62", "63", "89", "78"]:
        op_ui = "Jio"
        op_code = "RC"
    elif first_two in ["90", "91", "92", "93", "94"]:
        op_ui = "BSNL"
        op_code = "BT"
    else:
        op_ui = "VI"
        op_code = "V"

    return {
        "success": True,
        "is_fallback": True,
        "mobile": clean_mobile,
        "operator": op_ui.upper(),
        "ui_operator": op_ui,
        "operator_code": op_code,
        "circle": DEFAULT_CIRCLE_NAME,
        "circle_code": DEFAULT_CIRCLE_CODE,
        "message": "Auto-detected"
    }


# ── 2. R-OFFER CHECK ───────────────────────────────────────────────────

def roffer_check(mobile: str, operator_code: Optional[str] = None) -> Dict[str, Any]:
    """
    Checks subscriber-specific special offers (roffers) for a mobile number against live HLR data.
    Endpoint: https://a1planapi.com/planapi/rofferCheck
    """
    clean_mobile = re.sub(r"\D", "", mobile or "")
    if len(clean_mobile) == 12 and clean_mobile.startswith("91"):
        clean_mobile = clean_mobile[2:]
    if len(clean_mobile) != 10:
        return {
            "success": False,
            "error": "Invalid mobile number. Must be 10 digits.",
            "offers": []
        }

    # Auto-resolve operator code if not provided
    if not operator_code:
        op_res = operator_circle_fetch(clean_mobile)
        operator_code = op_res.get("operator_code", "A")
    else:
        operator_code = normalize_operator_code(operator_code)

    # Check cache (15 mins TTL)
    now = time.time()
    cache_key = f"{clean_mobile}_{operator_code}"
    if cache_key in _roffer_cache:
        cached_time, cached_data = _roffer_cache[cache_key]
        if now - cached_time < 900:
            return cached_data

    username, pwd = get_credentials()
    if not username or not pwd:
        return {
            "success": False,
            "error": "A1PlanAPI credentials not configured in settings.",
            "offers": []
        }

    base_url = getattr(settings, "A1PLANAPI_BASE_URL", "https://a1planapi.com/planapi")
    req_url = f"{base_url}/rofferCheck"
    params = {
        "username": username,
        "pwd": pwd,
        "operatorcode": operator_code,
        "mobileno": clean_mobile
    }

    try:
        resp = requests.get(req_url, params=params, timeout=12)
        data = resp.json()
        logger.info(f"rofferCheck for {clean_mobile} ({operator_code}): {data}")

        if str(data.get("ERROR", "")) == "0":
            raw_offers = data.get("RDATA", [])
            formatted_offers = []
            if isinstance(raw_offers, list):
                for item in raw_offers:
                    try:
                        price_val = float(item.get("price", 0))
                        desc_val = item.get("ofrtext", "")
                        formatted_offers.append({
                            "id": f"roffer_{int(price_val)}",
                            "price": price_val,
                            "amount": price_val,
                            "description": desc_val,
                            "ofrtext": desc_val,
                            "validity": "Exclusive HLR Offer",
                            "data_benefit": extract_data_benefit(desc_val),
                            "category": "Exclusive R-Offer",
                            "is_roffer": True
                        })
                    except Exception:
                        continue

            res = {
                "success": True,
                "mobile": data.get("MOBILENO", clean_mobile),
                "operator_code": operator_code,
                "ui_operator": operator_code_to_ui(operator_code),
                "message": data.get("MESSAGE", "Offers retrieved"),
                "offers": formatted_offers
            }
            _roffer_cache[cache_key] = (now, res)
            return res
        else:
            return {
                "success": False,
                "error": data.get("MESSAGE") or "No special offers found for this number.",
                "offers": []
            }

    except Exception as e:
        logger.error(f"rofferCheck exception: {e}")
        return {
            "success": False,
            "error": f"Error reaching R-Offer gateway: {str(e)}",
            "offers": []
        }


# ── 3. LIVE PLAN FETCH ────────────────────────────────────────────────

def plan_fetch(operator_code: str, circle_code: str = DEFAULT_CIRCLE_CODE) -> Dict[str, Any]:
    """
    Returns live prepaid recharge plans for an operator and circle.
    Endpoint: https://a1planapi.com/planapi/planFetch
    Cached in memory based on settings.A1PLANAPI_CACHE_TTL_MINUTES to avoid draining paid API hits.
    """
    op_code = normalize_operator_code(operator_code)
    c_code = str(circle_code or DEFAULT_CIRCLE_CODE).strip()

    # Check cache
    now = time.time()
    cache_ttl = getattr(settings, "A1PLANAPI_CACHE_TTL_MINUTES", 120) * 60
    cache_key = f"{op_code}_{c_code}"
    if cache_key in _plans_cache:
        cached_time, cached_data = _plans_cache[cache_key]
        if now - cached_time < cache_ttl:
            return cached_data

    username, pwd = get_credentials()
    if not username or not pwd:
        return {
            "success": False,
            "error": "A1PlanAPI credentials not configured in settings.",
            "categories": {},
            "plans": []
        }

    base_url = getattr(settings, "A1PLANAPI_BASE_URL", "https://a1planapi.com/planapi")
    req_url = f"{base_url}/planFetch"
    params = {
        "username": username,
        "pwd": pwd,
        "operatorcode": op_code,
        "circle": c_code
    }

    try:
        resp = requests.get(req_url, params=params, timeout=15)
        data = resp.json()
        logger.info(f"planFetch for {op_code} circle {c_code}: Status={resp.status_code}")

        # Check success: ERROR="0"
        if str(data.get("ERROR", "")) == "0":
            rdata = data.get("RDATA", {})
            categories_out = {}
            flat_plans = []

            if isinstance(rdata, dict):
                for cat_name, plan_list in rdata.items():
                    cat_plans = []
                    if isinstance(plan_list, list):
                        for p_idx, item in enumerate(plan_list):
                            if not isinstance(item, dict):
                                continue
                            rs_val = float(item.get("rs", 0))
                            validity_val = str(item.get("validity", "Standard")).strip()
                            desc_val = str(item.get("desc", "")).strip()

                            plan_obj = {
                                "id": f"a1_{op_code}_{c_code}_{int(rs_val)}_{p_idx}",
                                "amount": rs_val,
                                "price": rs_val,
                                "validity": validity_val,
                                "description": desc_val,
                                "data_benefit": extract_data_benefit(desc_val),
                                "category": cat_name,
                                "operator": data.get("Operator", operator_code_to_ui(op_code)),
                                "circle": data.get("Circle", DEFAULT_CIRCLE_NAME)
                            }
                            cat_plans.append(plan_obj)
                            flat_plans.append(plan_obj)

                    categories_out[cat_name] = cat_plans

            res = {
                "success": True,
                "operator": data.get("Operator", operator_code_to_ui(op_code)),
                "circle": data.get("Circle", DEFAULT_CIRCLE_NAME),
                "operator_code": op_code,
                "circle_code": c_code,
                "categories": categories_out,
                "plans": flat_plans,
                "total_plans": len(flat_plans)
            }
            _plans_cache[cache_key] = (now, res)
            return res
        else:
            return {
                "success": False,
                "error": data.get("MESSAGE") or "Failed to fetch operator plans.",
                "categories": {},
                "plans": []
            }

    except Exception as e:
        logger.error(f"planFetch exception: {e}")
        return {
            "success": False,
            "error": f"Error reaching plan gateway: {str(e)}",
            "categories": {},
            "plans": []
        }
