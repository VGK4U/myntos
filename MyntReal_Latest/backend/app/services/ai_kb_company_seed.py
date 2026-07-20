"""
AI KB Company Seed — DC Protocol AI_KB_COMPANY_001
Inserts factual, neutral, compliance-safe KB entries for:
  - COMPANY_BACKGROUND  : legal identity, registrations, ecosystem
  - EV_MARKET           : EV brand comparison (neutral)
  - SOLAR_MARKET        : Solar brand comparison (neutral)
  - INSURANCE_MARKET    : Insurance comparison (neutral)
  - FAQ_GENERAL         : Common trust/reliability Q&A
  - PARTNER_SUPPORT     : VGK4U ecosystem, partner model

Rules:
  - Idempotent: checks for seed marker before inserting
  - Additive only: no existing rows modified or deleted
  - company_id=1 (MyntReal default)
  - All factual claims anchored to verifiable references
  - No income guarantees, no recruitment framing, no unverifiable stats
"""

import logging
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

_SEED_MARKER_CATEGORY = "COMPANY_SEED_V1"
_COMPANY_ID = 1

_KB_ENTRIES = [

    # ── SEGMENT: COMPANY_BACKGROUND ─────────────────────────────────────────
    {
        "segment": "COMPANY_BACKGROUND",
        "category": "COMPANY_SEED_V1",
        "title": "Seed Marker — Company Background",
        "content": "Seed marker for COMPANY_BACKGROUND segment. Version: V1.",
        "sort_order": 0,
    },
    {
        "segment": "COMPANY_BACKGROUND",
        "category": "LEGAL_IDENTITY",
        "title": "What is MyntReal / Mynt Real LLP?",
        "content": (
            "MyntReal (legal name: Mynt Real LLP) is a registered Limited Liability Partnership "
            "based in Andhra Pradesh, India. It operates a structured business ecosystem across "
            "electric vehicle mobility, solar energy, insurance facilitation, real estate services, "
            "and professional EV training.\n\n"
            "Primary response when asked 'Is MyntReal genuine?' or 'What is this company?':\n"
            "MyntReal / VGK4U is a registered business ecosystem operating in EV mobility, solar energy, "
            "insurance facilitation, and related services across Andhra Pradesh and Telangana, with "
            "verified legal and tax registrations."
        ),
        "sort_order": 1,
    },
    {
        "segment": "COMPANY_BACKGROUND",
        "category": "LEGAL_IDENTITY",
        "title": "MCA Registration — Mynt Real LLP",
        "content": (
            "Mynt Real LLP is registered with the Ministry of Corporate Affairs (MCA):\n"
            "- LLPIN: ACT-5518\n"
            "- Registrar of Companies: ROC Vijayawada\n"
            "- Incorporation Date: 16 December 2025\n"
            "- Status: Active\n"
            "- Registered State: Andhra Pradesh\n\n"
            "Verification: mca.gov.in → Search LLP → LLPIN ACT-5518"
        ),
        "sort_order": 2,
    },
    {
        "segment": "COMPANY_BACKGROUND",
        "category": "LEGAL_IDENTITY",
        "title": "GST Registration — Mynt Real LLP",
        "content": (
            "Mynt Real LLP holds an active GST registration:\n"
            "- GSTIN: 37ACFM9S86Q1Z0\n"
            "- State: Andhra Pradesh (State Code 37)\n"
            "- Status: Active\n\n"
            "Verification: gst.gov.in → Search Taxpayer → GSTIN 37ACFM9S86Q1Z0"
        ),
        "sort_order": 3,
    },
    {
        "segment": "COMPANY_BACKGROUND",
        "category": "LEGAL_IDENTITY",
        "title": "ISO Certification — Mynt Real LLP",
        "content": (
            "Mynt Real LLP holds ISO 9001:2015 certification for Quality Management Systems:\n"
            "- Standard: ISO 9001:2015 — Quality Management Systems\n"
            "- Certificate Number: E20260346985\n"
            "- Scope: Standardized operations across all business verticals"
        ),
        "sort_order": 4,
    },
    {
        "segment": "COMPANY_BACKGROUND",
        "category": "ECOSYSTEM",
        "title": "Business Verticals Overview",
        "content": (
            "MyntReal operates across five business verticals:\n"
            "1. Royal Manthra EV — Electric two-wheelers with LFP battery technology (PRIMARY)\n"
            "2. Har Ghar Solar — PM Surya Ghar subsidised rooftop solar facilitation (PRIMARY)\n"
            "3. VGK Care — Insurance facilitation (health, life, vehicle, business)\n"
            "4. VGK Real Dreams — Real estate facilitation (plots, apartments, agricultural land)\n"
            "5. EVolution Training Center — Professional EV technician certification\n\n"
            "Geographic coverage: Andhra Pradesh and Telangana"
        ),
        "sort_order": 5,
    },
    {
        "segment": "COMPANY_BACKGROUND",
        "category": "ECOSYSTEM",
        "title": "VGK4U — Partner Ecosystem Explained",
        "content": (
            "VGK4U is the partner and member network operating under MyntReal.\n\n"
            "Structure:\n"
            "- Mynt Real LLP is the registered legal entity (MCA, GSTIN, ISO)\n"
            "- VGK4U is the partner ecosystem connecting independent business partners to MyntReal products\n\n"
            "What VGK4U partners do:\n"
            "- Facilitate sales of Royal Manthra EV 2-wheelers in their local area\n"
            "- Assist customers with Har Ghar Solar applications and installations\n"
            "- Support insurance facilitation through VGK Care\n"
            "- Refer real estate leads through VGK Real Dreams\n\n"
            "Partner earnings are based on documented product/service transactions — not recruitment."
        ),
        "sort_order": 6,
    },

    # ── SEGMENT: EV_MARKET ───────────────────────────────────────────────────
    {
        "segment": "EV_MARKET",
        "category": "COMPANY_SEED_V1",
        "title": "Seed Marker — EV Market",
        "content": "Seed marker for EV_MARKET segment. Version: V1.",
        "sort_order": 0,
    },
    {
        "segment": "EV_MARKET",
        "category": "BRAND_COMPARISON",
        "title": "EV 2-Wheeler Market — Key Brands (India)",
        "content": (
            "Key electric 2-wheeler brands available in India (neutral comparison):\n\n"
            "Ola Electric (S1 series):\n"
            "- Range: 90–195 km | Price: ₹75,000–1,50,000\n"
            "- Strengths: Large service network, OTA updates, app integration\n"
            "- Considerations: Service quality varies by city\n\n"
            "Ather Energy (450X, 450 Apex):\n"
            "- Range: 105–150 km | Price: ₹1,20,000–1,65,000\n"
            "- Strengths: Performance-focused, fast charging grid, good app experience\n"
            "- Considerations: Higher price segment\n\n"
            "TVS iQube:\n"
            "- Range: 100–145 km | Price: ₹85,000–1,30,000\n"
            "- Strengths: Established brand, wide service network, reliable build\n"
            "- Considerations: Mid-tier performance\n\n"
            "Bajaj Chetak:\n"
            "- Range: 108–126 km | Price: ₹1,00,000–1,20,000\n"
            "- Strengths: Classic styling, Bajaj service reliability\n"
            "- Considerations: Limited range vs newer models\n\n"
            "Hero Vida V1:\n"
            "- Range: 110–165 km | Price: ₹80,000–1,45,000\n"
            "- Strengths: Hero dealer network coverage across India\n"
            "- Considerations: Newer entrant, service maturity still developing\n\n"
            "Royal Manthra EV (MyntReal ecosystem):\n"
            "- LFP (Lithium Iron Phosphate) battery technology — longer cycle life vs NMC\n"
            "- Distributed through VGK4U partner network in Andhra Pradesh and Telangana\n"
            "- Suited for customers in AP/Telangana seeking ecosystem-backed local support"
        ),
        "sort_order": 1,
    },
    {
        "segment": "EV_MARKET",
        "category": "BUYING_GUIDE",
        "title": "How to Choose the Right EV Scooter",
        "content": (
            "Key factors to evaluate when choosing an electric scooter:\n\n"
            "1. Daily commute range: Choose a vehicle with 30–40% more range than your daily need\n"
            "2. Charging infrastructure: Check availability of charging at home/office (most EV scooters use standard home charging)\n"
            "3. Service network: Verify there is an authorised service centre within practical distance\n"
            "4. Battery warranty: Look for minimum 3-year battery warranty\n"
            "5. Total cost of ownership: Compare upfront price + maintenance + insurance cost\n"
            "6. LFP vs NMC batteries: LFP batteries have longer cycle life and better thermal stability; NMC offers higher energy density\n\n"
            "For customers in Andhra Pradesh and Telangana: Royal Manthra EV through MyntReal/VGK4U "
            "offers localised support and ecosystem integration with solar and insurance."
        ),
        "sort_order": 2,
    },

    # ── SEGMENT: SOLAR_MARKET ────────────────────────────────────────────────
    {
        "segment": "SOLAR_MARKET",
        "category": "COMPANY_SEED_V1",
        "title": "Seed Marker — Solar Market",
        "content": "Seed marker for SOLAR_MARKET segment. Version: V1.",
        "sort_order": 0,
    },
    {
        "segment": "SOLAR_MARKET",
        "category": "BRAND_COMPARISON",
        "title": "Rooftop Solar — Key Providers (India)",
        "content": (
            "Key rooftop solar providers and panel manufacturers in India (neutral comparison):\n\n"
            "Tata Power Solar:\n"
            "- Large integrated solar company — panels + installation + maintenance\n"
            "- Strengths: Trusted brand, pan-India presence, financing options\n"
            "- Suited for: Urban residential, commercial, and industrial\n\n"
            "Loom Solar:\n"
            "- Mono PERC and bi-facial panels; strong e-commerce distribution\n"
            "- Strengths: Competitive pricing, good dealer network\n"
            "- Suited for: Budget-conscious residential customers\n\n"
            "Waaree Energies:\n"
            "- One of India's largest panel manufacturers\n"
            "- Strengths: Wide panel wattage range, export-grade quality\n"
            "- Suited for: Bulk/commercial installations\n\n"
            "Vikram Solar:\n"
            "- Premium mono PERC panels; strong efficiency ratings\n"
            "- Strengths: Quality certifications, institutional projects\n"
            "- Suited for: Quality-first installations\n\n"
            "Adani Solar:\n"
            "- Integrated solar + green energy company\n"
            "- Strengths: Scale, financing ecosystem, brand recognition\n"
            "- Suited for: Large-scale and commercial\n\n"
            "MyntReal / Har Ghar Solar (AP & Telangana):\n"
            "- Facilitates PM Surya Ghar Muft Bijli Yojana (govt subsidy up to ₹78,000)\n"
            "- Handles DISCOM registration, subsidy paperwork, and installation coordination\n"
            "- Suited for: Residential customers in AP/Telangana seeking guided subsidy process"
        ),
        "sort_order": 1,
    },
    {
        "segment": "SOLAR_MARKET",
        "category": "BUYING_GUIDE",
        "title": "PM Surya Ghar Subsidy — How It Works",
        "content": (
            "PM Surya Ghar Muft Bijli Yojana — Government subsidy for rooftop solar:\n\n"
            "Subsidy structure (as per scheme guidelines):\n"
            "- Up to 1 kW: ₹30,000 subsidy\n"
            "- 1–2 kW: ₹60,000 subsidy\n"
            "- 2–3 kW: ₹78,000 subsidy (maximum)\n\n"
            "Eligibility:\n"
            "- Residential property with active electricity connection (DISCOM registered)\n"
            "- Property must be in India\n\n"
            "Process overview:\n"
            "1. Register on the PM Surya Ghar portal (pmsuryaghar.gov.in)\n"
            "2. Get DISCOM approval for grid-connected system\n"
            "3. Choose an empanelled installer\n"
            "4. Install system and get net meter installed by DISCOM\n"
            "5. Submit documents to claim subsidy\n\n"
            "Har Ghar Solar (MyntReal) facilitates steps 1–5 for customers in AP and Telangana."
        ),
        "sort_order": 2,
    },

    # ── SEGMENT: INSURANCE_MARKET ────────────────────────────────────────────
    {
        "segment": "INSURANCE_MARKET",
        "category": "COMPANY_SEED_V1",
        "title": "Seed Marker — Insurance Market",
        "content": "Seed marker for INSURANCE_MARKET segment. Version: V1.",
        "sort_order": 0,
    },
    {
        "segment": "INSURANCE_MARKET",
        "category": "BRAND_COMPARISON",
        "title": "Health Insurance — Key Providers (India)",
        "content": (
            "Major health insurance providers in India (neutral comparison):\n\n"
            "HDFC Ergo Health:\n"
            "- Strong claim settlement ratio; wide hospital network\n"
            "- Products: Optima Secure, my:health Suraksha\n"
            "- Good for: Comprehensive family floater plans\n\n"
            "Star Health Insurance:\n"
            "- Dedicated health insurer with large hospital tie-ups\n"
            "- Products: Comprehensive, Senior Citizen Red Carpet\n"
            "- Good for: Senior citizen coverage, Andhra Pradesh hospital network\n\n"
            "ICICI Lombard:\n"
            "- Large general insurer; strong digital claims process\n"
            "- Products: Complete Health Insurance, iHealth\n"
            "- Good for: Digital-first customers seeking fast claims\n\n"
            "SBI General Insurance:\n"
            "- Backed by SBI; good rural and semi-urban network\n"
            "- Products: Arogya Supreme\n"
            "- Good for: Customers with existing SBI banking relationship\n\n"
            "Niva Bupa (formerly Max Bupa):\n"
            "- Strong network of cashless hospitals\n"
            "- Products: ReAssure, Health Companion\n"
            "- Good for: High sum insured, premium coverage\n\n"
            "VGK Care (MyntReal) facilitates comparison across these and other IRDAI-regulated "
            "providers — helping customers choose based on their specific needs and budget."
        ),
        "sort_order": 1,
    },
    {
        "segment": "INSURANCE_MARKET",
        "category": "BUYING_GUIDE",
        "title": "How to Choose Health Insurance",
        "content": (
            "Key factors when selecting health insurance:\n\n"
            "1. Sum insured: Minimum ₹5 lakh for individuals; ₹10–15 lakh recommended for families\n"
            "2. Network hospitals: Verify cashless hospitals near your location\n"
            "3. Claim settlement ratio: Higher % indicates better claim approval rate\n"
            "4. Waiting periods: Pre-existing disease waiting period (typically 2–4 years)\n"
            "5. No-claim bonus: Plans that increase sum insured for claim-free years\n"
            "6. Sub-limits: Some plans cap room rent or specific treatments — check carefully\n"
            "7. Premium vs coverage: Cheapest plan is not always best — compare exclusions\n\n"
            "VGK Care assists with comparison, documentation, and claim support for AP/Telangana customers."
        ),
        "sort_order": 2,
    },

    # ── SEGMENT: FAQ_GENERAL ─────────────────────────────────────────────────
    {
        "segment": "FAQ_GENERAL",
        "category": "COMPANY_SEED_V1",
        "title": "Seed Marker — FAQ General",
        "content": "Seed marker for FAQ_GENERAL segment. Version: V1.",
        "sort_order": 0,
    },
    {
        "segment": "FAQ_GENERAL",
        "category": "TRUST_FAQ",
        "title": "Q: Is MyntReal genuine / trustworthy?",
        "content": (
            "RESPONSE TEMPLATE when asked 'Is MyntReal genuine?' / 'Is this trustworthy?' / 'What is this company?':\n\n"
            "Lead with: 'MyntReal LLP is a registered business ecosystem operating in EV mobility, solar energy, "
            "insurance facilitation, and related services across Andhra Pradesh and Telangana, with verified "
            "legal and tax registrations.'\n\n"
            "Then provide:\n"
            "- MCA Registration: LLPIN ACT-5518, ROC Vijayawada, incorporated 16 Dec 2025, Status: Active\n"
            "- GSTIN: 37ACFM9S86Q1Z0 (Active, Andhra Pradesh)\n"
            "- ISO 9001:2015 Certification: Certificate No. E20260346985\n"
            "- Geographic scope: Andhra Pradesh and Telangana\n"
            "- Primary business: Royal Manthra EV 2-wheelers and Har Ghar Solar installations\n\n"
            "Do NOT: use defensive language, make income guarantees, attack competitors, "
            "or make claims that cannot be independently verified."
        ),
        "sort_order": 1,
    },
    {
        "segment": "FAQ_GENERAL",
        "category": "TRUST_FAQ",
        "title": "Q: Does MyntReal guarantee income?",
        "content": (
            "Response when asked about income guarantees or returns:\n\n"
            "MyntReal does not guarantee any fixed income, returns, or earnings to partners or members. "
            "Partner earnings within the VGK4U ecosystem are based on documented product and service "
            "transactions — specifically sales of Royal Manthra EV 2-wheelers, solar installations, "
            "and insurance facilitation.\n\n"
            "Income depends on individual partner activity, local market conditions, and actual "
            "product/service sales. Past or estimated figures are not guaranteed future outcomes."
        ),
        "sort_order": 2,
    },
    {
        "segment": "FAQ_GENERAL",
        "category": "TRUST_FAQ",
        "title": "Q: How can registrations be verified independently?",
        "content": (
            "Independent verification steps:\n\n"
            "MCA (LLPIN):\n"
            "  → mca.gov.in → LLP Master Data → Search LLPIN: ACT-5518\n\n"
            "GST:\n"
            "  → gst.gov.in → Search Taxpayer → GSTIN: 37ACFM9S86Q1Z0\n\n"
            "ISO Certificate:\n"
            "  → Certificate No: E20260346985 — request document from MyntReal directly\n\n"
            "All three can be independently verified without contacting MyntReal."
        ),
        "sort_order": 3,
    },

    # ── SEGMENT: PARTNER_SUPPORT ─────────────────────────────────────────────
    {
        "segment": "PARTNER_SUPPORT",
        "category": "COMPANY_SEED_V1",
        "title": "Seed Marker — Partner Support",
        "content": "Seed marker for PARTNER_SUPPORT segment. Version: V1.",
        "sort_order": 0,
    },
    {
        "segment": "PARTNER_SUPPORT",
        "category": "PARTNER_MODEL",
        "title": "VGK4U Partner Model — How It Works",
        "content": (
            "VGK4U is the partner network of Mynt Real LLP.\n\n"
            "What partners do:\n"
            "- Facilitate sales of Royal Manthra EV 2-wheelers in their local area (AP/Telangana)\n"
            "- Assist customers with Har Ghar Solar applications and PM Surya Ghar subsidy process\n"
            "- Support insurance facilitation through VGK Care\n"
            "- Refer real estate leads through VGK Real Dreams\n\n"
            "How partner earnings work:\n"
            "- Based on completed, documented product/service transactions\n"
            "- Not based on recruitment of new members\n"
            "- Commission structure is defined per product/service category\n\n"
            "Joining VGK4U:\n"
            "- Partners register through the official VGK4U platform\n"
            "- KYC and documentation required before activation\n"
            "- Access to MyntReal's product catalogue, pricing, and operational support"
        ),
        "sort_order": 1,
    },
    {
        "segment": "PARTNER_SUPPORT",
        "category": "PARTNER_MODEL",
        "title": "VGK4U — Registered Address and Contact",
        "content": (
            "Mynt Real LLP (operating as MyntReal / VGK4U):\n\n"
            "Registered Address:\n"
            "Sy No.156/1, Saripalli, Pendurthy,\n"
            "Visakhapatnam, Andhra Pradesh 531173\n\n"
            "LLPIN: ACT-5518\n"
            "GSTIN: 37ACFM9S86Q1Z0\n"
            "ISO: 9001:2015 — Certificate E20260346985\n\n"
            "For official queries, contact through: myntreal.com/hub/contact"
        ),
        "sort_order": 2,
    },
]


def run_ai_kb_company_seed(db: Session) -> None:
    """Idempotently insert company KB entries into ai_product_catalogue.

    Checks for seed marker row before inserting. Safe to call at every startup.
    """
    try:
        existing = db.execute(
            text(
                "SELECT COUNT(*) FROM ai_product_catalogue "
                "WHERE company_id = :cid AND category = :cat"
            ),
            {"cid": _COMPANY_ID, "cat": _SEED_MARKER_CATEGORY},
        ).scalar()

        if existing and existing > 0:
            logger.info("[AI_KB_COMPANY] Seed already applied — skipping.")
            return

        inserted = 0
        for entry in _KB_ENTRIES:
            db.execute(
                text(
                    "INSERT INTO ai_product_catalogue "
                    "(company_id, segment, category, title, content, is_active, sort_order, created_by) "
                    "VALUES (:cid, :seg, :cat, :title, :content, TRUE, :sort, 'system_seed')"
                ),
                {
                    "cid": _COMPANY_ID,
                    "seg": entry["segment"],
                    "cat": entry["category"],
                    "title": entry["title"],
                    "content": entry["content"],
                    "sort": entry.get("sort_order", 0),
                },
            )
            inserted += 1

        db.commit()
        logger.info(f"[AI_KB_COMPANY] Seeded {inserted} KB entries across 6 segments.")

    except Exception as exc:
        db.rollback()
        logger.warning(f"[AI_KB_COMPANY] Seed warning (non-fatal): {exc}")
