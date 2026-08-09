"""
Structured Creative Intelligence Engine & Multi-Vertical Concept System (Phase 2H)
Generates structured advertising creative briefs and vertical-specific creative concepts.
Enforces strict negative constraints and commercial advertising aesthetics.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

STANDARD_NEGATIVE_CONSTRAINTS = (
    "No distorted architecture, no fake solar panels, no malformed people, no extra limbs, "
    "no random gibberish text, no fake logos, no watermark, no cheap stock photo look, "
    "no cartoon or anime look, no excessive oversaturation, no visual clutter"
)


class CreativeBrief:
    def __init__(
        self,
        vertical: str,
        product_name: str,
        target_location: str,
        target_audience: str = "Homeowners",
        objective: str = "OUTCOME_LEADS",
        concept_name: str = "PREMIUM_HOME_SOLAR",
        headline: str = "",
        primary_text: str = "",
        cta_type: str = "LEARN_MORE",
        aspect_ratio: str = "1:1"
    ):
        self.vertical = vertical.upper()
        self.product_name = product_name
        self.target_location = target_location
        self.target_audience = target_audience
        self.objective = objective
        self.concept_name = concept_name
        self.headline = headline
        self.primary_text = primary_text
        self.cta_type = cta_type
        self.aspect_ratio = aspect_ratio
        self.negative_constraints = STANDARD_NEGATIVE_CONSTRAINTS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vertical": self.vertical,
            "product_name": self.product_name,
            "target_location": self.target_location,
            "target_audience": self.target_audience,
            "objective": self.objective,
            "concept_name": self.concept_name,
            "headline": self.headline,
            "primary_text": self.primary_text,
            "cta_type": self.cta_type,
            "aspect_ratio": self.aspect_ratio,
            "negative_constraints": self.negative_constraints
        }


def get_vertical_creative_concepts(vertical: str, product_name: str, location: str) -> List[Dict[str, Any]]:
    """
    Returns structured commercial advertising concepts for target vertical.
    """
    v = vertical.upper()
    if v == "SOLAR":
        return [
            {
                "concept_id": "PREMIUM_HOME_SOLAR",
                "concept_name": "1. Premium Home + Rooftop Solar",
                "visual_style": "Commercial Architectural Photography",
                "environment": f"Modern villa in {location} with sleek rooftop solar panels",
                "lighting": "Warm evening golden hour sunlight",
                "layout_template": "PRODUCT_HERO"
            },
            {
                "concept_id": "FAMILY_LIFESTYLE_SOLAR",
                "concept_name": "2. Family Lifestyle + Solar",
                "visual_style": "Warm Authentic Family Lifestyle",
                "environment": f"Indian family enjoying green lawn outside solar-powered home in {location}",
                "lighting": "Bright morning natural light",
                "layout_template": "LIFESTYLE"
            },
            {
                "concept_id": "PRODUCT_HERO_SOLAR",
                "concept_name": "3. High-Efficiency Product Hero",
                "visual_style": "Ultra HD Technical Product Close-up",
                "environment": "High-efficiency monocrystalline solar panels close-up with metallic sheen",
                "lighting": "Direct clear sunlight with metallic reflection",
                "layout_template": "SPLIT_LAYOUT"
            },
            {
                "concept_id": "SAVINGS_VALUE_SOLAR",
                "concept_name": "4. Energy Savings & Value",
                "visual_style": "Infographic Commercial Hybrid",
                "environment": "Solar rooftop background with clean negative space for zero-bill callouts",
                "lighting": "Crisp studio commercial light",
                "layout_template": "OFFER_BADGE"
            },
            {
                "concept_id": "TRUST_INSTALLATION_SOLAR",
                "concept_name": "5. Certified Installation Trust",
                "visual_style": "Professional Documentary Style",
                "environment": "Certified engineers inspecting solar inverter & rooftop panel wiring",
                "lighting": "Daylight professional workplace",
                "layout_template": "TEXT_LEFT_VISUAL_RIGHT"
            },
            {
                "concept_id": "REGIONAL_AP_SOLAR",
                "concept_name": "6. Andhra Pradesh Regional Pride",
                "visual_style": "Regional Commercial Showcase",
                "environment": f"Rooftop solar installation overlooking iconic {location} landscape",
                "lighting": "Clear blue sky daytime",
                "layout_template": "FULL_BLEED"
            }
        ]
    elif v == "EV":
        return [
            {"concept_id": "EV_LIFESTYLE", "concept_name": "1. EV Lifestyle", "layout_template": "LIFESTYLE"},
            {"concept_id": "EV_PRODUCT_HERO", "concept_name": "2. Product Hero", "layout_template": "PRODUCT_HERO"},
            {"concept_id": "EV_CHARGING", "concept_name": "3. Charging Convenience", "layout_template": "SPLIT_LAYOUT"}
        ]
    elif v == "REAL_ESTATE":
        return [
            {"concept_id": "RE_EXTERIOR_HERO", "concept_name": "1. Exterior Hero", "layout_template": "FULL_BLEED"},
            {"concept_id": "RE_INTERIOR_LIFESTYLE", "concept_name": "2. Interior Luxury", "layout_template": "LIFESTYLE"}
        ]
    elif v == "INSURANCE":
        return [
            {"concept_id": "INS_FAMILY_PROTECTION", "concept_name": "1. Family Protection", "layout_template": "LIFESTYLE"},
            {"concept_id": "INS_SECURITY", "concept_name": "2. Financial Security", "layout_template": "OFFER_BADGE"}
        ]
    else:  # TRAINING
        return [
            {"concept_id": "TRN_CAREER_UPGRADE", "concept_name": "1. Career Success", "layout_template": "TEXT_LEFT_VISUAL_RIGHT"},
            {"concept_id": "TRN_SKILL_DEV", "concept_name": "2. Professional Skill Lab", "layout_template": "PRODUCT_HERO"}
        ]
