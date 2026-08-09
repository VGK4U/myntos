"""
Multi-Vertical Configuration System (Release 1A Engine)
Defines vertical-specific qualification schemas, scoring factors, approved knowledge categories, and allowed actions.
Supports Solar, EV, Real Estate, Insurance, Training, and Future Verticals without hardcoding logic.
"""

from typing import Dict, Any, List

VERTICAL_CONFIGS: Dict[str, Dict[str, Any]] = {
    "SOLAR": {
        "display_name": "Solar Rooftop & Commercial",
        "qualification_fields": ["monthly_electricity_bill", "rooftop_area_sqft", "system_size_kw", "location", "budget", "timeline"],
        "qualification_questions": [
            "What is your average monthly electricity bill?",
            "Do you own the rooftop or property?",
            "When are you looking to install the solar system?"
        ],
        "scoring_factors": {"high_bill": 30, "own_rooftop": 25, "immediate_timeline": 25, "location_coverage": 20},
        "objection_categories": ["HIGH_INITIAL_COST", "ROI_TIMELINE", "ROOFTOP_SUITABILITY", "DISCOM_NET_METERING_DELAY"],
        "appointment_type": "SITE_SURVEY",
        "allowed_ai_actions": ["SEND_WHATSAPP", "START_AI_CALL", "SCHEDULE_FOLLOWUP", "BOOK_APPOINTMENT", "ASSIGN_HUMAN"]
    },
    "EV": {
        "display_name": "EV Vehicles & Spare Parts",
        "qualification_fields": ["vehicle_type", "fleet_quantity", "location", "budget", "financing_required", "timeline"],
        "qualification_questions": [
            "Are you looking for 2-wheeler, 3-wheeler, or commercial EV?",
            "What is the fleet size or quantity required?",
            "Do you require EV loan or financing options?"
        ],
        "scoring_factors": {"fleet_quantity_high": 35, "financing_preapproved": 25, "immediate_purchase": 25, "service_area": 15},
        "objection_categories": ["BATTERY_WARRANTY", "CHARGING_INFRASTRUCTURE", "PRICE_VS_ICE", "RANGE_ANXIETY"],
        "appointment_type": "TEST_DRIVE_SHOWROOM",
        "allowed_ai_actions": ["SEND_WHATSAPP", "START_AI_CALL", "SCHEDULE_FOLLOWUP", "BOOK_APPOINTMENT", "ASSIGN_HUMAN"]
    },
    "REAL_ESTATE": {
        "display_name": "Real Estate & Commercial Properties",
        "qualification_fields": ["property_type", "budget_range", "preferred_location", "purpose", "financing_needed", "possession_timeline"],
        "qualification_questions": [
            "Are you looking for plot, villa, or apartment?",
            "What is your preferred budget range?",
            "Is this for self-use or investment?"
        ],
        "scoring_factors": {"budget_matched": 35, "end_user": 25, "preapproved_home_loan": 20, "visit_scheduled": 20},
        "objection_categories": ["PRICE_PER_SQFT", "LOCATION_DISTANCE", "POSSESSION_DATE", "BUILDER_REPUTATION"],
        "appointment_type": "SITE_VISIT",
        "allowed_ai_actions": ["SEND_WHATSAPP", "START_AI_CALL", "SCHEDULE_FOLLOWUP", "BOOK_APPOINTMENT", "ASSIGN_HUMAN"]
    },
    "INSURANCE": {
        "display_name": "Health, Term & General Insurance",
        "qualification_fields": ["policy_type", "sum_insured", "member_count", "existing_diseases", "budget", "timeline"],
        "qualification_questions": [
            "Which insurance type are you seeking (Health, Life, Vehicle)?",
            "How many family members need coverage?",
            "Do you have any existing medical conditions?"
        ],
        "scoring_factors": {"high_sum_insured": 30, "family_floater": 25, "no_pre_existing": 25, "immediate_renewal": 20},
        "objection_categories": ["PREMIUM_COST", "CLAIM_SETTLEMENT_RATIO", "WAITING_PERIOD", "EXCLUSIONS"],
        "appointment_type": "EXPERT_CONSULTATION",
        "allowed_ai_actions": ["SEND_WHATSAPP", "START_AI_CALL", "SCHEDULE_FOLLOWUP", "ASSIGN_HUMAN"]
    },
    "TRAINING": {
        "display_name": "Executive & Vocational Training Programs",
        "qualification_fields": ["course_name", "education_level", "experience_years", "mode_preference", "budget", "timeline"],
        "qualification_questions": [
            "Which course or certification program interests you?",
            "Are you looking for online or classroom training?",
            "When do you plan to join the upcoming batch?"
        ],
        "scoring_factors": {"upcoming_batch_fit": 35, "working_professional": 25, "fee_budget_available": 25, "lead_activity": 15},
        "objection_categories": ["COURSE_FEE", "PLACEMENT_GUARANTEE", "BATCH_TIMINGS", "CERTIFICATION_RECOGNITION"],
        "appointment_type": "COUNSELING_SESSION",
        "allowed_ai_actions": ["SEND_WHATSAPP", "START_AI_CALL", "SCHEDULE_FOLLOWUP", "ASSIGN_HUMAN"]
    },
    "GENERAL": {
        "display_name": "General Inquiries",
        "qualification_fields": ["product_interest", "requirements", "location", "budget", "timeline"],
        "qualification_questions": ["How can our team assist you today?"],
        "scoring_factors": {"basic_interest": 50, "phone_provided": 50},
        "objection_categories": ["GENERAL_PRICING", "SERVICE_AVAILABILITY"],
        "appointment_type": "GENERAL_MEETING",
        "allowed_ai_actions": ["SEND_WHATSAPP", "SCHEDULE_FOLLOWUP", "ASSIGN_HUMAN"]
    }
}


def get_vertical_config(vertical: str) -> Dict[str, Any]:
    """Retrieve vertical configuration with safe GENERAL fallback."""
    v_upper = str(vertical or "GENERAL").upper()
    return VERTICAL_CONFIGS.get(v_upper, VERTICAL_CONFIGS["GENERAL"])
