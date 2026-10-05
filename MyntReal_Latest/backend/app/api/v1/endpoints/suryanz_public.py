"""
Suryanz Solar - Public Lead Capture & Solar Knowledge API
DC Protocol (Oct 2026):
- Serves public requests for suryanz.com & suryanzsolar.com
- Handles server-validated lead ingestion into crm_leads (source='SURYANZ_SOLAR_WEBSITE', category_id=6)
- Idempotency & retry durability protection
- Interactive Solar Calculator estimation helper endpoint
- Public brand knowledge & FAQ endpoint for AI Search engines (ChatGPT/Gemini/Perplexity)
"""

import logging
import re
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Body, status
from sqlalchemy.orm import Session
from sqlalchemy import text, or_

from app.core.database import get_db
from app.models.crm import CRMLead
from app.utils.phone_otp import normalize_phone_10
from app.utils.name_formatter import format_proper_name

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_primary_solar_company_id(db: Session) -> int:
    """
    Dynamically resolve the primary company ID for solar leads.
    Fallback to Company ID 1 if associated_companies lookup is not found.
    """
    try:
        row = db.execute(text("SELECT id FROM associated_companies WHERE is_active=true ORDER BY id ASC LIMIT 1")).fetchone()
        if row:
            return row[0]
    except Exception as e:
        logger.warning(f"[SURYANZ-API] Company lookup warning: {e}")
    return 1


@router.post("/lead", summary="Submit Suryanz Solar Public Lead")
def capture_suryanz_lead(
    payload: Dict[str, Any] = Body(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Public lead capture endpoint for SURYANZ SOLAR.
    Validates form data, checks for duplicate submissions within 5 minutes,
    and inserts into crm_leads with source='SURYANZ_SOLAR_WEBSITE' and category_id=6 (Solar).
    """
    name = (payload.get("name") or "").strip()
    phone_raw = (payload.get("phone") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    city = (payload.get("city") or "").strip()
    state = (payload.get("state") or "").strip()
    customer_type = (payload.get("customer_type") or "residential").strip().lower()
    interested_solution = (payload.get("interested_solution") or "Rooftop Solar System").strip()
    
    monthly_bill = float(payload.get("monthly_bill") or 0)
    roof_area = float(payload.get("roof_area_sqft") or payload.get("roof_area") or 0)
    recommended_capacity = float(payload.get("recommended_capacity") or payload.get("recommended_capacity_kw") or 0)
    preferred_contact_time = (payload.get("preferred_contact_time") or "").strip()

    # Validation
    if not name or len(name) < 2:
        raise HTTPException(status_code=400, detail="Please provide your full name.")

    phone = normalize_phone_10(phone_raw)
    if not phone or len(phone) != 10:
        raise HTTPException(status_code=400, detail="Please provide a valid 10-digit mobile number.")

    # Idempotency Check: Prevent duplicate lead creation within 5 minutes
    five_mins_ago = datetime.utcnow() - timedelta(minutes=5)
    existing_recent = db.query(CRMLead).filter(
        CRMLead.phone == phone,
        CRMLead.source == "SURYANZ_SOLAR_WEBSITE",
        CRMLead.created_at >= five_mins_ago
    ).first()

    if existing_recent:
        return {
            "success": True,
            "message": "Thank you! We have already received your enquiry. Our solar engineering expert will call you shortly.",
            "lead_id": existing_recent.id,
            "duplicate_prevented": True
        }

    company_id = _get_primary_solar_company_id(db)

    # UTM Metadata
    utm_source = payload.get("utm_source") or ""
    utm_medium = payload.get("utm_medium") or ""
    utm_campaign = payload.get("utm_campaign") or ""
    utm_term = payload.get("utm_term") or ""
    utm_content = payload.get("utm_content") or ""
    landing_url = payload.get("landing_url") or payload.get("page_url") or "suryanzsolar.com"

    req_details = (
        f"Customer Type: {customer_type.title()}\n"
        f"Monthly Electricity Bill: ₹{monthly_bill:,.2f}\n"
        f"Estimated Roof Area: {roof_area} sq.ft.\n"
        f"Recommended System Capacity: {recommended_capacity} kW\n"
        f"Interested Solution: {interested_solution}\n"
        f"Preferred Contact Time: {preferred_contact_time or 'Anytime'}\n"
        f"UTM Parameters: source={utm_source}, medium={utm_medium}, campaign={utm_campaign}\n"
        f"Landing Page: {landing_url}"
    )

    formatted_name = format_proper_name(name)

    new_lead = CRMLead(
        company_id=company_id,
        category_id=6,  # Category 6 = Solar
        name=formatted_name,
        phone=phone,
        email=email if email and "@" in email else None,
        city=city or "Not Specified",
        state=state or "Not Specified",
        source="SURYANZ_SOLAR_WEBSITE",
        source_details=f"Web Enquiry via Suryanz Solar Platform ({landing_url})",
        status="new",
        priority="high" if monthly_bill >= 10000 or customer_type == "commercial" else "medium",
        looking_for=f"SURYANZ SOLAR - {interested_solution} ({recommended_capacity} kW estimated)",
        requirements=req_details,
        address=f"{city}, {state}" if city and state else city,
        is_vgk_program=False
    )

    try:
        db.add(new_lead)
        db.commit()
        db.refresh(new_lead)
        logger.info(f"[SURYANZ-LEAD] Lead #{new_lead.id} captured successfully for {formatted_name} ({phone})")
    except Exception as e:
        db.rollback()
        logger.error(f"[SURYANZ-LEAD] Lead creation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to record enquiry. Please try again or request a callback.")

    return {
        "success": True,
        "message": "Your solar consultation request has been submitted successfully! A Suryanz Solar engineer will contact you shortly.",
        "lead_id": new_lead.id
    }


@router.post("/calculate", summary="Suryanz Solar Calculator Logic Engine")
def calculate_solar_estimate(
    payload: Dict[str, Any] = Body(...)
):
    """
    Public API calculation engine for Suryanz Solar Savings Calculator.
    Inputs: monthly_bill, tariff_rate, roof_area_sqft, customer_type
    Outputs: system_capacity_kw, annual_generation_kwh, annual_savings_inr, payback_years, co2_offset_tons
    """
    try:
        monthly_bill = float(payload.get("monthly_bill") or 0)
        tariff = float(payload.get("tariff_rate") or 8.0)  # Default ₹8.0 per kWh
        roof_area = float(payload.get("roof_area_sqft") or 0)
        customer_type = (payload.get("customer_type") or "residential").lower()

        if tariff <= 0: tariff = 8.0
        
        # Approximate monthly kWh consumption
        monthly_kwh = monthly_bill / tariff if monthly_bill > 0 else 300
        daily_kwh = monthly_kwh / 30.0

        # System capacity sizing: 1 kW generates approx 4 kWh per day in South/Central India
        recommended_kw = round(daily_kwh / 4.0, 1)
        if recommended_kw < 2.0:
            recommended_kw = 2.0  # Minimum residential system size

        # Required roof area check: ~80-100 sq ft per 1 kW
        required_roof_sqft = recommended_kw * 90.0
        roof_feasible = True if roof_area == 0 or roof_area >= required_roof_sqft else False

        # Generation & Financial Estimates
        annual_generation_kwh = round(recommended_kw * 1450, 0)  # ~1450 units per kW per year
        annual_savings_inr = round(annual_generation_kwh * tariff, 0)
        
        # Approximate system cost range (indicative)
        base_cost_per_kw = 55000 if customer_type == "commercial" else 62000
        approx_system_cost = round(recommended_kw * base_cost_per_kw, 0)
        
        payback_years = round(approx_system_cost / annual_savings_inr, 1) if annual_savings_inr > 0 else 4.5
        if payback_years < 3.0: payback_years = 3.2
        if payback_years > 7.0: payback_years = 6.5

        # 25-Year Cumulative Figures
        twenty_five_yr_savings = round(annual_savings_inr * 25 * 0.9, 0)  # Factoring 0.7% degradation per year
        twenty_five_yr_generation = round(annual_generation_kwh * 25 * 0.9, 0)
        co2_offset_tons = round((twenty_five_yr_generation * 0.82) / 1000.0, 1)

        return {
            "success": True,
            "data": {
                "monthly_bill": monthly_bill,
                "recommended_capacity_kw": recommended_kw,
                "annual_generation_kwh": annual_generation_kwh,
                "annual_savings_inr": annual_savings_inr,
                "approx_system_cost": approx_system_cost,
                "payback_years": payback_years,
                "roof_area_required_sqft": required_roof_sqft,
                "roof_feasible": roof_feasible,
                "twenty_five_year_savings_inr": twenty_five_yr_savings,
                "twenty_five_year_generation_kwh": twenty_five_yr_generation,
                "co2_offset_tons": co2_offset_tons,
                "disclaimer": "Indicative estimate — final system design, component selection, and financial payback require a physical site assessment."
            }
        }
    except Exception as e:
        logger.error(f"[SURYANZ-CALCULATOR] Error: {e}")
        raise HTTPException(status_code=400, detail="Invalid input parameters for calculation.")


@router.get("/knowledge", summary="Public Brand Knowledge Base for AI Search & Crawlers")
def get_suryanz_knowledge_base():
    """
    Public factual knowledge endpoint structured for AI Search Engines
    (ChatGPT Search, Google Gemini, Perplexity AI) and automated web crawlers.
    """
    return {
        "brand": {
            "master_brand": "SURYANZ",
            "vertical_brand": "SURYANZ SOLAR",
            "tagline": "Powering a Brighter Tomorrow",
            "positioning": "Smart Solar. Reliable Energy. A Better Future.",
            "background": "Backed by 20+ years of team experience in the solar and energy sector.",
            "corporate_domain": "https://suryanz.com",
            "solar_domain": "https://suryanzsolar.com",
            "verified_address": "[VERIFIED SURYANZ BUSINESS ADDRESS]"
        },
        "customer_protection_framework": {
            "stage_1_before_installation": [
                "Detailed engineering site assessment & shadow analysis",
                "Electricity consumption & load profile audit",
                "Transparent itemized quotation & scope-of-work documentation",
                "Accurate ROI and generation modeling"
            ],
            "stage_2_during_installation": [
                "Tier-1 high-efficiency module technology (540W, 550W, 580W TOPCon & N-Type)",
                "Structural safety evaluation & weather-proof mounting systems",
                "Electrical safety standards & certified inspection checklist",
                "Net-metering & grid connection documentation assistance"
            ],
            "stage_3_after_installation": [
                "Complete product & performance warranty documentation",
                "Inverter support (Up to 8–10 years depending on category)",
                "Module Product Warranty: 12 Years",
                "Module Performance Warranty: Up to 20–30 Years",
                "Ongoing monitoring, preventive AMC options & ticketed service support"
            ]
        },
        "solutions_offered": [
            "Residential Rooftop Solar Systems",
            "Commercial & Industrial Solar EPC",
            "On-Grid / Grid-Tied Solar Systems",
            "Hybrid Solar + Battery Energy Storage",
            "Off-Grid Remote Solar Energy Systems",
            "Solar Solutions for Housing Societies & Apartments",
            "Solar Operations, Maintenance & AMC (O&M)"
        ],
        "regions_covered": [
            "Andhra Pradesh (Visakhapatnam, Vijayawada, Guntur, Tirupati)",
            "Telangana (Hyderabad, Warangal, Karimnagar)",
            "Karnataka (Bengaluru, Mangalore, Mysuru, Hubballi)"
        ]
    }
