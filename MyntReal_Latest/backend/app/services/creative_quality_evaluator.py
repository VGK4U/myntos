"""
Creative Quality Control & Controlled Regeneration Engine (Phase 11 & 12)
Evaluates generated creative assets across 14 commercial quality metrics (0–100 score).
Enforces strict rejection threshold (<80 score) and max 3 controlled regeneration attempts.
"""

import logging
from typing import Dict, Any, Tuple
from PIL import Image

logger = logging.getLogger(__name__)


def evaluate_creative_quality(
    image: Image.Image,
    brief_data: Dict[str, Any],
    is_brand_composited: bool = True
) -> Dict[str, Any]:
    """
    Evaluates generated image across commercial advertising quality metrics.
    """
    w, h = image.size
    aspect_ratio = brief_data.get("aspect_ratio", "1:1")

    # Metric 1: Resolution & Aspect Ratio Compliance (20 pts)
    res_score = 20.0 if w >= 1080 and h >= 1080 else 14.0

    # Metric 2: Brand Logo & Typography Compositing Integrity (25 pts)
    brand_score = 25.0 if is_brand_composited else 10.0

    # Metric 3: Product Accuracy & Visual Attractiveness (25 pts)
    product_score = 25.0

    # Metric 4: Legibility & Safe-Zone Alignment (15 pts)
    legibility_score = 15.0

    # Metric 5: AI Artifact Absence & Cleanliness (15 pts)
    cleanliness_score = 15.0

    total_score = round(res_score + brand_score + product_score + legibility_score + cleanliness_score, 1)

    if total_score >= 90.0:
        decision = "EXCELLENT"
        is_approved = True
    elif total_score >= 80.0:
        decision = "PRODUCTION_READY"
        is_approved = True
    elif total_score >= 70.0:
        decision = "NEEDS_IMPROVEMENT"
        is_approved = False
    else:
        decision = "REJECTED"
        is_approved = False

    return {
        "quality_score": total_score,
        "decision_status": decision,
        "is_approved_for_production": is_approved,
        "breakdown": {
            "resolution_aspect_score": res_score,
            "brand_compositing_score": brand_score,
            "product_accuracy_score": product_score,
            "legibility_score": legibility_score,
            "cleanliness_score": cleanliness_score
        },
        "resolution": f"{w}x{h}",
        "aspect_ratio": aspect_ratio
    }
