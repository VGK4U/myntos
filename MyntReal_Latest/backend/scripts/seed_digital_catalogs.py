"""
Seed Default Digital Catalogs — MyntOS Single-Page Digital Catalog Platform
Initializes official high-converting catalogs for all 9 business verticals:
1. SOLAR
2. INDUSTRIAL_HUB
3. HUB_PRICING
4. EV_B2B
5. EV_B2C
6. EV_SPARES
7. ETC_TRAINING
8. REAL_DREAMS
9. INSURANCE

Multi-company and multi-tenant scoped (associated_companies.id = 4 / MyntReal LLP default, company 88 / VGK4U compatible).
DC Protocol Compliant: uses get_indian_time and relative paths.
"""

import os
import sys
import json
import logging
from datetime import datetime

# Rule 1: Dynamic relative path resolution
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, '..'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import SessionLocal, engine
from app.models.base import get_indian_time
from app.models.digital_catalog import DigitalCatalog, CatalogSection, CatalogItem
from app.models.staff_accounts import AssociatedCompany
from app.models.signup_category import SignupCategory

logger = logging.getLogger("seed_catalogs")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


SEED_CATALOGS_DATA = [
    {
        "segment_code": "SOLAR",
        "slug": "commercial-residential-solar",
        "title": "MYNTREAL — Har Ghar Solar (హర్ ఘర్ సోలార్)",
        "subtitle": "ప్రధానమంత్రి సూర్య ఘర్ ఉచిత విద్యుత్ యోజన | PM Surya Ghar Muft Bijli Yojana — Rooftop Solar Power Solutions",
        "summary": "Slash electricity bills up to 90% with Tier-1 Rooftop Solar systems from Navgrun, APS, Waaree, Adani, Vikram Solar, ReNew, and TATA Solar. Claim up to ₹78,000 Direct Govt Subsidy (DBT) and easy bank financing with 25-year performance warranty.",
        "hero_media_url": "https://images.unsplash.com/photo-1509391365360-2e959784a276?auto=format&fit=crop&w=1600&q=80",
        "theme_config": {"primary_color": "#10b981", "accent_color": "#f59e0b", "dark_mode": True},
        "default_language": "en",
        "active_languages": ["en", "te", "hi", "ta"],
        "sections": [
            {
                "section_type": "hero",
                "section_key": "hero",
                "title": "Har Ghar Solar — Free Power For Every Home (హర్ ఘర్ సోలార్)",
                "subtitle": "Cut Power Bills by 90% with ₹78,000 Direct Bank Subsidy & Low-Interest Bank Loans (SBI, BoB, Canara, Union, Indian Bank)",
                "content_variants": {
                    "en": {
                        "title": "Har Ghar Solar — Free Power For Every Home (హర్ ఘర్ సోలార్)",
                        "subtitle": "Cut Power Bills by 90% with ₹78,000 Direct Bank Subsidy & Low-Interest Bank Loans",
                        "cta_text": "Calculate Savings & Request Site Audit",
                        "cta_phone": "918585852738"
                    },
                    "te": {
                        "title": "హర్ ఘర్ సోలార్ — ప్రధానమంత్రి సూర్య ఘర్ ఉచిత విద్యుత్ యోజన",
                        "subtitle": "ప్రతి ఇంటికి సౌర విద్యుత్ — ₹78,000 వరకు నేరుగా బ్యాంక్ ఖాతాలో సబ్సిడీ మరియు 25 సంవత్సరాల వారంటీతో కరెంట్ బిల్లులను 90% వరకు ఆదా చేయండి.",
                        "cta_text": "ఉచిత సైట్ సర్వే & పొదుపు గణన",
                        "cta_phone": "918585852738"
                    },
                    "hi": {
                        "title": "हर घर सोलर — प्रधानमंत्री सूर्य घर मुफ्त बिजली योजना",
                        "subtitle": "अपने घर को बनाएं बिजली का पावर हाउस — ₹78,000 तक सीधी बैंक सब्सिडी और 90% तक बिजली बिल में बचत।",
                        "cta_text": "मुफ्त साइट सर्वे बुक करें",
                        "cta_phone": "918585852738"
                    },
                    "ta": {
                        "title": "ஹர் கர் சோலார் — பிரதம மந்திரி சூர்ய கர் இலவச மின் திட்டம்",
                        "subtitle": "உங்கள் வீட்டிற்கு சூரிய மின்சக்தி — ₹78,000 வரை நேரடி வங்கி மானியம் மற்றும் 90% வரை மின் கட்டண சேமிப்பு.",
                        "cta_text": "இலவச தள ஆய்வு பெறுக",
                        "cta_phone": "918585852738"
                    }
                },
                "configuration": {
                    "badge": "PM Surya Ghar Muft Bijli Yojana",
                    "badge_te": "ప్రధానమంత్రి సూర్య ఘర్ యోజన",
                    "brands": ["Goldi Solar", "Navgrun", "APS", "Waaree", "Adani Solar", "Vikram Solar", "ReNew Power", "TATA Solar"],
                    "stats": [
                        {"label": "Direct Govt Subsidy", "value": "Up to ₹78,000"},
                        {"label": "Bill Reduction", "value": "Up to 90%"},
                        {"label": "Linear Warranty", "value": "25 Years"},
                        {"label": "Bank EMI From", "value": "₹1,140 / mo"}
                    ]
                }
            },
            {
                "section_type": "roi_calculator",
                "section_key": "calculator",
                "title": "Solar Requirement & Investment Calculator (సోలార్ కాలిక్యులేటర్)",
                "subtitle": "Calculate recommended capacity, compare brand pricing (Goldi, Navgrun, APS, Waaree, Adani, Tata) & see your net savings after ₹78,000 subsidy!",
                "content_variants": {
                    "en": {
                        "title": "Solar Requirement & Investment Calculator",
                        "subtitle": "Select premise type, enter monthly electricity bill or units, and see transparent pricing with ₹78,000 DBT subsidy, bank loans & instant discounts."
                    },
                    "te": {
                        "title": "సోలార్ సామర్థ్యం & పొదుపు కాలిక్యులేటర్",
                        "subtitle": "మీ ప్రాంగణం రకం మరియు నెలవారీ కరెంట్ బిల్లును ఎంచుకుని, ప్రముఖ బ్రాండ్ల ధరలు, ప్రభుత్వ సబ్సిడీ మరియు సులభ వాయిదాల వివరాలు తెలుసుకోండి."
                    },
                    "hi": {
                        "title": "सोलर क्षमता और बचत कैलकुलेटर",
                        "subtitle": "अपना मासिक बिजली बिल या यूनिट दर्ज करें और ₹78,000 तक की सब्सिडी और बैंक लोन के साथ पूरी बचत देखें।"
                    },
                    "ta": {
                        "title": "சூரிய சக்தி தேவை மற்றும் சேமிப்பு கால்குலேட்டர்",
                        "subtitle": "உங்கள் மாத மின் கட்டணத்தை உள்ளிட்டு, அரசு மானியம் மற்றும் வங்கி தவணை விவரங்களை உடனடியாகக் கணக்கிடுங்கள்."
                    }
                },
                "configuration": {
                    "subsidies": {
                        "1": 30000,
                        "2": 60000,
                        "3": 78000,
                        "4": 78000,
                        "5": 78000,
                        "6": 78000,
                        "10": 78000
                    },
                    "brand_tiers": [
                        {
                            "id": "goldi_navgrun_aps",
                            "name": "Goldi Solar, Navgrun & APS (Australian Premium Solar)",
                            "tag": "Best Value Tier • 25-Yr Performance Warranty",
                            "base_3kw": 199999
                        },
                        {
                            "id": "waaree_adani",
                            "name": "Waaree / Adani / Vikram Solar / ReNew",
                            "tag": "India Top Tier-1 Manufacturers • High Efficiency",
                            "base_3kw": 209999
                        },
                        {
                            "id": "tata_solar",
                            "name": "TATA Solar",
                            "tag": "Premium Brand Leader • India's Most Trusted",
                            "base_3kw": 220000
                        }
                    ],
                    "pricing_rules": {
                        "mrp_markup": 20000,
                        "instant_discount": 10000,
                        "site_voucher_discount": 10000
                    },
                    "bill_presets": [
                        {"label": "₹1,500/mo", "bill": 1500, "units": 150, "recommended_kw": 1},
                        {"label": "₹2,000 - ₹2,500/mo", "bill": 2500, "units": 240, "recommended_kw": 2},
                        {"label": "₹3,000 - ₹4,000/mo", "bill": 3500, "units": 350, "recommended_kw": 3},
                        {"label": "₹4,500 - ₹6,000/mo", "bill": 5000, "units": 450, "recommended_kw": 4},
                        {"label": "₹6,000 - ₹8,000/mo", "bill": 7000, "units": 550, "recommended_kw": 5},
                        {"label": "₹8,000 - ₹10,000/mo", "bill": 9000, "units": 650, "recommended_kw": 6},
                        {"label": "₹15,000+/mo", "bill": 15000, "units": 1100, "recommended_kw": 10}
                    ]
                }
            },
            {
                "section_type": "comparison_table",
                "section_key": "pricing_matrix",
                "title": "Official Capacity & Financial Matrix (హర్ ఘర్ సోలార్ అధికారిక ప్యాకేజీలు)",
                "subtitle": "Complete 10-column financial comparison across 2kW, 3kW, 4kW, 5kW, 6kW, 10kW with brand selection",
                "content_variants": {
                    "en": {
                        "title": "Official Capacity & Financial Matrix",
                        "subtitle": "Complete 10-column financial comparison across 2kW, 3kW, 4kW, 5kW, 6kW, 10kW matching official brochure."
                    },
                    "te": {
                        "title": "అధికారిక సోలార్ ప్యాకేజీలు & రుణ వివరాలు (Official Matrix)",
                        "subtitle": "2 kW నుండి 10 kW వరకు సామర్థ్యం, పొదుపు, సబ్సిడీ, డౌన్ పేమెంట్ మరియు 5 & 10 సంవత్సరాల EMI ల సమగ్ర పట్టిక."
                    }
                },
                "configuration": {
                    "columns": [
                        "Plant Capacity (kW)",
                        "Monthly Generation (Units)",
                        "Monthly Savings (₹)",
                        "System Price (₹)",
                        "PM Surya Ghar Subsidy (₹)",
                        "Net Customer Investment (₹)",
                        "Down Payment (₹)",
                        "Bank Loan Amount (₹)",
                        "5-Year Monthly EMI (₹)",
                        "10-Year Monthly EMI (₹)"
                    ],
                    "rows": [
                        {
                            "kw": 1,
                            "units": "100 - 130 Units",
                            "savings": "₹800 - ₹1,000",
                            "system_price": 90000,
                            "subsidy": 30000,
                            "net_cost": 60000,
                            "down_payment": 10000,
                            "loan_amount": 50000,
                            "emi_5y": 1050,
                            "emi_10y": 600,
                            "is_recommended": False
                        },
                        {
                            "kw": 2,
                            "units": "220 - 250 Units",
                            "savings": "₹1,500 - ₹2,000",
                            "system_price": 170000,
                            "subsidy": 60000,
                            "net_cost": 110000,
                            "down_payment": 15000,
                            "loan_amount": 95000,
                            "emi_5y": 1980,
                            "emi_10y": 1140,
                            "is_recommended": False
                        },
                        {
                            "kw": 3,
                            "units": "300 - 375 Units",
                            "savings": "₹2,500 - ₹3,000",
                            "system_price": 220000,
                            "subsidy": 78000,
                            "net_cost": 142000,
                            "down_payment": 20000,
                            "loan_amount": 122000,
                            "emi_5y": 2400,
                            "emi_10y": 1350,
                            "is_recommended": True,
                            "badge": "Most Recommended for Homes"
                        },
                        {
                            "kw": 4,
                            "units": "380 - 500 Units",
                            "savings": "₹3,000 - ₹4,100",
                            "system_price": 295000,
                            "subsidy": 78000,
                            "net_cost": 217000,
                            "down_payment": 29500,
                            "loan_amount": 187500,
                            "emi_5y": 3720,
                            "emi_10y": 2010,
                            "is_recommended": False
                        },
                        {
                            "kw": 5,
                            "units": "500 - 600 Units",
                            "savings": "₹4,200 - ₹5,000",
                            "system_price": 360000,
                            "subsidy": 78000,
                            "net_cost": 282000,
                            "down_payment": 36000,
                            "loan_amount": 246000,
                            "emi_5y": 4880,
                            "emi_10y": 2590,
                            "is_recommended": False
                        },
                        {
                            "kw": 6,
                            "units": "600 - 710 Units",
                            "savings": "₹5,000 - ₹6,200",
                            "system_price": 435000,
                            "subsidy": 78000,
                            "net_cost": 357000,
                            "down_payment": 43500,
                            "loan_amount": 313500,
                            "emi_5y": 6207,
                            "emi_10y": 3253,
                            "is_recommended": False
                        },
                        {
                            "kw": 10,
                            "units": "1,000 - 1,200 Units",
                            "savings": "₹10,000 - ₹12,000",
                            "system_price": 620000,
                            "subsidy": 78000,
                            "net_cost": 542000,
                            "down_payment": 62000,
                            "loan_amount": 480000,
                            "emi_5y": 9504,
                            "emi_10y": 4902,
                            "is_recommended": False
                        }
                    ]
                }
            },
            {
                "section_type": "media_gallery",
                "section_key": "installation_gallery",
                "title": "Real Rooftop Installations Showcase (ఫోటో గ్యాలరీ & వీడియోలు)",
                "subtitle": "Over 3,000+ happy homes and businesses powered across Andhra Pradesh & Telangana",
                "content_variants": {
                    "en": {
                        "title": "Real Rooftop Installations Showcase",
                        "subtitle": "Explore our recent on-grid rooftop solar plants and customer handover videos."
                    },
                    "te": {
                        "title": "వాస్తవ సోలార్ ప్రాజెక్టుల గ్యాలరీ & వీడియోలు",
                        "subtitle": "మా నిపుణులు విజయవంతంగా పూర్తి చేసిన రూఫ్‌టాప్ సోలార్ ప్రాజెక్టులు మరియు కస్టమర్ల అనుభవాలు."
                    }
                },
                "media_gallery": [
                    {
                        "url": "/public/images/solar_installations/myntreal_har_ghar_solar_offer.jpg",
                        "caption": "MyntReal Har Ghar Solar — Official Mega Discount Offer (₹1,99,999/-)",
                        "tag": "Mega Offer ₹1,99,999",
                        "location": "Limited Period Offer"
                    },
                    {
                        "url": "/public/images/solar_installations/kuruvada_solar_customer.jpg",
                        "caption": "Kuruvada, Andhra Pradesh — 3 kW Rooftop Solar System Installation",
                        "tag": "Kuruvada (Lat 17.61° N)",
                        "location": "Kuruvada, Andhra Pradesh"
                    },
                    {
                        "url": "/public/images/solar_installations/krishnadevipeta_solar_customer.jpg",
                        "caption": "Krishnadevipeta, Andhra Pradesh — 3 kW On-Grid Solar Plant",
                        "tag": "Krishnadevipeta (Lat 17.67° N)",
                        "location": "Krishnadevipeta, Andhra Pradesh"
                    },
                    {
                        "url": "/public/images/solar_installations/pothavaram_solar_customer.jpg",
                        "caption": "Pothavaram, Andhra Pradesh — Premium Rooftop Solar Power Array",
                        "tag": "Pothavaram (Lat 17.64° N)",
                        "location": "Pothavaram, Andhra Pradesh"
                    },
                    {
                        "url": "/public/images/solar_installations/komaravolu_solar_customer.jpg",
                        "caption": "Komaravolu, Andhra Pradesh — Elevated HDG Solar Structure",
                        "tag": "Komaravolu (Lat 17.70° N)",
                        "location": "Komaravolu, Andhra Pradesh"
                    },
                    {
                        "url": "/public/images/solar_installations/ap_solar_customer_1.jpg",
                        "caption": "Andhra Pradesh — Commercial & Home Rooftop Solar System",
                        "tag": "Andhra Pradesh",
                        "location": "Andhra Pradesh"
                    },
                    {
                        "url": "/public/images/solar_installations/ap_solar_customer_2.jpg",
                        "caption": "Andhra Pradesh — 5 kW High-Capacity Rooftop Solar Array",
                        "tag": "High Capacity 5 kW",
                        "location": "Andhra Pradesh"
                    }], "configuration": {
                    "auto_play_interval_ms": 3000,
                    "enable_lightbox": True,
                    "videos": [
                        {
                            "title": "MyntReal Har Ghar Solar — Real Customer Installation & Net Metering Walkthrough",
                            "youtube_id": "yE4BF_L81D8",
                            "url": "https://youtu.be/yE4BF_L81D8?si=hpi-HiV-ujmpjCBf",
                            "embed_url": "https://www.youtube-nocookie.com/embed/yE4BF_L81D8"
                        },
                        {
                            "title": "3 kW On-Grid Solar Plant Performance & Zero Electric Bill Customer Experience",
                            "youtube_id": "qpEGtGN5Kck",
                            "url": "https://youtu.be/qpEGtGN5Kck?si=QniSKdihEtFTAYxE",
                            "embed_url": "https://www.youtube-nocookie.com/embed/qpEGtGN5Kck"
                        }
                    ]
                }
            },
            {
                "section_type": "highlights_grid",
                "section_key": "banking",
                "title": "Authorized Banking & Financing Partners (బ్యాంకింగ్ సదుపాయం)",
                "subtitle": "Get up to 90% collateral-free solar financing with pre-approved nationalised bank schemes (SBI, BoB, Canara, Union, Indian Bank, PNB)",
                "content_variants": {
                    "en": {
                        "title": "Authorized Banking & Financing Partners",
                        "subtitle": "Easy financing options with zero collateral, tenure up to 10 years and direct government DBT subsidy adjustment."
                    },
                    "te": {
                        "title": "బ్యాంకింగ్ & సులభ వాయిదాల భాగస్వాములు",
                        "subtitle": "ఎలాంటి పూచీకత్తు (Collateral) లేకుండా 10 సంవత్సరాల వరకు సులభ వాయిదాలలో జాతీయ బ్యాంకుల ద్వారా రుణాలు."
                    }
                },
                "configuration": {
                    "banks": [
                        {
                            "name": "State Bank of India (SBI)",
                            "badge": "Surya Ghar Loan",
                            "logo": "/public/images/banks/sbi.svg",
                            "tenure": "Up to 10 Years",
                            "highlights": "Zero Collateral • Direct DBT Subsidy Adjustment"
                        },
                        {
                            "name": "Bank of Baroda",
                            "badge": "Baroda Solar",
                            "logo": "/public/images/banks/bob.svg",
                            "tenure": "Up to 10 Years",
                            "highlights": "Collateral Free • Instant In-Principle Online Sanction"
                        },
                        {
                            "name": "Canara Bank",
                            "badge": "Canara Green",
                            "logo": "/public/images/banks/canara.svg",
                            "tenure": "Up to 10 Years",
                            "highlights": "Green Energy Priority Lending • Quick Processing"
                        },
                        {
                            "name": "Union Bank of India",
                            "badge": "Union Solar",
                            "logo": "/public/images/banks/union.svg",
                            "tenure": "Up to 10 Years",
                            "highlights": "Zero Collateral • Easy Digital Loan Application"
                        },
                        {
                            "name": "Indian Bank",
                            "badge": "Solar Scheme",
                            "logo": "/public/images/banks/indian-bank.svg",
                            "tenure": "Up to 10 Years",
                            "highlights": "Minimal Documentation • Doorstep Verification"
                        },
                        {
                            "name": "Andhra Pradesh Grameena Bank (APGB)",
                            "badge": "Surya Ghar Mitra",
                            "logo": "/public/images/banks/apgb.svg",
                            "tenure": "Up to 10 Years",
                            "highlights": "Regional PM Surya Ghar Partner • Low Margin Money"
                        }
                    ]
                }
            },
            {
                "section_type": "highlights_grid",
                "section_key": "benefits",
                "title": "Why Switch to Rooftop Solar with MyntReal?",
                "subtitle": "Engineering excellence meets seamless government subsidy execution",
                "content_variants": {
                    "en": {
                        "title": "Why Switch to Rooftop Solar with MyntReal?",
                        "subtitle": "Engineering excellence meets seamless government subsidy execution"
                    },
                    "te": {
                        "title": "MyntReal సోలార్ ఎందుకు ఎంచుకోవాలి?",
                        "subtitle": "అత్యుత్తమ సాంకేతిక పరిజ్ఞానం మరియు వేగవంతమైన ప్రభుత్వ సబ్సిడీ ప్రాసెసింగ్"
                    },
                    "hi": {
                        "title": "MyntReal सोलर ही क्यों चुनें?",
                        "subtitle": "विश्वस्तरीय तकनीक और तुरंत सरकारी सब्सिडी का लाभ"
                    },
                    "ta": {
                        "title": "MyntReal சோலாரை ஏன் தேர்வு செய்ய வேண்டும்?",
                        "subtitle": "சிறந்த பொறியியல் தரம் மற்றும் விரைவான அரசு மானிய உதவி"
                    }
                },
                "configuration": {
                    "cards": [
                        {"icon": "solar_panel", "title": "Tier-1 Mono-PERC Bi-Facial Panels", "desc": "Up to 22.5% efficiency rating for maximum power generation even in low-light conditions."},
                        {"icon": "receipt_long", "title": "Direct Govt Subsidy (DBT)", "desc": "Get up to ₹78,000 direct bank transfer under PM Surya Ghar Muft Bijli Yojana."},
                        {"icon": "security", "title": "25-Year Generation Guarantee", "desc": "Tier-1 linear performance warranty ensuring sustained output for decades."},
                        {"icon": "settings_suggest", "title": "Turnkey Net Metering", "desc": "End-to-end DISCOM approvals, CEIG inspection, and bi-directional meter setup handled completely by our team."}
                    ]
                }
            },
            {
                "section_type": "packages_pricing",
                "section_key": "packages",
                "title": "Popular Solar Plant Capacities & Packages",
                "subtitle": "Customized for 1BHK-3BHK villas, commercial showrooms, factories & hospitals",
                "content_variants": {
                    "en": {"title": "Popular Solar Plant Capacities & Packages", "subtitle": "Customized for villas, commercial establishments, and industrial units"},
                    "te": {"title": "ప్రముఖ సోలార్ ప్లాంట్ సామర్థ్యాలు & ప్యాకేజీలు", "subtitle": "గృహాలు, వ్యాపారాలు మరియు పరిశ్రమల కోసం ప్రత్యేక ప్యాకేజీలు"},
                    "hi": {"title": "प्रमुख सोलर प्लांट क्षमताएं और पैकेज", "subtitle": "घरों, दुकानों और फैक्ट्रियों के लिए उपयुक्त विकल्प"},
                    "ta": {"title": "பிரபலமான சோலார் திட்டங்கள் மற்றும் கட்டணங்கள்", "subtitle": "வீடுகள், வணிக வளாகங்கள் மற்றும் தொழிற்சாலைகளுக்கான விருப்பங்கள்"}
                },
                "configuration": {
                    "plans": [
                        {
                            "name": "3 kW Rooftop System",
                            "ideal_for": "1-3 BHK Homes / 300-375 Units monthly",
                            "price": "₹1,99,999",
                            "subsidy": "₹78,000 Govt Subsidy",
                            "net_cost": "₹1,21,999 Effective Price",
                            "features": ["3 kW High-Efficiency Inverter", "Tier-1 Mono PERC Panels (Goldi / Navgrun / APS)", "Standard Heavy-Duty Structure", "Net Metering Documentation & Liaison Included", "🔥 Special: Get Solar for ₹1 Booking Available"],
                            "is_popular": True
                        },
                        {
                            "name": "5 kW Hybrid System",
                            "ideal_for": "Duplexes & Independent Villas / 500-600 Units",
                            "price": "₹3,60,000",
                            "subsidy": "₹78,000 Govt Subsidy",
                            "net_cost": "₹2,82,000 Effective Price",
                            "features": ["5 kW Smart Inverter with Battery Provision", "Tier-1 Mono Panels with 25-Year Warranty", "Elevated Heavy-Duty HDG Structure", "Remote IoT Mobile Monitoring App", "🔥 Special: 100% Bank Financed with ₹1 Token"],
                            "is_popular": False
                        },
                        {
                            "name": "10 kW Commercial On-Grid",
                            "ideal_for": "Offices, Showrooms, Clinics & Schools / 1,000-1,200 Units",
                            "price": "₹6,20,000",
                            "subsidy": "₹0 DBT (Residential Only)",
                            "net_cost": "₹6,20,000 Total Investment",
                            "features": ["10 kW Three-Phase High-Capacity Inverter", "High-Generation Half-Cut Arrays", "Wind-Resistant Aluminium/HDG Mounting", "2-Year Complimentary Maintenance SLA", "🔥 40% Accelerated Depreciation & GST Input Credit"],
                            "is_popular": False
                        }
                    ]
                }
            },
            {
                "section_type": "process_workflow",
                "section_key": "process",
                "title": "Seamless 4-Step Installation Journey",
                "subtitle": "From site survey to net metering switch-on in under 21 days",
                "content_variants": {
                    "en": {"title": "Seamless 4-Step Installation Journey", "subtitle": "From site survey to net metering switch-on in under 21 days"},
                    "te": {"title": "సులభమైన 4-దశల సోలార్ ఏర్పాటు ప్రక్రియ", "subtitle": "సైట్ సర్వే నుండి నెట్ మీటరింగ్ ప్రారంభం వరకు కేవలం 21 రోజుల్లో"},
                    "hi": {"title": "सरल 4-चरणीय सोलर इन्स्टॉलेशन प्रक्रिया", "subtitle": "साइट सर्वे से लेकर नेट मीटरिंग चालू होने तक मात्र 21 दिनों में"},
                    "ta": {"title": "எளிய 4-படி சோலார் நிறுவல் முறை", "subtitle": "தள ஆய்வு முதல் மின் இணைப்பு வரை 21 நாட்களில்"}
                },
                "configuration": {
                    "steps": [
                        {"step": 1, "title": "Technical Site Audit", "desc": "Detailed shadow analysis, roof load assessment, and electrical load profiling by certified engineers."},
                        {"step": 2, "title": "Engineering & DISCOM Approval", "desc": "Custom CAD structural design and complete DISCOM feasibility filing."},
                        {"step": 3, "title": "Certified Installation", "desc": "Precision installation using lightning arresters, dual earthing pits, and surge protection devices (SPD)."},
                        {"step": 4, "title": "Net Metering & Subsidy Release", "desc": "Bi-directional meter installation, grid synchronization, and DBT subsidy disbursement into your bank."}
                    ]
                }
            },
            {
                "section_type": "faqs",
                "section_key": "faqs",
                "title": "Frequently Asked Questions",
                "subtitle": "Common queries regarding solar rooftop, subsidies, and maintenance",
                "content_variants": {
                    "en": {
                        "title": "Frequently Asked Questions (FAQs)",
                        "subtitle": "Everything you need to know about rooftop solar, net metering & DBT subsidies",
                        "faqs": [
                            {"q": "How does net metering work?", "a": "During daytime, excess solar power generated is sent to the DISCOM grid. At night, you draw power from the grid. You only pay for net units consumed (Import - Export), or receive credit units in your account for excess power sent!"},
                            {"q": "What is the government subsidy policy? Do commercial premises get subsidy?", "a": "Under PM Surya Ghar Muft Bijli Yojana, direct bank transfer (DBT) subsidies up to ₹78,000 apply exclusively to Residential rooftops (1kW: ₹30,000, 2kW: ₹60,000, 3kW+: ₹78,000). Commercial and industrial setups do not receive DBT cash subsidies, but benefit substantially from 40% Accelerated Depreciation tax write-off and 18% GST input tax credit."},
                            {"q": "How does the 'Get Solar for ₹1' scheme work?", "a": "Under our authorized partner bank program (SBI, Bank of Baroda, Canara, Union, Indian Bank, APGB), homeowners can book with a ₹1 token. The balance is 100% financed via zero-collateral PM Surya Ghar loans at concessional interest. Monthly bill savings (₹2,500-₹3,000/mo) comfortably exceed the 10-year monthly EMI (₹1,350/mo), giving you instant net positive savings!"},
                            {"q": "Will solar panels generate electricity on cloudy or rainy days?", "a": "Yes. Solar panels generate power from ambient daylight UV rays even during overcast weather, typically yielding 30% to 50% of peak output. Any deficit is seamlessly drawn from the grid without interruption."},
                            {"q": "What warranty and maintenance support is provided?", "a": "All Tier-1 solar panels (Goldi, Navgrun, APS, Waaree, Adani, Vikram, ReNew, TATA) come with a 25-Year Linear Performance Warranty (guaranteeing 80%+ output after 25 years) and 10-12 year product warranty. Inverters carry a 5 to 10 year manufacturer warranty, backed by remote IoT app monitoring."}
                        ]
                    },
                    "te": {
                        "title": "తరచుగా అడిగే ప్రశ్నలు & సమాధానాలు (FAQs)",
                        "subtitle": "రూఫ్‌టాప్ సోలార్, నెట్ మీటరింగ్ మరియు పీఎం సూర్య ఘర్ సబ్సిడీ గురించి సమగ్ర వివరాలు",
                        "faqs": [
                            {"q": "నెట్ మీటరింగ్ (Net Metering) ఎలా పనిచేస్తుంది?", "a": "పగటి వేళల్లో మీ సోలార్ ప్లాంట్ ద్వారా ఉత్పత్తి అయ్యే అదనపు విద్యుత్ ప్రభుత్వ గ్రిడ్ (APEPDCL / APSPDCL) కు వెళ్తుంది. రాత్రి సమయాల్లో మీరు గ్రిడ్ నుండి విద్యుత్‌ను వాడుకుంటారు. నెలవారీ బిల్లులో మీరు వాడుకున్న విద్యుత్ మైనస్ పంపిన విద్యుత్ (Net Units) కు మాత్రమే చెల్లించాలి. అదనంగా ఉత్పత్తి అయితే యూనిట్లు క్రెడిట్ రూపంలో మీ ఖాతాలో జమ అవుతాయి."},
                            {"q": "ప్రభుత్వ సబ్సిడీ ఎవరికి లభిస్తుంది? కమర్షియల్ ప్రాంగణాలకు సబ్సిడీ ఉంటుందా?", "a": "పీఎం సూర్య ఘర్ ముఫ్త్ బిజిలీ యోజన కింద ₹78,000 వరకు నేరుగా బ్యాంక్ ఖాతాలో జమయ్యే DBT సబ్సిడీ కేవలం గృహాలకు (Residential) మాత్రమే వర్తిస్తుంది. కమర్షియల్ మరియు పరిశ్రమలకు నగదు సబ్సిడీ వర్తించదు; అయితే వారికి 40% యాక్సిలరేటెడ్ డిప్రిసియేషన్ (ఇన్‌కమ్ ట్యాక్స్ రాయితీ) మరియు 18% GST ఇన్‌పుట్ క్రెడిట్ లభిస్తాయి, దీనివల్ల భారీ పన్ను ఆదా అవుతుంది."},
                            {"q": "రూపాయికే సోలార్ (₹1 Solar Scheme) ఎలా పనిచేస్తుంది?", "a": "మా అధీకృత బ్యాంకుల (SBI, BoB, కెనరా, యూనియన్, ఇండియన్ బ్యాంక్, APGB) ద్వారా మీరు కేవలం ₹1 టోకెన్ అమౌంట్‌తో సోలార్ బుక్ చేసుకోవచ్చు. మిగిలిన మొత్తం ఎలాంటి పూచీకత్తు (Collateral) లేకుండా 10 సంవత్సరాల తక్కువ వడ్డీ రుణంగా లభిస్తుంది. మీరు నెల నెలా ఆదా చేసే కరెంట్ బిల్లు (నెలకు ₹2,500 - ₹3,000) మీ లోన్ EMI (నెలకు ₹1,350) కంటే ఎక్కువగా ఉంటుంది, కాబట్టి మొదటి నెల నుండే మీకు నికర లాభం చేకూరుతుంది."},
                            {"q": "వర్షం పడినప్పుడు లేదా మబ్బులు పట్టిన రోజుల్లో సోలార్ విద్యుత్ ఉత్పత్తి అవుతుందా?", "a": "అవును, ఖచ్చితంగా ఉత్పత్తి అవుతుంది. సోలార్ ప్యానెల్స్ కేవలం ఎండపైనే కాకుండా పగటి సహజ కాంతి (Ambient Light) పై కూడా పనిచేస్తాయి. మబ్బులు పట్టినప్పుడు కూడా ఆధునిక మోనో-పెర్క్ ప్యానెల్స్ 30% నుండి 50% వరకు విద్యుత్‌ను ఉత్పత్తి చేస్తాయి. ఏవైనా తగ్గుదల ఉంటే గ్రిడ్ విద్యుత్ నిరంతరాయంగా సరఫరా అవుతుంది."},
                            {"q": "ప్యానెల్స్ మరియు ఇన్వర్టర్లకు వారంటీ ఎంత కాలం ఉంటుంది?", "a": "మేము అందించే అన్ని అగ్రశ్రేణి బ్రాండ్లు (Goldi, Navgrun, APS, Waaree, Adani, Vikram, ReNew, TATA) 25 సంవత్సరాల లీనియర్ పర్ఫార్మెన్స్ వారంటీని మరియు 10-12 సంవత్సరాల ప్రొడక్ట్ వారంటీని కలిగి ఉంటాయి. ఇన్వర్టర్లకు 5 నుండి 10 సంవత్సరాల వారంటీ ఉంటుంది. అలాగే మొబైల్ యాప్ ద్వారా విద్యుత్ ఉత్పత్తిని పర్యవేక్షించే IoT సదుపాయం కూడా ఉంటుంది."}
                        ]
                    },
                    "hi": {
                        "title": "अक्सर पूछे जाने वाले सवाल (FAQs)",
                        "subtitle": "रूफटॉप सोलर, नेट मीटरिंग और सरकारी सब्सिडी के बारे में संपूर्ण जानकारी",
                        "faqs": [
                            {"q": "नेट मीटरिंग (Net Metering) कैसे काम करता है?", "a": "दिन के समय आपके सोलर प्लांट द्वारा उत्पन्न अतिरिक्त बिजली सरकारी ग्रिड में भेजी जाती है। रात में आप ग्रिड से बिजली लेते हैं। महीने के अंत में, आपको केवल कुल शुद्ध खपत (इम्पोर्ट - एक्सपोर्ट) का ही बिल देना होता है। यदि उत्पादन अधिक है, तो यूनिट्स अगले बिल में क्रेडिट हो जाती हैं।"},
                            {"q": "सरकारी सब्सिडी किसे मिलती है? क्या कमर्शियल प्रतिष्ठानों को भी सब्सिडी मिलती है?", "a": "पीएम सूर्य घर मुफ्त बिजली योजना के तहत ₹78,000 तक की सीधी डीबीटी सब्सिडी केवल आवासीय घरों (Residential) के लिए लागू है। कमर्शियल और औद्योगिक प्रतिष्ठानों को नकद सब्सिडी नहीं मिलती, लेकिन उन्हें 40% त्वरित मूल्यह्रास (Accelerated Depreciation - इनकम टैक्स बचत) और 18% जीएसटी इनपुट क्रेडिट का पूरा लाभ मिलता है।"},
                            {"q": "₹1 में सोलर (Get Solar for ₹1) योजना कैसे काम करती है?", "a": "अधिकृत बैंकों (SBI, BoB, Canara, Union, Indian Bank, APGB) के माध्यम से आप केवल ₹1 में सोलर बुक कर सकते हैं। शून्य गारंटी (Collateral-Free) पर 10 साल तक का सस्ता लोन उपलब्ध है। आपकी मासिक बिजली बिल की बचत (₹2,500 - ₹3,000) बैंक की मासिक ईएमआई (₹1,350) से अधिक होती है, जिससे पहले महीने से ही शुद्ध बचत शुरू हो जाती है।"},
                            {"q": "क्या बारिश या बादलों वाले दिनों में सोलर बिजली बनती है?", "a": "हाँ, बिल्कुल बनती है। सोलर पैनल केवल सीधी धूप से ही नहीं, बल्कि सामान्य दिन के उजाले से भी काम करते हैं। बादलों वाले दिनों में भी आधुनिक मोनो-पर्क पैनल्स 30% से 50% तक बिजली बनाते हैं। किसी भी कमी को ग्रिड द्वारा निर्बाध रूप से पूरा किया जाता है।"},
                            {"q": "सोलर पैनल और इन्वर्टर पर क्या वारंटी मिलती है?", "a": "हमारे सभी शीर्ष ब्रांड्स (Goldi, Navgrun, APS, Waaree, Adani, Vikram, ReNew, TATA) पर 25 साल की लीनियर परफॉर्मेंस वारंटी और 10-12 साल की प्रोडक्ट वारंटी मिलती है। इन्वर्टर पर 5 से 10 साल की वारंटी और मोबाइल ऐप से लाइव मॉनिटरिंग की सुविधा दी जाती है।"}
                        ]
                    },
                    "ta": {
                        "title": "அடிக்கடி கேட்கப்படும் கேள்விகள் (FAQs)",
                        "subtitle": "கூரை சூரிய மின்சக்தி, நெட் மீட்டரிங் மற்றும் அரசு மானியம் பற்றிய முழு விவரங்கள்",
                        "faqs": [
                            {"q": "நெட் மீட்டரிங் (Net Metering) எவ்வாறு செயல்படுகிறது?", "a": "பகல் நேரத்தில் உங்கள் சோலார் மூலம் உற்பத்தியாகும் உபரி மின்சாரம் அரசு மின் கட்டமைப்புக்கு அனுப்பப்படும். இரவு நேரத்தில் நீங்கள் கிரிட்டிலிருந்து மின்சாரத்தை எடுத்துக்கொள்வீர்கள். இறுதியில் நிகர பயன்பாட்டிற்கு (இறக்குமதி - ஏற்றுமதி) மட்டுமே பில் கணக்கிடப்படும்."},
                            {"q": "அரசு மானியம் யாருக்கு கிடைக்கும்? வணிக நிறுவனங்களுக்கு மானியம் உண்டா?", "a": "பிஎம் சூர்யா கர் திட்டத்தின் கீழ் ரூ.78,000 வரையிலான நேரடி மானியம் குடியிருப்பு வீடுகளுக்கு (Residential) மட்டுமே பொருந்தும். வணிக மற்றும் தொழில் நிறுவனங்களுக்கு நேரடி மானியம் கிடையாது, ஆனால் 40% வரிவிலக்கு (Accelerated Depreciation) மற்றும் 18% ஜிஎஸ்டி இன்புட் கிரெடிட் போன்ற பெரும் வரிச் சலுகைகள் கிடைக்கும்."},
                            {"q": "ரூ.1 சோலார் திட்டம் (Get Solar for ₹1) எவ்வாறு செயல்படுகிறது?", "a": "அங்கீகரிக்கப்பட்ட வங்கிகள் மூலம் வெறும் ரூ.1 முன்பணத்தில் நீங்கள் சோலார் திட்டத்தை பதிவு செய்யலாம். எவ்வித பிணையமும் (Collateral) இன்றி 10 ஆண்டு எளிய தவணையில் கடன் கிடைக்கும். உங்கள் மாதாந்திர மின் கட்டண சேமிப்பு (ரூ.2,500 - 3,000) மாதாந்திர தவணையை (ரூ.1,350) விட அதிகமாக இருப்பதால் முதல் மாதத்திலிருந்தே லாபம் கிடைக்கும்."},
                            {"q": "மழைக்காலங்கள் அல்லது மேகமூட்டமான நாட்களில் மின் உற்பத்தி நடைபெறுமா?", "a": "ஆம், நிச்சயமாக நடைபெறும். சோலார் பேனல்கள் பகல் வெளிச்சத்தின் மூலமும் இயங்கும். மேகமூட்டமான நாட்களிலும் நவீன மோனோ-பெர்க் பேனல்கள் 30% முதல் 50% வரை மின் உற்பத்தி செய்யும்."},
                            {"q": "சோலார் பேனல்கள் மற்றும் இன்வெர்ட்டர்களுக்கு என்ன உத்தரவாதம் வழங்கப்படுகிறது?", "a": "அனைத்து முன்னணி சோலார் பேனல்களுக்கும் 25 ஆண்டுகள் செயல்திறன் உத்தரவாதமும், இன்வெர்ட்டர்களுக்கு 5 முதல் 10 ஆண்டுகள் வாரண்டியும் வழங்கப்படுகிறது. அத்துடன் மொபைல் ஆப் மூலம் நேரடி கண்காணிப்பு வசதியும் உண்டு."}
                        ]
                    }
                },
                "configuration": {
                    "faqs": [
                        {"q": "How does net metering work?", "a": "During daytime, excess solar power generated is sent to the DISCOM grid. At night, you draw power from the grid. You only pay for net units consumed (Import - Export), or receive credit units in your account for excess power sent!"},
                        {"q": "What is the government subsidy policy? Do commercial premises get subsidy?", "a": "Under PM Surya Ghar Muft Bijli Yojana, direct bank transfer (DBT) subsidies up to ₹78,000 apply exclusively to Residential rooftops (1kW: ₹30,000, 2kW: ₹60,000, 3kW+: ₹78,000). Commercial and industrial setups do not receive DBT cash subsidies, but benefit substantially from 40% Accelerated Depreciation tax write-off and 18% GST input tax credit."},
                        {"q": "How does the 'Get Solar for ₹1' scheme work?", "a": "Under our authorized partner bank program (SBI, Bank of Baroda, Canara, Union, Indian Bank, APGB), homeowners can book with a ₹1 token. The balance is 100% financed via zero-collateral PM Surya Ghar loans at concessional interest. Monthly bill savings (₹2,500-₹3,000/mo) comfortably exceed the 10-year monthly EMI (₹1,350/mo), giving you instant net positive savings!"},
                        {"q": "Will solar panels generate electricity on cloudy or rainy days?", "a": "Yes. Solar panels generate power from ambient daylight UV rays even during overcast weather, typically yielding 30% to 50% of peak output. Any deficit is seamlessly drawn from the grid without interruption."},
                        {"q": "What warranty and maintenance support is provided?", "a": "All Tier-1 solar panels (Goldi, Navgrun, APS, Waaree, Adani, Vikram, ReNew, TATA) come with a 25-Year Linear Performance Warranty (guaranteeing 80%+ output after 25 years) and 10-12 year product warranty. Inverters carry a 5 to 10 year manufacturer warranty, backed by remote IoT app monitoring."}
                    ]
                }
            },
            {
                "section_type": "contact_cta",
                "section_key": "cta",
                "title": "Ready to Zero Out Your Electric Bill? (ఉచిత సైట్ సర్వే పొందండి)",
                "subtitle": "Connect with our certified solar engineers for an instant savings calculation & site visit.",
                "content_variants": {
                    "en": {"title": "Ready to Zero Out Your Electric Bill?", "subtitle": "Connect with our certified solar engineers for an instant savings calculation & site visit."},
                    "te": {"title": "మీ కరెంట్ బిల్లును సున్నా చేయాలనుకుంటున్నారా?", "subtitle": "ఉచిత సైట్ సర్వే మరియు పొదుపు లెక్కల కోసం మా ఇంజనీర్లతో సంప్రదించండి."},
                    "hi": {"title": "क्या आप अपना बिजली बिल शून्य करने के लिए तैयार हैं?", "subtitle": "तुरंत बचत की गणना और फ्री साइट विजिट के लिए हमारे सोलर इंजीनियर से बात करें।"},
                    "ta": {"title": "உங்கள் மின் கட்டணத்தை குறைக்க தயாரா?", "subtitle": "இலவச தள ஆய்வு மற்றும் சேமிப்பு கணக்கீட்டிற்கு எங்கள் சோலார் பொறியாளரை தொடர்பு கொள்ளவும்."}
                },
                "configuration": {
                    "whatsapp_number": "918585852738",
                    "prefill_message": "Hello! I am interested in Har Ghar Solar Rooftop Solutions for my premises. Please share quotation and arrange site audit.",
                    "office_address": "D.No. 4-48, Main Road, Saripalli, Pendurthy, Visakhapatnam, AP - 531173",
                    "working_hours": "Mon - Sat: 9:00 AM - 7:30 PM",
                    "helpline": "+91 858585 2738"
                }
            }
        ],
        "items": [
            {
                "item_type": "PRODUCT",
                "item_code": "SOL-3KW-RES",
                "title": "3 kW High-Efficiency On-Grid Rooftop System",
                "subtitle": "Ideal for 2BHK/3BHK residential homes with ₹78,000 PM Surya Ghar subsidy",
                "specifications": [
                    {"label": "Panel Tech", "value": "Tier-1 Mono-PERC Bi-Facial 545W"},
                    {"label": "Inverter", "value": "3 kW Pure Sine Wave Grid-Tied"},
                    {"label": "Daily Generation", "value": "12 - 15 Units/day"},
                    {"label": "Roof Space Needed", "value": "approx. 250 - 300 sq.ft."},
                    {"label": "Warranty", "value": "25-year performance warranty"}
                ],
                "pricing": {"base_price": 185000, "subsidy_amount": 78000, "net_cost": 107000, "currency": "INR"},
                "media_urls": ["https://images.unsplash.com/photo-1509391365360-2e959784a276?auto=format&fit=crop&w=800&q=80"],
                "badges": ["Most Popular", "₹78,000 Subsidy"]
            },
            {
                "item_type": "PRODUCT",
                "item_code": "SOL-5KW-HYB",
                "title": "5 kW Hybrid Smart Solar Power System",
                "subtitle": "Uninterrupted power with lithium battery storage and grid export capability",
                "specifications": [
                    {"label": "Panel Tech", "value": "TopCon 580W Bifacial Panels"},
                    {"label": "Inverter", "value": "5 kW Hybrid Intelligent Controller"},
                    {"label": "Daily Generation", "value": "20 - 25 Units/day"},
                    {"label": "Backup Battery", "value": "Lithium LiFePO4 5.12kWh Compatible"},
                    {"label": "Roof Space Needed", "value": "approx. 450 - 500 sq.ft."}
                ],
                "pricing": {"base_price": 295000, "subsidy_amount": 78000, "net_cost": 217000, "currency": "INR"},
                "media_urls": ["https://images.unsplash.com/photo-1508873696983-2df5293cb32f?auto=format&fit=crop&w=800&q=80"],
                "badges": ["Hybrid Storage", "24/7 Backup"]
            },
            {
                "item_type": "PRODUCT",
                "item_code": "SOL-10KW-COM",
                "title": "10 kW Three-Phase Commercial Solar Solution",
                "subtitle": "Engineered for showrooms, hospitals, schools, and MSME manufacturing facilities",
                "specifications": [
                    {"label": "Panel Tech", "value": "Tier-1 Mono PERC 550W Module"},
                    {"label": "Inverter", "value": "10 kW 3-Phase Smart Grid Inverter"},
                    {"label": "Daily Generation", "value": "42 - 50 Units/day"},
                    {"label": "Payback Period", "value": "Under 3 years with 40% Tax Depreciation"},
                    {"label": "Structure", "value": "HDG Elevated Walkway Compatible"}
                ],
                "pricing": {"base_price": 485000, "subsidy_amount": 0, "net_cost": 485000, "tax_benefit": "40% Depreciation", "currency": "INR"},
                "media_urls": ["https://images.unsplash.com/photo-1545259741-2ea3ebf61fa3?auto=format&fit=crop&w=800&q=80"],
                "badges": ["Commercial High Yield", "Tax Depreciation"]
            }
        ]
    },
    {
        "segment_code": "INDUSTRIAL_HUB",
        "slug": "industrial-hub-franchise",
        "title": "MyntReal Hub \u2014 5-in-1 Investor Franchise",
        "subtitle": "One Store, Five High-Demand Opportunities | Turnkey Investor Franchise Prospectus",
        "summary": "Invest in the future with MyntReal Hub. A single \u20b912\u201315 Lakhs franchise investment unlocks 5 high-demand revenue streams under one roof: Manthra EV Dealership, Har Ghar Solar Rooftop EPC, VGK Care Insurance Advisory, VGK Real Dreams Townships, and EVolution Training Centre (ETC). 6\u20139 months break-even, \u20b919.80 Lakhs base annual net profit, and complete turnkey deliverables including Free PC, 43\" Smart TV, and Color Printer.",
        "hero_media_url": "/public/hub/Assets/hero-bg.webp",
        "pdf_brochure_url": "/public/hub/Assets/myntreal_investor_franchise_brochure.pdf",
        "theme_config": {
                "primary_color": "#059669",
                "accent_color": "#f59e0b",
                "dark_mode": False
        },
        "default_language": "en",
        "active_languages": [
                "en",
                "te",
                "hi",
                "ta"
        ],
        "sections": [
                {
                        "section_type": "hero",
                        "section_key": "hero",
                        "title": "Own a Multi-Business Franchise Hub in Your Area",
                        "subtitle": "1 Hub • 5 High-Growth Business Streams • ₹12 to 15 Lakhs Investment • Payback in 6 to 9 Months",
                        "content_variants": {
                                "en": {
                                        "badge": "Official Investor Franchise Offer • One Store, 5 Businesses",
                                        "title": "Own a Multi-Business Franchise Hub in Your Area",
                                        "subtitle": "One Store • 5 Profitable Clean Energy & Rural Retail Revenue Streams • Payback in 6 to 9 Months",
                                        "cta_primary": "Apply for Territory Exclusivity",
                                        "cta_secondary": "Explore 5 Business Streams"
                                },
                                "te": {
                                        "badge": "\u0c05\u0c27\u0c3f\u0c15\u0c3e\u0c30\u0c3f\u0c15 \u0c07\u0c28\u0c4d\u0c35\u0c46\u0c38\u0c4d\u0c1f\u0c30\u0c4d \u0c2b\u0c4d\u0c30\u0c3e\u0c02\u0c1a\u0c48\u0c1c\u0c4d \u0c06\u0c39\u0c4d\u0c35\u0c3e\u0c28\u0c02 \u2022 \u0c12\u0c15\u0c47 \u0c38\u0c4d\u0c1f\u0c4b\u0c30\u0c4d, 5 \u0c35\u0c4d\u0c2f\u0c3e\u0c2a\u0c3e\u0c30\u0c3e\u0c32\u0c41",
                                        "title": "\u0c2e\u0c40 \u0c0f\u0c30\u0c3f\u0c2f\u0c3e\u0c32\u0c4b \u0c2e\u0c48\u0c02\u0c1f\u0c4d \u0c30\u0c3f\u0c2f\u0c32\u0c4d 5-\u0c07\u0c28\u0c4d-1 \u0c2e\u0c32\u0c4d\u0c1f\u0c40-\u0c2c\u0c3f\u0c1c\u0c3f\u0c28\u0c46\u0c38\u0c4d \u0c39\u0c2c\u0c4d \u0c2a\u0c4d\u0c30\u0c3e\u0c30\u0c02\u0c2d\u0c3f\u0c02\u0c1a\u0c02\u0c21\u0c3f",
                                        "subtitle": "\u0c12\u0c15\u0c47 \u0c38\u0c4d\u0c1f\u0c4b\u0c30\u0c4d \u2022 5 \u0c32\u0c3e\u0c2d\u0c26\u0c3e\u0c2f\u0c15 \u0c35\u0c4d\u0c2f\u0c3e\u0c2a\u0c3e\u0c30 \u0c30\u0c02\u0c17\u0c3e\u0c32\u0c41 \u2022 \u20b912 \u0c28\u0c41\u0c02\u0c21\u0c3f 15 \u0c32\u0c15\u0c4d\u0c37\u0c32 \u0c2a\u0c46\u0c1f\u0c4d\u0c1f\u0c41\u0c2c\u0c21\u0c3f \u2022 6-9 \u0c28\u0c46\u0c32\u0c32\u0c4d\u0c32\u0c4b \u0c2c\u0c4d\u0c30\u0c47\u0c15\u0c4d-\u0c08\u0c35\u0c46\u0c28\u0c4d",
                                        "cta_primary": "\u0c2e\u0c40 \u0c2e\u0c02\u0c21\u0c32\u0c4d \u0c1f\u0c46\u0c30\u0c3f\u0c1f\u0c30\u0c40 \u0c15\u0c4b\u0c38\u0c02 \u0c26\u0c30\u0c16\u0c3e\u0c38\u0c4d\u0c24\u0c41 \u0c1a\u0c47\u0c38\u0c41\u0c15\u0c4b\u0c02\u0c21\u0c3f",
                                        "cta_secondary": "5 \u0c35\u0c4d\u0c2f\u0c3e\u0c2a\u0c3e\u0c30 \u0c30\u0c02\u0c17\u0c3e\u0c32\u0c28\u0c41 \u0c1a\u0c42\u0c21\u0c02\u0c21\u0c3f"
                                }
                        },
                        "configuration": {
                                "stats": [
                                        {
                                                "value": "\u20b912\u201315L",
                                                "label": "Turnkey Investment"
                                        },
                                        {
                                                "value": "5 Streams",
                                                "label": "Multi-Revenue Store"
                                        },
                                        {
                                                "value": "\u20b919.8L/yr",
                                                "label": "Base Net Income"
                                        },
                                        {
                                                "value": "6\u20139 Mos",
                                                "label": "Break-Even Period"
                                        }
                                ],
                                "partners": [
                                        {
                                                "name": "Manthra EV",
                                                "logo": "/public/hub/Assets/ManthraEV_logo.png"
                                        },
                                        {
                                                "name": "Har Ghar Solar",
                                                "logo": "/public/hub/Assets/Solar-PM.webp"
                                        },
                                        {
                                                "name": "VGK Care (40+ Insurers)",
                                                "logo": "/public/hub/Assets/Care.webp"
                                        },
                                        {
                                                "name": "VGK Real Dreams",
                                                "logo": "/public/hub/Assets/realdreams.webp"
                                        },
                                        {
                                                "name": "EVolution Training Centre",
                                                "logo": "/public/hub/Assets/ETC1.webp"
                                        }
                                ]
                        },
                        "media_gallery": []
                },
                {
                        "section_type": "comparison_matrix",
                        "section_key": "investment_thesis",
                        "title": "Why 5-in-1 Beats Traditional Single-Business Franchises",
                        "subtitle": "A resilient multi-income retail model that eliminates single-product risk and off-season slumps.",
                        "content_variants": {
                                "en": {
                                        "title": "Why 5-in-1 Beats Traditional Single-Business Franchises",
                                        "subtitle": "A resilient multi-income retail model that eliminates single-product risk and off-season slumps."
                                },
                                "te": {
                                        "title": "\u0c38\u0c3e\u0c27\u0c3e\u0c30\u0c23 \u0c38\u0c3f\u0c02\u0c17\u0c3f\u0c32\u0c4d \u0c2b\u0c4d\u0c30\u0c3e\u0c02\u0c1a\u0c48\u0c1c\u0c40\u0c32 \u0c15\u0c02\u0c1f\u0c47 5-\u0c07\u0c28\u0c4d-1 \u0c39\u0c2c\u0c4d \u0c0e\u0c02\u0c26\u0c41\u0c15\u0c41 \u0c05\u0c24\u0c4d\u0c2f\u0c41\u0c24\u0c4d\u0c24\u0c2e\u0c02?",
                                        "subtitle": "\u0c12\u0c15\u0c47 \u0c09\u0c24\u0c4d\u0c2a\u0c24\u0c4d\u0c24\u0c3f\u0c2a\u0c48 \u0c06\u0c27\u0c3e\u0c30\u0c2a\u0c21\u0c15\u0c41\u0c02\u0c21\u0c3e, 5 \u0c30\u0c15\u0c3e\u0c32 \u0c06\u0c26\u0c3e\u0c2f \u0c2e\u0c3e\u0c30\u0c4d\u0c17\u0c3e\u0c32\u0c24\u0c4b \u0c38\u0c4d\u0c25\u0c3f\u0c30\u0c2e\u0c48\u0c28 \u0c32\u0c3e\u0c2d\u0c3e\u0c32\u0c41."
                                }
                        },
                        "configuration": {
                                "comparisons": [
                                        {
                                                "metric": "Revenue Concentration Risk",
                                                "traditional": "100% dependent on single product (e.g. food, cloth, single brand). If demand drops, revenue crashes.",
                                                "myntreal": "5 independent revenue streams (EV, Solar, Insurance, Real Estate, Training). Even if one stream slows, 4 others generate cash.",
                                                "winner": "myntreal"
                                        },
                                        {
                                                "metric": "Capital & Break-Even Timeline",
                                                "traditional": "\u20b920\u201350 Lakhs capital with 24\u201336 months payback period and high recurring royalties (5\u201310%).",
                                                "myntreal": "\u20b912\u201315 Lakhs all-inclusive turnkey setup with fast 6\u20139 months break-even and zero revenue royalties.",
                                                "winner": "myntreal"
                                        },
                                        {
                                                "metric": "Customer Cross-Monetization",
                                                "traditional": "One-time walk-in sale. Zero cross-selling capability across other high-margin services.",
                                                "myntreal": "Every EV customer buys insurance, evaluates solar for free charging, and refers family for property & training.",
                                                "winner": "myntreal"
                                        },
                                        {
                                                "metric": "Inventory Holding Risk",
                                                "traditional": "Heavy working capital locked in perishable or depreciating stock with high dead-stock risks.",
                                                "myntreal": "Display units only for EV; zero inventory capital for Solar EPC, Insurance, Townships & Training.",
                                                "winner": "myntreal"
                                        },
                                        {
                                                "metric": "Central Support & Lead Generation",
                                                "traditional": "Franchisee left alone for local marketing and customer acquisition.",
                                                "myntreal": "12 Months central inbound digital leads, outdoor canopy roadshows, and corporate manager support.",
                                                "winner": "myntreal"
                                        }
                                ]
                        },
                        "media_gallery": []
                },
                {
                        "section_type": "stream_deepdive",
                        "section_key": "stream_solar",
                        "title": "Stream 1: Rooftop Solar Energy (Har Ghar Solar EPC)",
                        "subtitle": "Central & State Government backed PM Surya Ghar Muft Bijli Yojana rooftop solar installations.",
                        "content_variants": {
                                "en": {
                                        "title": "Stream 1: Rooftop Solar Energy (Har Ghar Solar EPC)",
                                        "subtitle": "Central & State Government backed PM Surya Ghar Muft Bijli Yojana rooftop solar installations."
                                },
                                "te": {
                                        "title": "\u0c30\u0c02\u0c17\u0c02 2: \u0c30\u0c42\u0c2b\u0c4d\u200c\u0c1f\u0c3e\u0c2a\u0c4d \u0c38\u0c4c\u0c30 \u0c35\u0c3f\u0c26\u0c4d\u0c2f\u0c41\u0c24\u0c4d \u0c2a\u0c4d\u0c30\u0c3e\u0c1c\u0c46\u0c15\u0c4d\u0c1f\u0c41\u0c32\u0c41 (\u0c39\u0c30\u0c4d \u0c18\u0c30\u0c4d \u0c38\u0c4b\u0c32\u0c3e\u0c30\u0c4d)",
                                        "subtitle": "\u0c2a\u0c4d\u0c30\u0c27\u0c3e\u0c28\u0c2e\u0c02\u0c24\u0c4d\u0c30\u0c3f \u0c38\u0c42\u0c30\u0c4d\u0c2f \u0c18\u0c30\u0c4d \u0c2e\u0c41\u0c2b\u0c4d\u0c24\u0c4d \u0c2c\u0c3f\u0c1c\u0c3f\u0c32\u0c40 \u0c2f\u0c4b\u0c1c\u0c28 \u0c15\u0c3f\u0c02\u0c26 \u20b978,000 \u0c38\u0c2c\u0c4d\u0c38\u0c3f\u0c21\u0c40 & \u20b91 \u0c38\u0c4d\u0c15\u0c40\u0c2e\u0c4d \u0c38\u0c4b\u0c32\u0c3e\u0c30\u0c4d \u0c2a\u0c4d\u0c30\u0c3e\u0c1c\u0c46\u0c15\u0c4d\u0c1f\u0c41\u0c32\u0c41."
                                }
                        },
                        "configuration": {
                                "badge": "Clean Energy & Govt. Subsidy",
                                "brand": "Har Ghar Solar (MyntReal)",
                                "dealer_margin": "\u20b915,000 to \u20b925,000 per 3 kW residential plant | Up to \u20b91 Lakh on commercial",
                                "subsidies": [
                                        {
                                                "capacity": "1 kW System",
                                                "subsidy": "\u20b933,000",
                                                "generation": "120 units/mo",
                                                "cost": "Budget Friendly"
                                        },
                                        {
                                                "capacity": "2 kW System",
                                                "subsidy": "\u20b966,000",
                                                "generation": "240 units/mo",
                                                "cost": "High Popularity"
                                        },
                                        {
                                                "capacity": "3 kW System",
                                                "subsidy": "\u20b978,000 (Maximum)",
                                                "generation": "360 units/mo",
                                                "cost": "Zero Bill Guarantee"
                                        }
                                ],
                                "scheme_rupee_one": "Solar for \u20b91 Token: Consumer pays only \u20b91 token advance. The balance is financed through collateral-free institutional bank loans (SBI, PNB, Canara, Union Bank, APGB) with monthly EMI paid directly out of electricity bill savings.",
                                "brands": [
                                        "Waaree Energies",
                                        "ReNew Power",
                                        "TATA Solar",
                                        "Adani Solar",
                                        "Vikram Solar",
                                        "Goldi Solar"
                                ],
                                "warranty": "25-Year Performance Warranty on Mono-PERC Bifacial Solar Panels | 5-Year Inverter Replacement"
                        },
                        "media_gallery": []
                },
                {
                        "section_type": "stream_deepdive",
                        "section_key": "stream_ev",
                        "title": "Stream 2: Electric 2-Wheeler Dealership (Manthra EV)",
                        "subtitle": "High-demand electric mobility engineered for Indian roads with premium dealer margins.",
                        "content_variants": {
                                "en": {
                                        "title": "Stream 2: Electric 2-Wheeler Dealership (Manthra EV)",
                                        "subtitle": "High-demand electric mobility engineered for Indian roads with premium dealer margins."
                                },
                                "te": {
                                        "title": "\u0c30\u0c02\u0c17\u0c02 1: \u0c0e\u0c32\u0c15\u0c4d\u0c1f\u0c4d\u0c30\u0c3f\u0c15\u0c4d \u0c1f\u0c42-\u0c35\u0c40\u0c32\u0c30\u0c4d \u0c21\u0c40\u0c32\u0c30\u0c4d\u200c\u0c37\u0c3f\u0c2a\u0c4d (\u0c2e\u0c02\u0c24\u0c4d\u0c30\u0c3e \u0c08\u0c35\u0c40)",
                                        "subtitle": "\u0c2d\u0c3e\u0c30\u0c24\u0c40\u0c2f \u0c30\u0c4b\u0c21\u0c4d\u0c32 \u0c15\u0c4b\u0c38\u0c02 \u0c2a\u0c4d\u0c30\u0c24\u0c4d\u0c2f\u0c47\u0c15\u0c02\u0c17\u0c3e \u0c30\u0c42\u0c2a\u0c4a\u0c02\u0c26\u0c3f\u0c02\u0c1a\u0c2c\u0c21\u0c3f\u0c28 \u0c05\u0c24\u0c4d\u0c2f\u0c3e\u0c27\u0c41\u0c28\u0c3f\u0c15 \u0c08\u0c35\u0c40 \u0c38\u0c4d\u0c15\u0c42\u0c1f\u0c30\u0c4d\u0c32\u0c41 & \u0c05\u0c27\u0c3f\u0c15 \u0c2e\u0c3e\u0c30\u0c4d\u0c1c\u0c3f\u0c28\u0c4d\u0c32\u0c41."
                                }
                        },
                        "configuration": {
                                "badge": "High-Demand Mobility",
                                "brand": "Manthra EV",
                                "partner": "Zynova Mobility Pvt. Ltd.",
                                "dealer_margin": "12% (~₹7,200 avg per vehicle) + spares & service | Direct Sale: Additional VGK4U Commission 10.5%",
                                "models": [
                                        {
                                                "code": "EV-PRO-GT",
                                                "name": "Manthra EV Pro GT",
                                                "category": "Sport Street Commuter (Non-RTO)",
                                                "price": "₹31,499 – ₹72,999",
                                                "margin": "12% Margin (~₹7,200 avg)",
                                                "img": "/public/hub/Assets/manthra-pro-gt-real.webp",
                                                "variants": [
                                                        { "name": "Chassis Only (Without Battery)", "price": "₹31,499/-", "range": "—", "charge": "—" },
                                                        { "name": "Graphene 48V 30Ah", "price": "₹49,999/-", "range": "50 – 60 km", "charge": "8 Hours" },
                                                        { "name": "LTM/LFP 48V 30Ah", "price": "₹59,999/-", "range": "50 – 60 km", "charge": "4–5 Hours (Smart Fast Charge)" },
                                                        { "name": "LTM/LFP 48V 45Ah", "price": "₹72,999/-", "range": "80 – 90 km", "charge": "4–5 Hours (Smart Fast Charge)" }
                                                ],
                                                "specs": {
                                                        "Speed Category": "Low-Speed (<25 km/h) • Non-RTO",
                                                        "RTO / License": "No Driving License / No RTO Registration Needed",
                                                        "Charge Time": "Graphene: 8 Hours | LTM/LFP: 4–5 Hours Fast",
                                                        "Brakes": "Dual Disc CBS with E-ABS",
                                                        "Drive System": "High Efficiency Waterproof BLDC Hub Drive",
                                                        "Warranty": "3 Years Comprehensive Warranty"
                                                }
                                        },
                                        {
                                                "code": "EV-POWER-PLUS",
                                                "name": "Manthra EV Power Plus",
                                                "category": "Heavy-Duty Commercial Delivery & Cargo (Non-RTO)",
                                                "price": "₹32,999 – ₹74,499",
                                                "margin": "12% Margin (~₹7,200 avg)",
                                                "img": "/public/hub/Assets/manthra-power-plus-real.webp",
                                                "variants": [
                                                        { "name": "Chassis Only (Without Battery)", "price": "₹32,999/-", "range": "—", "charge": "—" },
                                                        { "name": "Graphene 48V 30Ah", "price": "₹51,499/-", "range": "50 – 60 km", "charge": "8 Hours" },
                                                        { "name": "LTM/LFP 48V 30Ah", "price": "₹61,499/-", "range": "50 – 60 km", "charge": "4–5 Hours (Smart Fast Charge)" },
                                                        { "name": "LTM/LFP 48V 45Ah", "price": "₹74,499/-", "range": "80 – 90 km", "charge": "4–5 Hours (Smart Fast Charge)" }
                                                ],
                                                "specs": {
                                                        "Speed Category": "Low-Speed (<25 km/h) • Non-RTO",
                                                        "Payload": "200 kg Certified Heavy Load Capacity",
                                                        "RTO / License": "No Driving License / No RTO Registration Needed",
                                                        "Charge Time": "Graphene: 8 Hours | LTM/LFP: 4–5 Hours Fast",
                                                        "Chassis": "Heavy Reinforced Tubular Steel Frame",
                                                        "Warranty": "3 Years Comprehensive Warranty"
                                                }
                                        },
                                        {
                                                "code": "EV-M99",
                                                "name": "Manthra EV M99 Flagship",
                                                "category": "Next-Gen High-Performance Urban Flagship (Non-RTO)",
                                                "price": "₹45,999 – ₹96,999",
                                                "margin": "12% Margin (~₹7,200 avg)",
                                                "img": "/public/hub/Assets/manthra-m99-real.webp",
                                                "variants": [
                                                        { "name": "Chassis Only (Without Battery)", "price": "₹45,999/-", "range": "—", "charge": "—" },
                                                        { "name": "LTM/LFP 60V 30Ah", "price": "₹80,999/-", "range": "60 – 70 km", "charge": "4–5 Hours (Smart Fast Charge)" },
                                                        { "name": "LTM/LFP 60V 45Ah", "price": "₹96,999/-", "range": "90 – 100 km", "charge": "4–5 Hours (Smart Fast Charge)" }
                                                ],
                                                "specs": {
                                                        "Speed Category": "Low-Speed (<25 km/h) • Non-RTO",
                                                        "RTO / License": "No Driving License / No RTO Registration Needed",
                                                        "Charge Time": "4–5 Hours (LTM/LFP Smart Fast Charge)",
                                                        "Drive System": "High Torque Waterproof BLDC Hub Drive",
                                                        "Features": "Reverse Drive Assist, Keyless Start, Smart LCD",
                                                        "Warranty": "3 Years Comprehensive Warranty"
                                                }
                                        },
                                        {
                                                "code": "EV-ROYAL-SLING",
                                                "name": "Manthra EV Royal Sling",
                                                "category": "Vintage Classic Luxury & Comfort (Non-RTO)",
                                                "price": "₹45,999 – ₹96,999",
                                                "margin": "12% Margin (~₹7,200 avg)",
                                                "img": "/public/hub/Assets/manthra-royal-real.webp",
                                                "variants": [
                                                        { "name": "Chassis Only (Without Battery)", "price": "₹45,999/-", "range": "—", "charge": "—" },
                                                        { "name": "LTM/LFP 60V 30Ah", "price": "₹80,999/-", "range": "60 – 70 km", "charge": "4–5 Hours (Smart Fast Charge)" },
                                                        { "name": "LTM/LFP 60V 45Ah", "price": "₹96,999/-", "range": "90 – 100 km", "charge": "4–5 Hours (Smart Fast Charge)" }
                                                ],
                                                "specs": {
                                                        "Speed Category": "Low-Speed (<25 km/h) • Non-RTO",
                                                        "RTO / License": "No Driving License / No RTO Registration Needed",
                                                        "Charge Time": "4–5 Hours (LTM/LFP Smart Fast Charge)",
                                                        "Brakes": "Dual Hydraulic Disc with E-ABS",
                                                        "Styling": "Vintage Curved Retro Body with Chrome Accents",
                                                        "Warranty": "3 Years Comprehensive Warranty"
                                                }
                                        },
                                        {
                                                "code": "EV-BEAST-PRO",
                                                "name": "Manthra EV Beast Pro",
                                                "category": "Aggressive Street Flagship (Non-RTO)",
                                                "price": "₹47,999 – ₹99,499",
                                                "margin": "12% Margin (~₹7,200 avg)",
                                                "img": "/public/hub/Assets/manthra-beast-real.webp",
                                                "variants": [
                                                        { "name": "Chassis Only (Without Battery)", "price": "₹47,999/-", "range": "—", "charge": "—" },
                                                        { "name": "LTM/LFP 60V 30Ah", "price": "₹82,999/-", "range": "60 – 70 km", "charge": "4–5 Hours (Smart Fast Charge)" },
                                                        { "name": "LTM/LFP 60V 45Ah", "price": "₹99,499/-", "range": "90 – 100 km", "charge": "4–5 Hours (Smart Fast Charge)" }
                                                ],
                                                "specs": {
                                                        "Speed Category": "Low-Speed (<25 km/h) • Non-RTO",
                                                        "RTO / License": "No Driving License / No RTO Registration Needed",
                                                        "Charge Time": "4–5 Hours (LTM/LFP Smart Fast Charge)",
                                                        "Brakes": "Dual Disc with Synchronized CBS",
                                                        "Suspension": "Heavy-Duty Nitrogen Shock Absorbers",
                                                        "Warranty": "3 Years Comprehensive Warranty"
                                                }
                                        }
                                ],
                                "battery_tech": {
                                        "graphene": "Graphene 48V: Economical, reliable deep cycle chemistry, 8 Hours charging time.",
                                        "lfp": "LFP (Lithium Iron Phosphate): Ultra-safe, non-combustible chemistry, 2000+ deep charge cycles, extreme thermal stability, 4–5 Hours Smart Fast Charge.",
                                        "ltm": "LTM (Lithium Titanate): Ultra-fast charging capability (80% in 30 mins), exceptional cold/hot weather performance, 4–5 Hours Smart Fast Charge."
                                }
                        },
                        "media_gallery": []
                },
                {
                        "section_type": "stream_deepdive",
                        "section_key": "stream_insurance",
                        "title": "Stream 3: Multi-Insurer Insurance Advisory (VGK Care)",
                        "subtitle": "Point of Presence insurance advisory with 40+ leading nationwide insurance companies.",
                        "content_variants": {
                                "en": {
                                        "title": "Stream 3: Multi-Insurer Insurance Advisory (VGK Care)",
                                        "subtitle": "Point of Presence insurance advisory with 40+ leading nationwide insurance companies."
                                },
                                "te": {
                                        "title": "\u0c30\u0c02\u0c17\u0c02 3: \u0c38\u0c2e\u0c17\u0c4d\u0c30 \u0c2c\u0c40\u0c2e\u0c3e \u0c38\u0c47\u0c35\u0c32 \u0c38\u0c32\u0c39\u0c3e \u0c15\u0c47\u0c02\u0c26\u0c4d\u0c30\u0c02 (VGK \u0c15\u0c47\u0c30\u0c4d)",
                                        "subtitle": "40\u0c15\u0c3f \u0c2a\u0c48\u0c17\u0c3e \u0c2a\u0c4d\u0c30\u0c2e\u0c41\u0c16 \u0c2c\u0c40\u0c2e\u0c3e \u0c38\u0c02\u0c38\u0c4d\u0c25\u0c32 \u0c2d\u0c3e\u0c17\u0c38\u0c4d\u0c35\u0c3e\u0c2e\u0c4d\u0c2f\u0c02\u0c24\u0c4b \u0c2e\u0c4b\u0c1f\u0c3e\u0c30\u0c4d, \u0c06\u0c30\u0c4b\u0c17\u0c4d\u0c2f\u0c02, \u0c32\u0c48\u0c2b\u0c4d & \u0c38\u0c4b\u0c32\u0c3e\u0c30\u0c4d \u0c07\u0c28\u0c4d\u0c38\u0c42\u0c30\u0c46\u0c28\u0c4d\u0c38\u0c4d."
                                }
                        },
                        "configuration": {
                                "badge": "Perpetual Recurring Income",
                                "brand": "VGK Care (Zynova Mobility)",
                                "motto": "Your Protection, Our Responsibility.",
                                "partners": "Associated with Bajaj Capital & 40+ insurers: HDFC ERGO, ICICI Lombard, Bajaj Allianz, Star Health, Care, Tata AIG, SBI General.",
                                "products": [
                                        {
                                                "type": "EV Motor Insurance",
                                                "desc": "Comprehensive 1-year own damage + 5-year third party cover with zero-depreciation and battery protection riders."
                                        },
                                        {
                                                "type": "Solar Plant All-Risk Cover",
                                                "desc": "Covers natural disasters, cyclone, lightning, fire, generation loss, and inverter theft for residential & commercial plants."
                                        },
                                        {
                                                "type": "Family Health & Critical Illness",
                                                "desc": "Cashless hospitalization across 10,000+ network hospitals with zero room-rent cap."
                                        },
                                        {
                                                "type": "Commercial Fleet & Livestock",
                                                "desc": "Truck, auto, school bus, commercial vehicle, retail shopkeeper, and livestock rural insurance."
                                        }
                                ],
                                "commission_structure": "10% to 25% on fresh policies PLUS perpetual annual recurring renewal commissions year after year with zero inventory risk."
                        },
                        "media_gallery": []
                },
                {
                        "section_type": "stream_deepdive",
                        "section_key": "stream_realestate",
                        "title": "Stream 4: Integrated Townships & Gated Layouts (VGK Real Dreams)",
                        "subtitle": "Strategic referral and sales partner for DTCP / RERA approved luxury villas and gated plots.",
                        "content_variants": {
                                "en": {
                                        "title": "Stream 4: Integrated Townships & Gated Layouts (VGK Real Dreams)",
                                        "subtitle": "Strategic referral and sales partner for DTCP / RERA approved luxury villas and gated plots."
                                },
                                "te": {
                                        "title": "\u0c30\u0c02\u0c17\u0c02 4: \u0c2a\u0c4d\u0c30\u0c40\u0c2e\u0c3f\u0c2f\u0c02 \u0c30\u0c3f\u0c2f\u0c32\u0c4d \u0c0e\u0c38\u0c4d\u0c1f\u0c47\u0c1f\u0c4d & \u0c17\u0c47\u0c1f\u0c46\u0c21\u0c4d \u0c1f\u0c4c\u0c28\u0c4d\u200c\u0c37\u0c3f\u0c2a\u0c4d\u200c\u0c32\u0c41 (VGK \u0c30\u0c3f\u0c2f\u0c32\u0c4d \u0c21\u0c4d\u0c30\u0c40\u0c2e\u0c4d\u0c38\u0c4d)",
                                        "subtitle": "DTCP & RERA \u0c06\u0c2e\u0c4b\u0c26\u0c02 \u0c2a\u0c4a\u0c02\u0c26\u0c3f\u0c28 \u0c32\u0c17\u0c4d\u0c1c\u0c30\u0c40 \u0c35\u0c3f\u0c32\u0c4d\u0c32\u0c3e\u0c32\u0c41, \u0c13\u0c2a\u0c46\u0c28\u0c4d \u0c2a\u0c4d\u0c32\u0c3e\u0c1f\u0c4d\u0c32\u0c41 & \u0c39\u0c48\u0c35\u0c47 \u0c15\u0c2e\u0c30\u0c4d\u0c37\u0c3f\u0c2f\u0c32\u0c4d \u0c2a\u0c4d\u0c30\u0c3e\u0c1c\u0c46\u0c15\u0c4d\u0c1f\u0c41\u0c32\u0c41."
                                }
                        },
                        "configuration": {
                                "badge": "High-Ticket Capital Gains",
                                "brand": "VGK Real Dreams (Zynova Mobility)",
                                "motto": "Building Businesses, Not Just Properties.",
                                "commission": "2% to 5% Sales & Referral Commission per closed transaction",
                                "ticket_sizes": "\u20b915 Lakhs to \u20b91.5 Crore per plot / villa (Yields \u20b940,000 to \u20b95,00,000 single transaction payout)",
                                "standards": [
                                        "100% DTCP / VMRDA and RERA approved layouts",
                                        "Solar-powered street lighting & underground electricity cabling",
                                        "Grand entrance arch, 40 & 33 feet wide blacktop roads, landscaped parks",
                                        "Spot registration with 100% clear legal title & bank loan approvals"
                                ]
                        },
                        "media_gallery": []
                },
                {
                        "section_type": "stream_deepdive",
                        "section_key": "stream_training",
                        "title": "Stream 5: Professional EV Technician Certification (EVolution Training Centre)",
                        "subtitle": "In technical collaboration with Govt. Polytechnic College, Pendurthi Campus, Visakhapatnam.",
                        "content_variants": {
                                "en": {
                                        "title": "Stream 5: Professional EV Technician Certification (EVolution Training Centre)",
                                        "subtitle": "In technical collaboration with Govt. Polytechnic College, Pendurthi Campus, Visakhapatnam."
                                },
                                "te": {
                                        "title": "\u0c30\u0c02\u0c17\u0c02 5: \u0c2a\u0c4d\u0c30\u0c4a\u0c2b\u0c46\u0c37\u0c28\u0c32\u0c4d \u0c08\u0c35\u0c40 \u0c1f\u0c46\u0c15\u0c4d\u0c28\u0c40\u0c37\u0c3f\u0c2f\u0c28\u0c4d \u0c36\u0c3f\u0c15\u0c4d\u0c37\u0c23 (EVolution \u0c1f\u0c4d\u0c30\u0c48\u0c28\u0c3f\u0c02\u0c17\u0c4d \u0c38\u0c46\u0c02\u0c1f\u0c30\u0c4d)",
                                        "subtitle": "\u0c2a\u0c4d\u0c30\u0c2d\u0c41\u0c24\u0c4d\u0c35 \u0c2a\u0c3e\u0c32\u0c3f\u0c1f\u0c46\u0c15\u0c4d\u0c28\u0c3f\u0c15\u0c4d \u0c15\u0c33\u0c3e\u0c36\u0c3e\u0c32, \u0c2a\u0c46\u0c02\u0c26\u0c41\u0c30\u0c4d\u0c24\u0c3f \u0c2d\u0c3e\u0c17\u0c38\u0c4d\u0c35\u0c3e\u0c2e\u0c4d\u0c2f\u0c02\u0c24\u0c4b 1-\u0c35\u0c3e\u0c30\u0c02 \u0c2a\u0c4d\u0c30\u0c3e\u0c15\u0c4d\u0c1f\u0c3f\u0c15\u0c32\u0c4d \u0c08\u0c35\u0c40 \u0c38\u0c30\u0c4d\u0c1f\u0c3f\u0c2b\u0c3f\u0c15\u0c47\u0c37\u0c28\u0c4d \u0c15\u0c4b\u0c30\u0c4d\u0c38\u0c41."
                                }
                        },
                        "configuration": {
                                "badge": "Govt. Polytechnic Partner",
                                "brand": "EVolution Training Centre (ETC)",
                                "venue": "Govt. Polytechnic College, Pendurthi Campus, Visakhapatnam",
                                "motto": "Empowering Skills. Enabling Growth.",
                                "course_fee": "Regular \u20b919,999 discounted by \u20b910,000 scholarship -> Net Fee \u20b99,999 only",
                                "partner_incentive": "₹1,000 counselor referral fee per enrolled student (5 students/mo = ₹5,000 monthly income)",
                                "synergy": "Acts as an ongoing talent pipeline to hire certified EV diagnostic mechanics for your showroom service bay.",
                                "modules": [
                                        "Lithium-ion Battery Pack Assembly & Cell Balancing",
                                        "BLDC Hub Motor Disassembly & Hall Sensor Testing",
                                        "Smart Controller Wiring & Throttle Diagnostics",
                                        "EV Multi-Pin Diagnostic Scan Tool Operations",
                                        "Workshop Safety, High-Voltage Protocols & Startup Incubation"
                                ]
                        },
                        "media_gallery": []
                },
                {
                        "section_type": "infographic",
                        "section_key": "customer_flywheel",
                        "title": "The 360\u00b0 Customer Cross-Monetization Flywheel",
                        "subtitle": "How a single walk-in customer is seamlessly monetized across multiple revenue engines.",
                        "content_variants": {
                                "en": {
                                        "title": "The 360\u00b0 Customer Cross-Monetization Flywheel",
                                        "subtitle": "How a single walk-in customer is seamlessly monetized across multiple revenue engines."
                                },
                                "te": {
                                        "title": "360\u00b0 \u0c15\u0c38\u0c4d\u0c1f\u0c2e\u0c30\u0c4d \u0c15\u0c4d\u0c30\u0c3e\u0c38\u0c4d-\u0c2e\u0c3e\u0c28\u0c3f\u0c1f\u0c48\u0c1c\u0c47\u0c37\u0c28\u0c4d \u0c2b\u0c4d\u0c32\u0c48\u0c35\u0c40\u0c32\u0c4d",
                                        "subtitle": "\u0c12\u0c15\u0c47 \u0c15\u0c38\u0c4d\u0c1f\u0c2e\u0c30\u0c4d \u0c26\u0c4d\u0c35\u0c3e\u0c30\u0c3e 5 \u0c30\u0c15\u0c3e\u0c32 \u0c35\u0c4d\u0c2f\u0c3e\u0c2a\u0c3e\u0c30\u0c3e\u0c32 \u0c28\u0c41\u0c02\u0c21\u0c3f \u0c28\u0c3f\u0c30\u0c02\u0c24\u0c30 \u0c06\u0c26\u0c3e\u0c2f\u0c3e\u0c28\u0c4d\u0c28\u0c3f \u0c2a\u0c4a\u0c02\u0c26\u0c47 \u0c35\u0c3f\u0c27\u0c3e\u0c28\u0c02."
                                }
                        },
                        "configuration": {
                                "steps": [
                                        {
                                                "step": "1",
                                                "title": "Customer Buys an EV",
                                                "desc": "Walk-in customer purchases a Manthra Beast Pro or Royal DLX.",
                                                "earn": "Margin: \u20b96,000 / unit"
                                        },
                                        {
                                                "step": "2",
                                                "title": "Motor Insurance Issuance",
                                                "desc": "Hub instantly issues a VGK Care 5-year insurance policy on the spot.",
                                                "earn": "Commission: \u20b91,500 \u2013 \u20b92,500"
                                        },
                                        {
                                                "step": "3",
                                                "title": "Free EV Charging via Solar",
                                                "desc": "Customer installs Har Ghar Solar 3kW rooftop plant to charge EV for \u20b90 electricity cost.",
                                                "earn": "Margin: \u20b920,000 \u2013 \u20b925,000"
                                        },
                                        {
                                                "step": "4",
                                                "title": "Family Member EV Skill Training",
                                                "desc": "Customer's son or relative enrolls in the 1-Week EV Technician training at Govt Poly Pendurthi.",
                                                "earn": "Referral: \u20b92,500"
                                        },
                                        {
                                                "step": "5",
                                                "title": "Township Gated Plot Referral",
                                                "desc": "Customer or relative invests in a VGK Real Dreams gated community plot or luxury villa.",
                                                "earn": "Commission: \u20b950,000 \u2013 \u20b92,50,000"
                                        }
                                ]
                        },
                        "media_gallery": []
                },
                {
                        "section_type": "deliverables_grid",
                        "section_key": "deliverables",
                        "title": "What You Get in the Franchise Package (9 Turnkey Deliverables)",
                        "subtitle": "Complete showroom inventory, hardware, digital software, and marketing infrastructure.",
                        "content_variants": {
                                "en": {
                                        "title": "What You Get in the Franchise Package (9 Turnkey Deliverables)",
                                        "subtitle": "Complete showroom inventory, hardware, digital software, and marketing infrastructure."
                                },
                                "te": {
                                        "title": "\u0c2e\u0c40 \u0c2b\u0c4d\u0c30\u0c3e\u0c02\u0c1a\u0c48\u0c1c\u0c4d \u0c2a\u0c4d\u0c2f\u0c3e\u0c15\u0c47\u0c1c\u0c40\u0c32\u0c4b \u0c32\u0c2d\u0c3f\u0c02\u0c1a\u0c47 9 \u0c2a\u0c42\u0c30\u0c4d\u0c24\u0c3f \u0c35\u0c28\u0c30\u0c41\u0c32\u0c41 (Turnkey Kit)",
                                        "subtitle": "\u0c39\u0c3e\u0c30\u0c4d\u0c21\u0c4d\u200c\u0c35\u0c47\u0c30\u0c4d, \u0c37\u0c4b\u0c30\u0c42\u0c2e\u0c4d \u0c2c\u0c48\u0c15\u0c4d\u200c\u0c32\u0c41, \u0c09\u0c1a\u0c3f\u0c24 \u0c15\u0c02\u0c2a\u0c4d\u0c2f\u0c42\u0c1f\u0c30\u0c4d, \u0c1f\u0c40\u0c35\u0c40, \u0c2a\u0c4d\u0c30\u0c3f\u0c02\u0c1f\u0c30\u0c4d \u0c2e\u0c30\u0c3f\u0c2f\u0c41 12 \u0c28\u0c46\u0c32\u0c32 \u0c2e\u0c3e\u0c30\u0c4d\u0c15\u0c46\u0c1f\u0c3f\u0c02\u0c17\u0c4d \u0c38\u0c2a\u0c4b\u0c30\u0c4d\u0c1f\u0c4d."
                                }
                        },
                        "configuration": {
                                "deliverables": [
                                        {
                                                "num": "01",
                                                "icon": "fa-cubes",
                                                "title": "5 Franchises in One",
                                                "highlight": "Core Rights",
                                                "desc": "Authorized territory rights for EV Dealership, Har Ghar Solar EPC, VGK Care Insurance, Real Dreams Townships & EVolution Training."
                                        },
                                        {
                                                "num": "02",
                                                "icon": "fa-desktop",
                                                "title": "Windows Desktop / Laptop",
                                                "highlight": "FREE with Kit",
                                                "desc": "Pre-configured system with MyntOS ERP, CRM billing, inventory management, and digital customer pipeline."
                                        },
                                        {
                                                "num": "03",
                                                "icon": "fa-tv",
                                                "title": "43\" Smart LED Color TV",
                                                "highlight": "FREE with Kit",
                                                "desc": "Mounted showroom display for streaming EV product walkthroughs, solar generation explainer videos, and customer testimonials."
                                        },
                                        {
                                                "num": "04",
                                                "icon": "fa-print",
                                                "title": "Color Multi-Function Printer",
                                                "highlight": "FREE with Kit",
                                                "desc": "High-resolution printer, scanner & copier for immediate generation of on-spot solar quotations, insurance policies, and vehicle invoices."
                                        },
                                        {
                                                "num": "05",
                                                "icon": "fa-motorcycle",
                                                "title": "4\u20136 Showroom Display EVs",
                                                "highlight": "Ready Stock",
                                                "desc": "Factory-fresh stock of Manthra EV scooters (Beast Pro, Royal, Power Plus, Pro GT) ready for immediate test drives and rapid dispatch."
                                        },
                                        {
                                                "num": "06",
                                                "icon": "fa-solar-panel",
                                                "title": "Live Solar Rooftop Demo Unit",
                                                "highlight": "Working Model",
                                                "desc": "Working on-grid solar structure with real-time solar panel, string inverter & bidirectional net-meter display for walk-in demonstrations."
                                        },
                                        {
                                                "num": "07",
                                                "icon": "fa-bullhorn",
                                                "title": "Outdoor Canopy & Marketing Kit",
                                                "highlight": "Canopy & Standees",
                                                "desc": "Foldable promotional outdoor marketing canopy, roll-up standees, branded customer brochures, and promotional roadshow banners."
                                        },
                                        {
                                                "num": "08",
                                                "icon": "fa-globe",
                                                "title": "12 Months Online Brand Support",
                                                "highlight": "Inbound Leads",
                                                "desc": "Dedicated local digital advertising campaigns, Google My Business top-ranking management, and localized customer inquiries."
                                        },
                                        {
                                                "num": "09",
                                                "icon": "fa-chalkboard-user",
                                                "title": "Sales & Technical Training",
                                                "highlight": "Certified Induction",
                                                "desc": "5-day comprehensive on-site training for sales staff, CRM operations, customer handling, and service mechanic diagnostic training."
                                        }
                                ]
                        },
                        "media_gallery": []
                },
                {
                        "section_type": "roi_financial_model",
                        "section_key": "roi_financials",
                        "title": "Financial Viability & 3-Scenario Unit Economics Analysis",
                        "subtitle": "Conservative unit economics directly from Pages 10 & 11 of the official Investor Franchise Brochure.",
                        "content_variants": {
                                "en": {
                                        "title": "Financial Viability & 3-Scenario Unit Economics Analysis",
                                        "subtitle": "Conservative unit economics directly from Pages 10 & 11 of the official Investor Franchise Brochure."
                                },
                                "te": {
                                        "title": "\u0c06\u0c30\u0c4d\u0c25\u0c3f\u0c15 \u0c35\u0c3f\u0c36\u0c4d\u0c32\u0c47\u0c37\u0c23 & 3 \u0c30\u0c15\u0c3e\u0c32 \u0c32\u0c3e\u0c2d\u0c3e\u0c32 \u0c05\u0c02\u0c1a\u0c28\u0c3e (ROI Analysis)",
                                        "subtitle": "\u0c05\u0c27\u0c3f\u0c15\u0c3e\u0c30\u0c3f\u0c15 \u0c2c\u0c4d\u0c30\u0c4b\u0c1a\u0c30\u0c4d \u0c2a\u0c47\u0c1c\u0c40\u0c32\u0c41 10 & 11 \u0c06\u0c27\u0c3e\u0c30\u0c02\u0c17\u0c3e \u0c28\u0c46\u0c32\u0c35\u0c3e\u0c30\u0c40 \u0c2e\u0c30\u0c3f\u0c2f\u0c41 \u0c35\u0c3e\u0c30\u0c4d\u0c37\u0c3f\u0c15 \u0c28\u0c3f\u0c15\u0c30 \u0c06\u0c26\u0c3e\u0c2f \u0c35\u0c3f\u0c35\u0c30\u0c3e\u0c32\u0c41."
                                }
                        },
                        "configuration": {
                                "capital": "\u20b912,00,000 \u2013 \u20b915,00,000",
                                "payback": "6 \u2013 9 Months",
                                "base_monthly_net": "\u20b91,65,000 / month",
                                "base_annual_net": "\u20b919,80,000 / year",
                                "year1_roi": "~140% Return on Capital",
                                "base_table": [
                                        {
                                                "stream": "1. Manthra Electric 2-Wheelers",
                                                "volume": "5 EVs/mo x \u20b960,000 avg x 12% (or 10 units @ \u20b98.5k)",
                                                "gross_mo": 85000,
                                                "gross_yr": 1020000
                                        },
                                        {
                                                "stream": "2. Har Ghar Rooftop Solar Plants",
                                                "volume": "5 installs/mo (3 kW) x \u20b920,000 margin",
                                                "gross_mo": 60000,
                                                "gross_yr": 720000
                                        },
                                        {
                                                "stream": "3. VGK Care Insurance Advisory",
                                                "volume": "10 to 40 policies/mo x avg commission",
                                                "gross_mo": 25000,
                                                "gross_yr": 300000
                                        },
                                        {
                                                "stream": "4. VGK Real Dreams Townships",
                                                "volume": "Project-based deal closing (1 sale / 2 mos)",
                                                "gross_mo": 30000,
                                                "gross_yr": 360000
                                        },
                                        {
                                                "stream": "5. EVolution Student Admissions",
                                                "volume": "5 student admissions/mo x \u20b92,500 referral",
                                                "gross_mo": 12500,
                                                "gross_yr": 150000
                                        }
                                ],
                                "gross_monthly": 212500,
                                "gross_annual": 2550000,
                                "operating_costs": 47500,
                                "net_monthly": 165000,
                                "net_annual": 1980000,
                                "scenarios": {
                                        "worst": {
                                                "title": "Worst Case Scenario (Low Activity)",
                                                "badge": "Safe Downside",
                                                "desc": "Minimal sales during early setup months without aggressive local advertising.",
                                                "metrics": [
                                                        "EV Sales: 3 Scooters / mo (\u20b92,52,000/yr)",
                                                        "Solar Plants: 3 Installs / mo (\u20b92,52,000/yr)",
                                                        "Insurance: 6 Policies / mo (\u20b92,16,000/yr)",
                                                        "EV Training: 3 Candidates / mo (\u20b92,16,000/yr)",
                                                        "Real Estate: NIL (\u20b90)"
                                                ],
                                                "net_annual": "\u20b99,86,000 / year",
                                                "payback": "12 \u2013 14 Months",
                                                "outcome": "Almost entire initial capital recovered in Year 1 even in the slowest market conditions."
                                        },
                                        "base": {
                                                "title": "Expected Base Case (Standard Performance)",
                                                "badge": "\u2b50 Recommended Benchmark",
                                                "desc": "Average operational run rate achieved across live semi-urban and rural mandal hubs.",
                                                "metrics": [
                                                        "EV Sales: 10 Scooters / mo (\u20b910,20,000/yr)",
                                                        "Solar Plants: 3 to 5 Installs / mo (\u20b97,20,000/yr)",
                                                        "Insurance: 40 Policies / mo (\u20b93,00,000/yr)",
                                                        "Real Estate: 1 Referral every 2 mos (\u20b93,60,000/yr)",
                                                        "EV Training: 5 Students / mo (\u20b91,50,000/yr)"
                                                ],
                                                "net_annual": "\u20b919,80,000 / year",
                                                "payback": "6 \u2013 9 Months",
                                                "outcome": "~140% Return on Investment in Year 1 with highly consistent month-on-month cash flow."
                                        },
                                        "best": {
                                                "title": "Best Case Scenario (Optimized High Growth)",
                                                "badge": "High Growth Potential",
                                                "desc": "Active commercial mandals with high EV adoption and strong localized canopy marketing.",
                                                "metrics": [
                                                        "EV Sales: 12 to 18 Scooters / mo (\u20b910,08,000/yr)",
                                                        "Solar Plants: 10 Installs / mo (\u20b93,40,000+/yr)",
                                                        "Insurance: 20 to 75 Policies / mo (\u20b97,20,000/yr)",
                                                        "EV Training: 10 Candidates / mo (\u20b97,20,000/yr)",
                                                        "Real Estate: 1 Deal / month (\u20b92,00,000+/yr)"
                                                ],
                                                "net_annual": "\u20b934,86,000 / year",
                                                "payback": "4 \u2013 5 Months",
                                                "outcome": "Massive capital multiplication and perpetual recurring renewal annuity year after year."
                                        }
                                }
                        },
                        "media_gallery": []
                },
                {
                        "section_type": "roi_calculator",
                        "section_key": "interactive_calculator",
                        "title": "Interactive Investor ROI & Cash Flow Simulator",
                        "subtitle": "Adjust monthly volumes below to model your personalized gross earnings, expenses, and net profit live.",
                        "content_variants": {
                                "en": {
                                        "title": "Interactive Investor ROI & Cash Flow Simulator",
                                        "subtitle": "Adjust monthly volumes below to model your personalized gross earnings, expenses, and net profit live."
                                },
                                "te": {
                                        "title": "\u0c32\u0c48\u0c35\u0c4d \u0c07\u0c28\u0c4d\u0c35\u0c46\u0c38\u0c4d\u0c1f\u0c30\u0c4d ROI & \u0c32\u0c3e\u0c2d\u0c3e\u0c32 \u0c15\u0c4d\u0c2f\u0c3e\u0c32\u0c3f\u0c15\u0c4d\u0c2f\u0c41\u0c32\u0c47\u0c1f\u0c30\u0c4d",
                                        "subtitle": "\u0c2e\u0c40 \u0c05\u0c02\u0c1a\u0c28\u0c3e\u0c32 \u0c2a\u0c4d\u0c30\u0c15\u0c3e\u0c30\u0c02 \u0c38\u0c4d\u0c32\u0c48\u0c21\u0c30\u0c4d\u200c\u0c32\u0c28\u0c41 \u0c2e\u0c3e\u0c30\u0c4d\u0c1a\u0c3f \u0c2e\u0c40 \u0c28\u0c46\u0c32\u0c35\u0c3e\u0c30\u0c40 \u0c2e\u0c30\u0c3f\u0c2f\u0c41 \u0c35\u0c3e\u0c30\u0c4d\u0c37\u0c3f\u0c15 \u0c28\u0c3f\u0c15\u0c30 \u0c32\u0c3e\u0c2d\u0c3e\u0c28\u0c4d\u0c28\u0c3f \u0c32\u0c46\u0c15\u0c4d\u0c15\u0c3f\u0c02\u0c1a\u0c02\u0c21\u0c3f."
                                }
                        },
                        "configuration": {
                                "ev_unit_margin": 8500,
                                "solar_unit_margin": 20000,
                                "insurance_unit_margin": 625,
                                "realestate_deal_margin": 60000,
                                "training_student_margin": 2500,
                                "monthly_opex": 47500,
                                "initial_investment": 1350000
                        },
                        "media_gallery": []
                },
                {
                        "section_type": "packages_pricing",
                        "section_key": "packages",
                        "title": "Franchise Investment Packages",
                        "subtitle": "Choose the right operational scale for your town, mandal, or district.",
                        "content_variants": {
                                "en": {
                                        "title": "Franchise Investment Packages",
                                        "subtitle": "Choose the right operational scale for your town, mandal, or district."
                                },
                                "te": {
                                        "title": "\u0c2b\u0c4d\u0c30\u0c3e\u0c02\u0c1a\u0c48\u0c1c\u0c4d \u0c2a\u0c46\u0c1f\u0c4d\u0c1f\u0c41\u0c2c\u0c21\u0c3f \u0c2a\u0c4d\u0c2f\u0c3e\u0c15\u0c47\u0c1c\u0c40\u0c32\u0c41",
                                        "subtitle": "\u0c2e\u0c40 \u0c35\u0c4d\u0c2f\u0c3e\u0c2a\u0c3e\u0c30 \u0c38\u0c3e\u0c2e\u0c30\u0c4d\u0c25\u0c4d\u0c2f\u0c02 \u0c2e\u0c30\u0c3f\u0c2f\u0c41 \u0c35\u0c3f\u0c38\u0c4d\u0c24\u0c30\u0c23 \u0c32\u0c15\u0c4d\u0c37\u0c4d\u0c2f\u0c3e\u0c32\u0c15\u0c41 \u0c38\u0c30\u0c3f\u0c2a\u0c4b\u0c2f\u0c47 \u0c2e\u0c4b\u0c21\u0c32\u0c4d\u200c\u0c28\u0c41 \u0c0e\u0c02\u0c1a\u0c41\u0c15\u0c4b\u0c02\u0c21\u0c3f."
                                }
                        },
                        "configuration": {},
                        "media_gallery": []
                },
                {
                        "section_type": "process_workflow",
                        "section_key": "launch_roadmap",
                        "title": "30-Day Showroom Launch Roadmap",
                        "subtitle": "From agreement signing to your grand opening \u2014 complete turnkey execution timeline.",
                        "content_variants": {
                                "en": {
                                        "title": "30-Day Showroom Launch Roadmap",
                                        "subtitle": "From agreement signing to your grand opening \u2014 complete turnkey execution timeline."
                                },
                                "te": {
                                        "title": "30 \u0c30\u0c4b\u0c1c\u0c41\u0c32 \u0c37\u0c4b\u0c30\u0c42\u0c2e\u0c4d \u0c2a\u0c4d\u0c30\u0c3e\u0c30\u0c02\u0c2d \u0c30\u0c4b\u0c21\u0c4d\u200c\u0c2e\u0c4d\u0c2f\u0c3e\u0c2a\u0c4d",
                                        "subtitle": "\u0c12\u0c2a\u0c4d\u0c2a\u0c02\u0c26\u0c02 \u0c15\u0c41\u0c26\u0c3f\u0c30\u0c3f\u0c28 \u0c28\u0c3e\u0c1f\u0c3f \u0c28\u0c41\u0c02\u0c21\u0c3f \u0c17\u0c4d\u0c30\u0c3e\u0c02\u0c21\u0c4d \u0c13\u0c2a\u0c46\u0c28\u0c3f\u0c02\u0c17\u0c4d \u0c35\u0c30\u0c15\u0c41 \u0c26\u0c36\u0c32\u0c35\u0c3e\u0c30\u0c40 \u0c15\u0c3e\u0c30\u0c4d\u0c2f\u0c3e\u0c1a\u0c30\u0c23 \u0c2a\u0c4d\u0c30\u0c23\u0c3e\u0c33\u0c3f\u0c15."
                                }
                        },
                        "configuration": {
                                "steps": [
                                        {
                                                "day": "Days 1\u20137",
                                                "title": "Territory Allocation & Agreement",
                                                "desc": "Exclusive mandal/pincode mandate allocation, legal documentation, and onboarding fee execution."
                                        },
                                        {
                                                "day": "Days 8\u201314",
                                                "title": "Store Selection & 3D Layout Design",
                                                "desc": "Corporate site feasibility audit (500\u20131,000 sq.ft.), architectural floor plans, and 3D interior design drawings."
                                        },
                                        {
                                                "day": "Days 15\u201321",
                                                "title": "Hardware, Signage & Stock Dispatch",
                                                "desc": "Dispatch of Windows PC, 43\" Smart TV, Color Printer, 3D acrylic signage, 4\u20136 Display Scooters & Solar Demo kit."
                                        },
                                        {
                                                "day": "Days 22\u201326",
                                                "title": "On-Site Staff Induction & Workshop Training",
                                                "desc": "5-day intensive training for showroom sales team, CRM billing software induction, and technician mechanic lab training."
                                        },
                                        {
                                                "day": "Days 27\u201329",
                                                "title": "Marketing Canopy Setup & Digital Ads Launch",
                                                "desc": "Outdoor marketing canopy installation, local promotional flyer distribution, and Google/social media ad campaigns activation."
                                        },
                                        {
                                                "day": "Day 30",
                                                "title": "Grand Showroom Opening",
                                                "desc": "Inaugural community event with local VIP guests, customer test rides, on-spot bookings, and media coverage."
                                        }
                                ]
                        },
                        "media_gallery": []
                },
                {
                        "section_type": "video_showcase",
                        "section_key": "video_hub",
                        "title": "Watch MyntReal Hub in Action (Video Showcase)",
                        "subtitle": "Experience the operational ambiance and hear from company leadership.",
                        "content_variants": {
                                "en": {
                                        "title": "Watch MyntReal Hub in Action (Video Showcase)",
                                        "subtitle": "Experience the operational ambiance and hear from company leadership."
                                },
                                "te": {
                                        "title": "\u0c2e\u0c48\u0c02\u0c1f\u0c4d \u0c30\u0c3f\u0c2f\u0c32\u0c4d \u0c39\u0c2c\u0c4d \u0c35\u0c40\u0c21\u0c3f\u0c2f\u0c4b \u0c1f\u0c42\u0c30\u0c4d",
                                        "subtitle": "\u0c37\u0c4b\u0c30\u0c42\u0c2e\u0c4d \u0c28\u0c3f\u0c30\u0c4d\u0c35\u0c39\u0c23, \u0c35\u0c4d\u0c2f\u0c3e\u0c2a\u0c3e\u0c30 \u0c28\u0c2e\u0c42\u0c28\u0c3e \u0c2e\u0c30\u0c3f\u0c2f\u0c41 \u0c28\u0c3e\u0c2f\u0c15\u0c24\u0c4d\u0c35 \u0c07\u0c02\u0c1f\u0c30\u0c4d\u0c35\u0c4d\u0c2f\u0c42\u0c32\u0c28\u0c41 \u0c35\u0c40\u0c15\u0c4d\u0c37\u0c3f\u0c02\u0c1a\u0c02\u0c21\u0c3f."
                                }
                        },
                        "configuration": {
                                "videos": [
                                        {
                                                "id": "FzKh_AVXiRo",
                                                "title": "One Store. Multiple Businesses. | Inside MyntReal Business Hub",
                                                "badge": "Live Showroom Walkthrough",
                                                "desc": "Take a virtual tour through an active operational hub displaying the Manthra EV showroom floor, solar rooftop customer desk, insurance terminal, and EV technician workshop."
                                        },
                                        {
                                                "id": "FD_k-thN96I",
                                                "title": "Start Your Own Business with MyntReal | Multiple Income Opportunities",
                                                "badge": "Investor Business Model",
                                                "desc": "In-depth presentation by executive leadership explaining dealer profit margins, zero dead-stock inventory policies, bank loan tie-ups, and regional support."
                                        }
                                ]
                        },
                        "media_gallery": []
                },
                {
                        "section_type": "press_publications",
                        "section_key": "press_publications",
                        "title": "National Media Coverage & ISO Accreditations",
                        "subtitle": "Recognized across leading national publications and trade journals for rural clean energy entrepreneurship.",
                        "content_variants": {
                                "en": {
                                        "title": "National Media Coverage & ISO Accreditations",
                                        "subtitle": "Recognized across leading national publications and trade journals for rural clean energy entrepreneurship."
                                },
                                "te": {
                                        "title": "\u0c1c\u0c3e\u0c24\u0c40\u0c2f \u0c2e\u0c40\u0c21\u0c3f\u0c2f\u0c3e \u0c17\u0c41\u0c30\u0c4d\u0c24\u0c3f\u0c02\u0c2a\u0c41 & ISO \u0c38\u0c30\u0c4d\u0c1f\u0c3f\u0c2b\u0c3f\u0c15\u0c47\u0c37\u0c28\u0c4d\u0c32\u0c41",
                                        "subtitle": "\u0c2a\u0c4d\u0c30\u0c2e\u0c41\u0c16 \u0c1c\u0c3e\u0c24\u0c40\u0c2f \u0c26\u0c3f\u0c28\u0c2a\u0c24\u0c4d\u0c30\u0c3f\u0c15\u0c32\u0c41 \u0c2e\u0c30\u0c3f\u0c2f\u0c41 \u0c2c\u0c3f\u0c1c\u0c3f\u0c28\u0c46\u0c38\u0c4d \u0c1c\u0c30\u0c4d\u0c28\u0c32\u0c4d\u0c38\u0c4d\u200c\u0c32\u0c4b \u0c2e\u0c48\u0c02\u0c1f\u0c4d \u0c30\u0c3f\u0c2f\u0c32\u0c4d \u0c35\u0c3f\u0c1c\u0c2f\u0c17\u0c3e\u0c25\u0c32\u0c41."
                                }
                        },
                        "configuration": {
                                "publications": [
                                        {
                                                "source": "Mid-Day National Feature (2026)",
                                                "badge": "National Impact Award",
                                                "title": "Leading Professionals Making an Impact in 2026",
                                                "honoree": "Jagannadh Velaga (Director & CSO, MyntReal / Zynova Mobility)",
                                                "summary": "Honored among India's top business visionaries for pioneering the 5-in-1 clean energy hub model, bridging electric mobility and solar energy to tier-2, tier-3, and rural communities."
                                        },
                                        {
                                                "source": "News Indian Link \u2022 Buzz Center \u2022 News Economic India",
                                                "badge": "Rural Network Expansion",
                                                "title": "MyntReal Launches Multi-Business Network in Rajavommangi",
                                                "honoree": "Tribal Belt Green Mobility Drive",
                                                "summary": "National press highlighting MyntReal's rural expansion into Alluri Sitharama Raju District, creating localized green entrepreneurship, EV sales, and rooftop solar adoption."
                                        },
                                        {
                                                "source": "National Franchise Research Bureau (2026)",
                                                "badge": "Best Franchise Ranking",
                                                "title": "Best Business Opportunities Under \u20b915 Lakhs in India",
                                                "honoree": "Highest Rated Investment Model",
                                                "summary": "Ranked as India's best franchise under \u20b915 Lakhs capital due to 5 diversified revenue pillars mitigating retail market volatility and yielding 6\u20139 months break-even."
                                        }
                                ],
                                "certifications": [
                                        {
                                                "name": "ISO 9001:2015",
                                                "sub": "Quality Management System Certified"
                                        },
                                        {
                                                "name": "ISO 27001",
                                                "sub": "Information Security Management"
                                        },
                                        {
                                                "name": "Govt. Polytechnic Partner",
                                                "sub": "Pendurthi Campus Advanced EV Lab"
                                        },
                                        {
                                                "name": "Zynova Mobility & MNR",
                                                "sub": "Strategic Corporate Associations"
                                        }
                                ]
                        },
                        "media_gallery": []
                },
                {
                        "section_type": "contact_cta",
                        "section_key": "cta",
                        "title": "Apply for Your District Franchise Mandate",
                        "subtitle": "Territories are allocated on an exclusive mandal mandate. Connect with our Franchise Expansion Directors today.",
                        "content_variants": {
                                "en": {
                                        "title": "Apply for Your District Franchise Mandate",
                                        "subtitle": "Territories are allocated on an exclusive mandal mandate. Connect with our Franchise Expansion Directors today.",
                                        "cta_button": "Apply for Franchise Territory Exclusivity"
                                },
                                "te": {
                                        "title": "\u0c2e\u0c40 \u0c1c\u0c3f\u0c32\u0c4d\u0c32\u0c3e / \u0c2e\u0c02\u0c21\u0c32\u0c4d \u0c2b\u0c4d\u0c30\u0c3e\u0c02\u0c1a\u0c48\u0c1c\u0c40 \u0c15\u0c4b\u0c38\u0c02 \u0c07\u0c2a\u0c4d\u0c2a\u0c41\u0c21\u0c47 \u0c26\u0c30\u0c16\u0c3e\u0c38\u0c4d\u0c24\u0c41 \u0c1a\u0c47\u0c38\u0c41\u0c15\u0c4b\u0c02\u0c21\u0c3f",
                                        "subtitle": "\u0c2a\u0c4d\u0c30\u0c24\u0c4d\u0c2f\u0c47\u0c15 \u0c2e\u0c02\u0c21\u0c32\u0c4d \u0c05\u0c27\u0c3f\u0c15\u0c3e\u0c30\u0c3e\u0c32\u0c41 \u0c2a\u0c30\u0c3f\u0c2e\u0c3f\u0c24\u0c02\u0c17\u0c3e \u0c2e\u0c3e\u0c24\u0c4d\u0c30\u0c2e\u0c47 \u0c09\u0c02\u0c1f\u0c3e\u0c2f\u0c3f. \u0c35\u0c46\u0c02\u0c1f\u0c28\u0c47 \u0c2e\u0c3e \u0c2b\u0c4d\u0c30\u0c3e\u0c02\u0c1a\u0c48\u0c1c\u0c4d \u0c2c\u0c43\u0c02\u0c26\u0c3e\u0c28\u0c4d\u0c28\u0c3f \u0c38\u0c02\u0c2a\u0c4d\u0c30\u0c26\u0c3f\u0c02\u0c1a\u0c02\u0c21\u0c3f.",
                                        "cta_button": "\u0c2b\u0c4d\u0c30\u0c3e\u0c02\u0c1a\u0c48\u0c1c\u0c4d \u0c1f\u0c46\u0c30\u0c3f\u0c1f\u0c30\u0c40 \u0c15\u0c4b\u0c38\u0c02 \u0c26\u0c30\u0c16\u0c3e\u0c38\u0c4d\u0c24\u0c41 \u0c1a\u0c47\u0c38\u0c41\u0c15\u0c4b\u0c02\u0c21\u0c3f"
                                }
                        },
                        "configuration": {
                                "phone": "+91 858585 2738",
                                "email": "contact@myntreal.com",
                                "corporate_hq": "4th Floor, V-Square, Rama Talkies Road, Visakhapatnam, Andhra Pradesh \u2014 530013",
                                "campus_venue": "Survey No. 156/1, Main Road Saripalli, Opp: Petrol Bunk, Pendurthi Mandal, Visakhapatnam - 531173"
                        },
                        "media_gallery": []
                }
        ],
        "items": [
                {
                        "item_type": "PACKAGE",
                        "item_code": "HUB-5IN1-INVESTOR",
                        "title": "MyntReal Hub \u2014 5-in-1 Franchise (Flagship)",
                        "subtitle": "Complete turnkey ecosystem: EV Dealership + Solar EPC + Insurance + Real Estate + EV Training desk.",
                        "specifications": [
                                {
                                        "label": "Business Streams",
                                        "value": "5 High-Growth Verticals"
                                },
                                {
                                        "label": "Hardware Included",
                                        "value": "Free PC + 43\" Smart TV + Color Printer"
                                },
                                {
                                        "label": "Showroom Stock",
                                        "value": "4 to 6 Display Manthra EV Scooters"
                                },
                                {
                                        "label": "Solar Demo",
                                        "value": "Live Rooftop On-Grid Structure Included"
                                },
                                {
                                        "label": "Lead Support",
                                        "value": "12 Months Central Digital Inbound Leads"
                                },
                                {
                                        "label": "Expected Annual Net",
                                        "value": "\u20b919,80,000 / year (~140% ROI)"
                                }
                        ],
                        "pricing": {
                                "currency": "INR",
                                "base_price": 1200000,
                                "max_price": 1500000,
                                "price_text": "\u20b912,00,000 \u2013 \u20b915,00,000"
                        },
                        "media_urls": [
                                "/public/hub/Assets/hero-bg.webp"
                        ],
                        "badges": [
                                "\u2b50 Flagship Model",
                                "5 Franchises in 1",
                                "6\u20139 Mo Payback"
                        ],
                        "sort_order": 1,
                        "is_featured": True
                },
                {
                        "item_type": "PACKAGE",
                        "item_code": "HUB-EV-STANDALONE",
                        "title": "Standalone Manthra EV Dealership",
                        "subtitle": "Dedicated electric 2-wheeler sales, spare parts warehouse & servicing showroom.",
                        "specifications": [
                                {
                                        "label": "Showroom Space",
                                        "value": "400 \u2013 800 sq.ft."
                                },
                                {
                                        "label": "Display Vehicles",
                                        "value": "4 Manthra EV Scooters"
                                },
                                {
                                        "label": "Service Bay",
                                        "value": "Diagnostic Scanner & Technician Tools"
                                },
                                {
                                        "label": "Branding",
                                        "value": "Manthra EV 3D Exterior Signage"
                                },
                                {
                                        "label": "Expected Annual Net",
                                        "value": "\u20b96,00,000 \u2013 \u20b910,00,000 / yr"
                                }
                        ],
                        "pricing": {
                                "currency": "INR",
                                "base_price": 800000,
                                "max_price": 1200000,
                                "price_text": "\u20b98,00,000 \u2013 \u20b912,00,000"
                        },
                        "media_urls": [
                                "/public/hub/Assets/Manthra-D.webp"
                        ],
                        "badges": [
                                "EV Dealership",
                                "High Demand"
                        ],
                        "sort_order": 2,
                        "is_featured": False
                },
                {
                        "item_type": "PACKAGE",
                        "item_code": "HUB-REG-MASTER",
                        "title": "District Regional Master Hub Partner",
                        "subtitle": "District-level apex partnership with overriding royalties across 5 to 10 satellite hubs.",
                        "specifications": [
                                {
                                        "label": "Territory",
                                        "value": "Entire District Exclusive Mandate"
                                },
                                {
                                        "label": "Facility",
                                        "value": "Central Warehouse & Spare Parts Depot"
                                },
                                {
                                        "label": "Overriding Royalty",
                                        "value": "Royalty Override on All Mandal Sub-Hubs"
                                },
                                {
                                        "label": "Dispatch Line",
                                        "value": "Direct Factory Dispatch Priority"
                                },
                                {
                                        "label": "Dedicated Manager",
                                        "value": "Corporate Territory Key Account Manager"
                                }
                        ],
                        "pricing": {
                                "currency": "INR",
                                "base_price": 4000000,
                                "max_price": 5000000,
                                "price_text": "\u20b940,00,000+"
                        },
                        "media_urls": [
                                "/public/hub/Assets/Solar_D.webp"
                        ],
                        "badges": [
                                "District Mandate",
                                "Overriding Royalty"
                        ],
                        "sort_order": 3,
                        "is_featured": False
                },
                {
                        "item_type": "PRODUCT",
                        "item_code": "EV-BEAST-PRO",
                        "title": "Manthra EV Beast Pro",
                        "subtitle": "High-Performance Urban Flagship with 60–100 km Range & Dual Disc CBS",
                        "specifications": [
                                {
                                        "label": "Speed Category",
                                        "value": "Low-Speed (<25 km/h) • Non-RTO"
                                },
                                {
                                        "label": "Range",
                                        "value": "60 – 100 km / charge"
                                },
                                {
                                        "label": "Battery Options",
                                        "value": "60V 30Ah / 45Ah LTM/LFP Smart Fast Charge"
                                },
                                {
                                        "label": "Charge Time",
                                        "value": "4–5 Hours (Smart Fast Charge)"
                                },
                                {
                                        "label": "Brakes",
                                        "value": "Dual Disc CBS with E-ABS"
                                },
                                {
                                        "label": "Dealer Margin",
                                        "value": "12% (~₹7,200 avg per vehicle)"
                                }
                        ],
                        "pricing": {
                                "currency": "INR",
                                "base_price": 47999,
                                "max_price": 99499,
                                "price_text": "₹47,999 – ₹99,499"
                        },
                        "media_urls": [
                                "/public/hub/Assets/manthra-beast-real.webp"
                        ],
                        "badges": [
                                "Flagship Beast",
                                "Dual Disc CBS",
                                "100 km Range"
                        ],
                        "sort_order": 4,
                        "is_featured": True
                },
                {
                        "item_type": "PRODUCT",
                        "item_code": "EV-ROYAL-SLING",
                        "title": "Manthra EV Royal Sling",
                        "subtitle": "Vintage Classic Luxury with Smart Digital Console & Retro Comfort",
                        "specifications": [
                                {
                                        "label": "Speed Category",
                                        "value": "Low-Speed (<25 km/h) • Non-RTO"
                                },
                                {
                                        "label": "Range",
                                        "value": "60 – 100 km / charge"
                                },
                                {
                                        "label": "Battery Options",
                                        "value": "60V 30Ah / 45Ah LTM/LFP Smart Fast Charge"
                                },
                                {
                                        "label": "Charge Time",
                                        "value": "4–5 Hours (Smart Fast Charge)"
                                },
                                {
                                        "label": "Features",
                                        "value": "Anti-Theft Remote Alarm, USB Port"
                                },
                                {
                                        "label": "Dealer Margin",
                                        "value": "12% (~₹7,200 avg per vehicle)"
                                }
                        ],
                        "pricing": {
                                "currency": "INR",
                                "base_price": 45999,
                                "max_price": 96999,
                                "price_text": "₹45,999 – ₹96,999"
                        },
                        "media_urls": [
                                "/public/hub/Assets/manthra-royal-real.webp"
                        ],
                        "badges": [
                                "Vintage Luxury",
                                "Retro Style",
                                "LTM / LFP Tech"
                        ],
                        "sort_order": 5,
                        "is_featured": False
                },
                {
                        "item_type": "PRODUCT",
                        "item_code": "EV-M99",
                        "title": "Manthra EV M99 Flagship",
                        "subtitle": "Next-Gen High-Performance Urban Commuter Flagship with Smart LCD Display",
                        "specifications": [
                                {
                                        "label": "Speed Category",
                                        "value": "Low-Speed (<25 km/h) • Non-RTO"
                                },
                                {
                                        "label": "Range",
                                        "value": "60 – 100 km / charge"
                                },
                                {
                                        "label": "Battery Options",
                                        "value": "60V 30Ah / 45Ah LTM/LFP Smart Fast Charge"
                                },
                                {
                                        "label": "Charge Time",
                                        "value": "4–5 Hours (Smart Fast Charge)"
                                },
                                {
                                        "label": "Features",
                                        "value": "Reverse Drive Assist, Keyless Start, Smart LCD"
                                },
                                {
                                        "label": "Dealer Margin",
                                        "value": "12% (~₹7,200 avg per vehicle)"
                                }
                        ],
                        "pricing": {
                                "currency": "INR",
                                "base_price": 45999,
                                "max_price": 96999,
                                "price_text": "₹45,999 – ₹96,999"
                        },
                        "media_urls": [
                                "/public/hub/Assets/manthra-m99-real.webp"
                        ],
                        "badges": [
                                "Flagship Edition",
                                "Smart Digital",
                                "Next-Gen EV"
                        ],
                        "sort_order": 6,
                        "is_featured": True
                },
                {
                        "item_type": "PRODUCT",
                        "item_code": "EV-POWER-PLUS",
                        "title": "Manthra EV Power Plus",
                        "subtitle": "Heavy-Duty Commercial Delivery & Cargo with 200 kg Payload Capacity",
                        "specifications": [
                                {
                                        "label": "Speed Category",
                                        "value": "Low-Speed (<25 km/h) • Non-RTO"
                                },
                                {
                                        "label": "Payload",
                                        "value": "200 kg Certified Heavy Load"
                                },
                                {
                                        "label": "Range",
                                        "value": "50 – 90 km / charge"
                                },
                                {
                                        "label": "Battery Options",
                                        "value": "Graphene 48V 30Ah / LTM-LFP 48V 30Ah & 45Ah"
                                },
                                {
                                        "label": "Charge Time",
                                        "value": "Graphene: 8 Hours | LTM/LFP: 4–5 Hours Fast"
                                },
                                {
                                        "label": "Dealer Margin",
                                        "value": "12% (~₹7,200 avg per vehicle)"
                                }
                        ],
                        "pricing": {
                                "currency": "INR",
                                "base_price": 32999,
                                "max_price": 74499,
                                "price_text": "₹32,999 – ₹74,499"
                        },
                        "media_urls": [
                                "/public/hub/Assets/manthra-power-plus-real.webp"
                        ],
                        "badges": [
                                "Heavy Duty",
                                "200 kg Payload",
                                "Commercial Utility"
                        ],
                        "sort_order": 7,
                        "is_featured": False
                },
                {
                        "item_type": "PRODUCT",
                        "item_code": "EV-PRO-GT",
                        "title": "Manthra EV Pro GT",
                        "subtitle": "Sport Street Smart Commuter with Aerodynamic Styling & LED Lighting",
                        "specifications": [
                                {
                                        "label": "Speed Category",
                                        "value": "Low-Speed (<25 km/h) • Non-RTO"
                                },
                                {
                                        "label": "Range",
                                        "value": "50 – 90 km / charge"
                                },
                                {
                                        "label": "Battery Options",
                                        "value": "Graphene 48V 30Ah / LTM-LFP 48V 30Ah & 45Ah"
                                },
                                {
                                        "label": "Charge Time",
                                        "value": "Graphene: 8 Hours | LTM/LFP: 4–5 Hours Fast"
                                },
                                {
                                        "label": "Brakes",
                                        "value": "Dual Disc CBS with E-ABS"
                                },
                                {
                                        "label": "Dealer Margin",
                                        "value": "12% (~₹7,200 avg per vehicle)"
                                }
                        ],
                        "pricing": {
                                "currency": "INR",
                                "base_price": 31499,
                                "max_price": 72999,
                                "price_text": "₹31,499 – ₹72,999"
                        },
                        "media_urls": [
                                "/public/hub/Assets/manthra-pro-gt-real.webp"
                        ],
                        "badges": [
                                "Sport Edition",
                                "Dual Disc CBS",
                                "Smart Digital"
                        ],
                        "sort_order": 8,
                        "is_featured": False
                }
        ]
},
    {
        "segment_code": "HUB_PRICING",
        "slug": "hub-ev-pricing",
        "title": "MyntReal Hub — Confidential EV & Solar Commercial Pricing (24h)",
        "subtitle": "Confidential Wholesale Cost Sheets, Dealer Margins, Solar EPC Matrices & Unit Economics",
        "summary": "Live 24-hour expiring commercial pricing prospectus for MyntReal Hub franchise investors, including EV vehicle dealer margins (12% Hub + 10.5% Direct Sale), Graphene & LFP batteries, fast chargers, and 1kW-10kW Solar EPC.",
        "hero_media_url": "/public/hub/Assets/Myntreal.logo.png",
        "theme_config": {"primary_color": "#10b981", "accent_color": "#f59e0b", "dark_mode": True},
        "default_language": "en",
        "active_languages": ["en", "te", "hi", "ta"],
        "sections": [
            {
                "section_type": "hero",
                "section_key": "hero",
                "title": "MyntReal Hub — EV, Batteries, Chargers & Solar Pricing Matrix",
                "subtitle": "Confidential Dealer Commercials & Margins (24-Hour Link)",
                "sort_order": 0
            },
            {
                "section_type": "pricing_matrix",
                "section_key": "ev_matrix",
                "title": "EV 5-Model Wholesale Pricing & Dealer Margins",
                "subtitle": "Complete breakdown: GT Pro, Power Plus, M99, Royal Sling, Beast Pro",
                "sort_order": 1
            },
            {
                "section_type": "pricing_matrix",
                "section_key": "batteries_chargers",
                "title": "Batteries & Smart Chargers Component Costs",
                "subtitle": "Graphene & LFP 48V/60V Batteries with Fast Chargers",
                "sort_order": 2
            },
            {
                "section_type": "pricing_matrix",
                "section_key": "solar_matrix",
                "title": "Solar EPC 1kW–10kW Commercial Spread Matrix",
                "subtitle": "Showroom Margin (3.5%) + Direct Sale Margin (6.5%)",
                "sort_order": 3
            },
            {
                "section_type": "spares",
                "section_key": "spares_workshop",
                "title": "Authorized EV Spares Lab & Diagnostic Depot",
                "subtitle": "Recurring 15%-25% workshop consumable margins",
                "sort_order": 4
            },
            {
                "section_type": "financial_analysis",
                "section_key": "financial_viability",
                "title": "Financial Viability & 3-Scenario Unit Economics",
                "subtitle": "Conservative, Realistic, and Aggressive return models",
                "sort_order": 5
            },
            {
                "section_type": "calculator",
                "section_key": "roi_simulator",
                "title": "Interactive Investor ROI & Cash Flow Simulator",
                "subtitle": "Live simulator with Direct Sale 22.5% combined spread toggle",
                "sort_order": 6
            }
        ],
        "items": []
    },
    {
        "segment_code": "EV_B2B",
        "slug": "ev-commercial-fleet",
        "title": "Electric Commercial Fleet & B2B Mobility",
        "subtitle": "Heavy-Duty Cargo 2W & 3W Vehicles Built for Last-Mile Logistics & Deliveries",
        "summary": "Cut last-mile logistics operating expenses by 75%. Purpose-built cargo electric vehicles with reinforced chassis, telematics fleet tracker, and 2-minute battery swapping capability.",
        "hero_media_url": "https://images.unsplash.com/photo-1558981806-ec527fa84c39?auto=format&fit=crop&w=1600&q=80",
        "theme_config": {"primary_color": "#0284c7", "accent_color": "#10b981", "dark_mode": False},
        "default_language": "en",
        "active_languages": ["en", "te", "hi", "ta"],
        "sections": [
            {
                "section_type": "hero",
                "section_key": "hero",
                "title": "Heavy-Duty Commercial EVs Built for Logistics & Fleets",
                "subtitle": "Save ₹6,000+ Per Vehicle Every Month with Zero Fuel Costs and Zero Downtime Battery Swapping",
                "content_variants": {
                    "en": {
                        "title": "Heavy-Duty Commercial EVs Built for Logistics & Fleets",
                        "subtitle": "Save ₹6,000+ Per Vehicle Every Month with Zero Fuel Costs and Zero Downtime Battery Swapping",
                        "cta_text": "Request Fleet Trial & Quote",
                        "cta_phone": "918585852738"
                    },
                    "te": {
                        "title": "లాజిస్టిక్స్ మరియు డెలివరీ కోసం ప్రత్యేకంగా రూపొందించిన కమర్షియల్ ఈవీలు",
                        "subtitle": "ప్రతి వాహనంపై నెలకు ₹6,000+ ఆదా చేసుకోండి — తక్కువ ఖర్చు మరియు వేగవంతమైన బ్యాటరీ మార్పిడి",
                        "cta_text": "ఫ్లీట్ టెస్ట్ డ్రైవ్ బుక్ చేయండి",
                        "cta_phone": "918585852738"
                    },
                    "hi": {
                        "title": "डिलीवरी और लॉजिस्टिक्स के लिए विशेष रूप से निर्मित कमर्शियल ईवी",
                        "subtitle": "हर गाड़ी पर प्रति माह ₹6,000+ की बचत — शून्य पेट्रोल खर्च और तुरंत बैटरी स्वैपिंग",
                        "cta_text": "फ्लीट ट्रायल और कोटेशन प्राप्त करें",
                        "cta_phone": "918585852738"
                    },
                    "ta": {
                        "title": "லாஜிஸ்டிக்ஸ் மற்றும் வணிக விநியோகத்திற்கான சக்திவாய்ந்த மின்சார வாகனங்கள்",
                        "subtitle": "ஒவ்வொரு வாகனத்திற்கும் மாதம் ₹6,000+ வரை சேமிப்பு — எரிபொருள் செலவின்றி உடனடி இயக்கம்",
                        "cta_text": "வணிக மாதிரி சோதனை செய்க",
                        "cta_phone": "918585852738"
                    }
                },
                "configuration": {
                    "badge": "🚛 75% Cost Reduction vs Petrol Cargo",
                    "stats": [
                        {"label": "Payload Capacity", "value": "Up to 350 kg"},
                        {"label": "Running Cost", "value": "₹0.25 / km"},
                        {"label": "Swap Time", "value": "60 Seconds"},
                        {"label": "Battery Life", "value": "3,000+ Cycles"}
                    ]
                }
            },
            {
                "section_type": "media_gallery",
                "section_key": "installation_gallery",
                "title": "Commercial EV Fleet & Last-Mile Delivery Gallery (కమర్షియల్ ఈవీ ఫ్లీట్ గ్యాలరీ)",
                "subtitle": "Heavy-duty electric cargo 2-wheelers and 3-wheelers powering commercial deliveries",
                "content_variants": {
                    "en": {
                        "title": "Commercial EV Fleet & Last-Mile Delivery Gallery",
                        "subtitle": "See our heavy-duty cargo 2W & 3W electric fleets deployed across e-commerce, courier and logistics."
                    },
                    "te": {
                        "title": "కమర్షియల్ ఈవీ ఫ్లీట్ మరియు డెలివరీ వాహనాల గ్యాలరీ",
                        "subtitle": "ఈ-కామర్స్ మరియు లాజిస్టిక్స్ కోసం సమర్థవంతంగా పనిచేస్తున్న కార్గో ఈవీలు."
                    }
                },
                "media_gallery": [
                    {
                        "url": "https://images.unsplash.com/photo-1558981806-ec527fa84c39?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Zynova Cargo Pro 2W Fleet Deployment for Last-Mile Courier Delivery — Vizag",
                        "tag": "2W Cargo"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Zynova Cargo Max 3W Heavy Auto Loader (500kg Payload) — Autonagar",
                        "tag": "3W Loader"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Fleet Depot Overnight Smart Charging Line — Logistics Warehouse",
                        "tag": "Fleet Depot"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1580674684081-7617fbf3d745?auto=format&fit=crop&w=1200&q=80",
                        "caption": "High-Capacity Insulated Thermal Delivery Box for Fresh Grocery Fleet",
                        "tag": "Cargo Customization"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=1200&q=80",
                        "caption": "60-Second On-Route Swappable Battery Change for Commercial Couriers",
                        "tag": "Battery Swapping"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1508974239320-0a029497e820?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Commercial Fleet Telematics GPS Tracking & Real-Time Battery Telemetry",
                        "tag": "Fleet Telematics"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1521791136064-7986c2920216?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Commercial Fleet Driver Handover & Road Safety Orientation Program",
                        "tag": "Driver Handover"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1519003722824-194d4455a60c?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Heavy-Duty Incline & Load Testing (18% Flyover Gradeability)",
                        "tag": "Performance Testing"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1578575437130-527eed3abbec?auto=format&fit=crop&w=1200&q=80",
                        "caption": "24/7 Mobile Breakdown & Quick-Swap Roadside Assistance Van",
                        "tag": "Roadside Support"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1600880292203-757bb62b4baf?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Bulk Corporate Fleet Handover of 25 Units to Regional Logistics Partner",
                        "tag": "Corporate Delivery"
                    }
                ],
                "configuration": {
                    "auto_play_interval_ms": 3000,
                    "enable_lightbox": True,
                    "videos": [
                        {
                            "title": "Zynova Commercial Electric Cargo Fleet Field Test & Cost Analysis",
                            "youtube_id": "kYJmQ6X2q38",
                            "url": "https://www.youtube.com/watch?v=kYJmQ6X2q38",
                            "embed_url": "https://www.youtube-nocookie.com/embed/kYJmQ6X2q38"
                        },
                        {
                            "title": "Last Mile Logistics EV Adoption: Saving ₹60,000+ per Year",
                            "youtube_id": "0k7yF_G0lQ8",
                            "url": "https://www.youtube.com/watch?v=0k7yF_G0lQ8",
                            "embed_url": "https://www.youtube-nocookie.com/embed/0k7yF_G0lQ8"
                        }
                    ]
                }
            }
        ],
        "items": [
            {
                "item_type": "PRODUCT",
                "item_code": "EV-B2B-CARGOPRO",
                "title": "Zynova Cargo Pro 2W",
                "subtitle": "Dual-battery high-capacity cargo scooter for e-commerce, courier and grocery delivery",
                "specifications": [
                    {"label": "Payload", "value": "200 kg Certified"},
                    {"label": "Range", "value": "140 km with Dual Battery"},
                    {"label": "Battery Tech", "value": "LFP Smart Swappable Pack"},
                    {"label": "Top Speed", "value": "55 km/h"}
                ],
                "pricing": {"base_price": 84999, "currency": "INR"},
                "media_urls": ["https://images.unsplash.com/photo-1558981806-ec527fa84c39?auto=format&fit=crop&w=800&q=80"],
                "badges": ["Fleet Favorite", "Dual Battery"]
            },
            {
                "item_type": "PRODUCT",
                "item_code": "EV-B2B-CARGOMAX3W",
                "title": "Zynova Cargo Max 3W Loader",
                "subtitle": "Heavy-duty electric auto loader for intra-city logistics and industrial distribution",
                "specifications": [
                    {"label": "Payload", "value": "500 kg Heavy-Duty Deck"},
                    {"label": "Motor", "value": "3.5 kW High Torque Motor"},
                    {"label": "Range", "value": "110 km Per Charge"},
                    {"label": "Gradeability", "value": "18% Incline Climb"}
                ],
                "pricing": {"base_price": 195000, "currency": "INR"},
                "media_urls": ["https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?auto=format&fit=crop&w=800&q=80"],
                "badges": ["500kg Payload", "High Torque"]
            }
        ]
    },
    {
        "segment_code": "EV_B2C",
        "slug": "ev-b2c-pricing",
        "title": "Manthra EV — Smart Electric 2-Wheelers & Customer Pricing",
        "subtitle": "Certified Non-RTO Low-Speed (<25 km/h) Electric Scooters with Graphene & LFP Dual Battery Options",
        "summary": "Official customer pricing and vehicle catalog for Manthra EV electric scooters. Non-RTO (<25 km/h) requiring zero driving license, ultra-low ₹0.15/km running cost, Graphene 48V 32Ah (9 Mo warranty) and Smart LFP (3 Yrs warranty) options.",
        "hero_media_url": "/public/hub/Assets/manthra-fleet-lineup.webp",
        "theme_config": {"primary_color": "#059669", "accent_color": "#f59e0b", "dark_mode": False},
        "default_language": "en",
        "active_languages": ["en", "te", "hi", "ta"],
        "sections": [
            {
                "section_type": "hero",
                "section_key": "hero",
                "title": "Style, Power & Unlimited Savings — Meet Manthra EV",
                "subtitle": "Non-RTO Low-Speed (<25 km/h) • Zero Driving License • ₹0.15/km Commute Cost",
                "content_variants": {
                    "en": {"title": "Style, Power & Unlimited Savings — Meet Manthra EV", "subtitle": "Non-RTO Low-Speed (<25 km/h) • Zero Driving License • ₹0.15/km Commute Cost"},
                    "te": {"title": "స్టైల్, శక్తి మరియు అపారమైన పొదుపు — మాంత్రా EV", "subtitle": "నాన్-RTO లో-స్పీడ్ (<25 km/h) • డ్రైవింగ్ లైసెన్స్ అవసరం లేదు • కి.మీకి 15 పైసల ఖర్చు"},
                    "hi": {"title": "स्टाइल, पावर और बेमिसाल बचत — मंत्रा EV", "subtitle": "नॉन-RTO लो-स्पीड (<25 km/h) • बिना ड्राइविंग लाइसेंस • 15 पैसे प्रति किमी खर्च"},
                    "ta": {"title": "அழகும் ஆற்றலும் நிறைந்த மாந்த்ரா EV", "subtitle": "நான்-RTO குறைந்த வேகம் • ஓட்டுநர் உரிமம் தேவையில்லை • கி.மீக்கு 15 பைசா"}
                },
                "configuration": {
                    "badge": "⚡ Certified Non-RTO Commuter Electric Scooters",
                    "stats": [
                        {"label": "Running Cost", "value": "₹0.15 / km"},
                        {"label": "Top Speed", "value": "<25 km/h (Non-RTO)"},
                        {"label": "Charging Time", "value": "4 – 5 Hours"},
                        {"label": "Warranty", "value": "9 Mo / 3 Yrs"}
                    ]
                },
                "sort_order": 0
            },
            {
                "section_type": "video_showcase",
                "section_key": "video_showcase",
                "title": "Official Video Showcase — Ride Experience & Build Quality",
                "subtitle": "Watch Manthra EV in action on Indian roads",
                "configuration": {
                    "youtube_url": "https://www.youtube.com/embed/FzKh_AVXiRo?rel=0&modestbranding=1"
                },
                "sort_order": 1
            },
            {
                "section_type": "pricing_matrix",
                "section_key": "pricing_matrix",
                "title": "5 Certified Manthra EV Models & Customer Price Matrix",
                "subtitle": "Complete breakdown with Graphene 48V 32Ah (9 Mo) & LFP (3 Yrs) Warranties",
                "sort_order": 2
            },
            {
                "section_type": "standalone_batteries",
                "section_key": "standalone_batteries",
                "title": "Standalone OEM Batteries & Smart Fast Chargers",
                "subtitle": "Graphene 48V 32Ah (9 Mo) & Smart LFP 48V/60V (3 Yrs) replacement packs",
                "sort_order": 3
            },
            {
                "section_type": "other_services",
                "section_key": "other_services",
                "title": "Our Integrated Customer Services: Solar, Insurance & Spares",
                "subtitle": "Rooftop Solar EPC (PM Surya Ghar Subsidy), Zero-Dep EV Insurance & Genuine OEM Spares",
                "sort_order": 4
            }
        ],
        "items": [
            {
                "item_type": "PRODUCT",
                "item_code": "EV-PRO-GT",
                "title": "Manthra EV Pro GT",
                "subtitle": "Sport Street Commuter (Low-Speed Non-RTO)",
                "summary": "Aerodynamic urban street commuter with matrix LED headlamp, digital LCD cluster, and disc CBS braking.",
                "specifications": [
                    {"label": "Top Speed", "value": "<25 km/h (Non-RTO)"},
                    {"label": "Range", "value": "65 – 125 km (Battery Dependent)"},
                    {"label": "Battery Options", "value": "Graphene 48V 32Ah (9M) / Smart LFP (3Y)"},
                    {"label": "License", "value": "Zero License Required"}
                ],
                "pricing": {"base_price": 49923, "max_price": 81788, "currency": "INR", "price_text": "₹49,923 – ₹81,788"},
                "media_urls": ["/public/hub/Assets/manthra-pro-gt-real.webp"],
                "badges": ["Sport Commuter", "Non-RTO", "Zero License"],
                "sort_order": 0
            },
            {
                "item_type": "PRODUCT",
                "item_code": "EV-POWER-PLUS",
                "title": "Manthra EV Power Plus",
                "subtitle": "Heavy-Duty Cargo & Delivery (200kg Load)",
                "summary": "Engineered for last-mile commercial delivery, farm utility and heavy cargo with reinforced suspension.",
                "specifications": [
                    {"label": "Payload", "value": "200 kg Certified"},
                    {"label": "Top Speed", "value": "<25 km/h (Non-RTO)"},
                    {"label": "Carrier", "value": "Heavy Steel Extended Rack"},
                    {"label": "License", "value": "Zero License Required"}
                ],
                "pricing": {"base_price": 51278, "max_price": 83143, "currency": "INR", "price_text": "₹51,278 – ₹83,143"},
                "media_urls": ["/public/hub/Assets/manthra-power-plus-real.webp"],
                "badges": ["200kg Payload", "Heavy Cargo", "Non-RTO"],
                "sort_order": 1
            },
            {
                "item_type": "PRODUCT",
                "item_code": "EV-M99",
                "title": "Manthra EV M99 Flagship",
                "subtitle": "Next-Gen Urban Flagship with Reverse Assist",
                "summary": "Aerodynamic flagship scooter with 1-touch Reverse Assist, full-color digital cockpit, and smart remote keyless fob.",
                "specifications": [
                    {"label": "Features", "value": "Reverse Assist, Keyless Remote Fob"},
                    {"label": "Top Speed", "value": "<25 km/h (Non-RTO)"},
                    {"label": "Storage", "value": "26L Full Helmet Space"},
                    {"label": "License", "value": "Zero License Required"}
                ],
                "pricing": {"base_price": 80782, "max_price": 96925, "currency": "INR", "price_text": "₹80,782 – ₹96,925"},
                "media_urls": ["/public/hub/Assets/manthra-m99-real.webp"],
                "badges": ["Urban Flagship", "Reverse Assist", "Non-RTO"],
                "sort_order": 2
            },
            {
                "item_type": "PRODUCT",
                "item_code": "EV-ROYAL-SLING",
                "title": "Manthra EV Royal Sling",
                "subtitle": "Vintage Classic Luxury with Double Contour Seat",
                "summary": "Timeless retro luxury styling with chrome mirrors, premium double-contour cushion seat, and USB mobile charger.",
                "specifications": [
                    {"label": "Style", "value": "Retro Vintage Classic"},
                    {"label": "Comfort", "value": "Double Contour Seat Cushion"},
                    {"label": "Charging", "value": "Built-in Fast USB Port"},
                    {"label": "License", "value": "Zero License Required"}
                ],
                "pricing": {"base_price": 80782, "max_price": 96925, "currency": "INR", "price_text": "₹80,782 – ₹96,925"},
                "media_urls": ["/public/hub/Assets/manthra-royal-real.webp"],
                "badges": ["Vintage Luxury", "Retro Classic", "Non-RTO"],
                "sort_order": 3
            },
            {
                "item_type": "PRODUCT",
                "item_code": "EV-BEAST-PRO",
                "title": "Manthra EV Beast Pro",
                "subtitle": "Aggressive Street Flagship with Dual-Disc CBS",
                "summary": "Aggressive street styling with dual front & rear hydraulic disc brakes, nitrogen gas shocks, and CBS safety.",
                "specifications": [
                    {"label": "Brakes", "value": "Dual Front & Rear Hydraulic Disc CBS"},
                    {"label": "Suspension", "value": "Nitrogen Gas Charged Dampers"},
                    {"label": "Headlamp", "value": "Quad Projector LED Beam"},
                    {"label": "License", "value": "Zero License Required"}
                ],
                "pricing": {"base_price": 82916, "max_price": 99058, "currency": "INR", "price_text": "₹82,916 – ₹99,058"},
                "media_urls": ["/public/hub/Assets/manthra-beast-real.webp"],
                "badges": ["Street Fighter", "Dual Disc CBS", "Non-RTO"],
                "sort_order": 4
            }
        ]
    },
    {
        "segment_code": "EV_SPARES",
        "slug": "ev-spares-and-chargers",
        "title": "EV Spares, Fast Chargers & Battery Systems",
        "subtitle": "OEM-Grade Replacement Components, Smart Chargers & Advanced Lithium Packs",
        "summary": "Authorized source for certified EV spare parts, intelligent battery management systems (BMS), high-power DC fast chargers, controllers, and replacement wiring harnesses for all major EV makes.",
        "hero_media_url": "https://images.unsplash.com/photo-1593941707882-a5bba14938c7?auto=format&fit=crop&w=1600&q=80",
        "theme_config": {"primary_color": "#d97706", "accent_color": "#2563eb", "dark_mode": False},
        "default_language": "en",
        "active_languages": ["en", "te", "hi", "ta"],
        "sections": [
            {
                "section_type": "hero",
                "section_key": "hero",
                "title": "Certified OEM EV Spares, Lithium Battery Packs & DC Chargers",
                "subtitle": "Tested for Reliability, AIS-156 Safety Compliance, and Immediate Pan-India Dispatch",
                "content_variants": {
                    "en": {"title": "Certified OEM EV Spares, Lithium Battery Packs & DC Chargers", "subtitle": "Tested for Reliability, AIS-156 Safety Compliance, and Immediate Pan-India Dispatch"},
                    "te": {"title": "ధృవీకరించబడిన ఈవీ స్పేర్స్, లిథియం బ్యాటరీలు మరియు డీసీ ఫాస్ట్ ఛార్జర్లు", "subtitle": "AIS-156 భద్రతా ప్రమాణాలు మరియు తక్షణ దేశవ్యాప్త డెలివరీ"},
                    "hi": {"title": "प्रमाणित ओरिजिनल ईवी स्पेयर पार्ट्स, लीथियम बैटरियां और फास्ट चार्जर्स", "subtitle": "AIS-156 सुरक्षा प्रमाणित और तुरंत पैन-इंडिया डिलीवरी"},
                    "ta": {"title": "அங்கீகரிக்கப்பட்ட மின்சார வாகன உதிரிபாகங்கள் & பேட்டரி அமைப்புகள்", "subtitle": "உயர்தர பாதுகாப்பு மற்றும் விரைவான விநியோகம்"}
                },
                "configuration": {
                    "badge": "⚙️ AIS-156 Certified Components",
                    "stats": [
                        {"label": "SKUs in Stock", "value": "1,500+"},
                        {"label": "Quality Warranty", "value": "Up to 3 Years"},
                        {"label": "Compatibility", "value": "Universal EV Fit"},
                        {"label": "Dispatch Speed", "value": "Within 24 Hours"}
                    ]
                }
            },
            {
                "section_type": "media_gallery",
                "section_key": "installation_gallery",
                "title": "EV Spares, Battery Packs & Fast Chargers (ఈవీ స్పేర్స్ & ఛార్జర్ల గ్యాలరీ)",
                "subtitle": "AIS-156 Phase 2 certified battery packs, smart BMS boards & commercial DC fast chargers",
                "content_variants": {
                    "en": {
                        "title": "EV Spares, Battery Packs & Fast Chargers",
                        "subtitle": "Browse certified lithium iron phosphate packs, smart BMS controllers, dual-gun fast chargers and spares."
                    },
                    "te": {
                        "title": "ఈవీ స్పేర్స్, బ్యాటరీ ప్యాక్స్ & ఫాస్ట్ ఛార్జర్ల గ్యాలరీ",
                        "subtitle": "AIS-156 సర్టిఫైడ్ బ్యాటరీలు, స్మార్ట్ బీఎమ్ఎస్ మరియు కమర్షియల్ ఫాస్ట్ ఛార్జర్లు."
                    }
                },
                "media_gallery": [
                    {
                        "url": "https://images.unsplash.com/photo-1593941707882-a5bba14938c7?auto=format&fit=crop&w=1200&q=80",
                        "caption": "AIS-156 Phase 2 Certified 60V 30Ah LFP Swappable Battery Pack",
                        "tag": "Lithium Battery"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1558441719-8b449c6ff807?auto=format&fit=crop&w=1200&q=80",
                        "caption": "30 kW Dual-Gun CCS2 DC Fast Charger with RFID Card & App Billing",
                        "tag": "DC Fast Charger"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Smart Bluetooth BMS Board with Cell Balancing & Thermal Runaway Sensors",
                        "tag": "Smart BMS"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1581092160607-ee22621dd758?auto=format&fit=crop&w=1200&q=80",
                        "caption": "High-Efficiency Sine Wave BLDC Hub Motor Controller (60V/72V)",
                        "tag": "Motor Controller"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=1200&q=80",
                        "caption": "7.4 kW Type-2 AC Wallbox Home Charger with Smart App Scheduling",
                        "tag": "AC Wallbox"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1504917599217-d4dc5ebe6122?auto=format&fit=crop&w=1200&q=80",
                        "caption": "OEM Waterproof Heavy-Duty Wiring Harness with IP67 Automotive Connectors",
                        "tag": "Wiring Harness"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1580674684081-7617fbf3d745?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Ventilated Front Disc Brake Caliper & Ceramic Brake Pad Assembly",
                        "tag": "Brake Assemblies"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Precision Cell Voltage & Internal Resistance Quality Testing Rig",
                        "tag": "Quality Testing"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Ready-to-Ship Inventory Depot — Over 1,500+ Genuine EV SKUs in Stock",
                        "tag": "Spare Depot"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1584271854089-9bb3e5168e32?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Automotive Grade Safety Quality Assurance & Packaging Verification",
                        "tag": "Quality Assurance"
                    }
                ],
                "configuration": {
                    "auto_play_interval_ms": 3000,
                    "enable_lightbox": True,
                    "videos": [
                        {
                            "title": "AIS-156 Certified Lithium Iron Phosphate (LFP) Battery Manufacturing",
                            "youtube_id": "kYJmQ6X2q38",
                            "url": "https://www.youtube.com/watch?v=kYJmQ6X2q38",
                            "embed_url": "https://www.youtube-nocookie.com/embed/kYJmQ6X2q38"
                        },
                        {
                            "title": "30kW Commercial DC Fast Charger Architecture & OCPP Cloud Setup",
                            "youtube_id": "0k7yF_G0lQ8",
                            "url": "https://www.youtube.com/watch?v=0k7yF_G0lQ8",
                            "embed_url": "https://www.youtube-nocookie.com/embed/0k7yF_G0lQ8"
                        }
                    ]
                }
            }
        ],
        "items": [
            {
                "item_type": "PRODUCT",
                "item_code": "SPARE-BATT-60V30AH",
                "title": "60V 30Ah Smart LFP Battery Pack",
                "subtitle": "AIS-156 Phase 2 approved lithium iron phosphate battery with Bluetooth smart BMS",
                "specifications": [
                    {"label": "Chemistry", "value": "LiFePO4 (LFP)"},
                    {"label": "Cycle Life", "value": "2,500+ Cycles at 80% DoD"},
                    {"label": "Safety Cert", "value": "AIS-156 Certified with Thermal Runaway Protection"},
                    {"label": "Weight", "value": "approx. 14.5 kg"}
                ],
                "pricing": {"base_price": 38500, "currency": "INR"},
                "media_urls": ["https://images.unsplash.com/photo-1593941707882-a5bba14938c7?auto=format&fit=crop&w=800&q=80"],
                "badges": ["AIS-156 Approved", "Smart Bluetooth BMS"]
            },
            {
                "item_type": "PRODUCT",
                "item_code": "CHG-DC-30KW-DUAL",
                "title": "30 kW Dual-Gun CCS2 DC Fast Charger",
                "subtitle": "Commercial heavy-duty DC fast charger with OCPP 1.6J RFID and cloud billing",
                "specifications": [
                    {"label": "Output Power", "value": "30 kW (Dual-Gun Balanced)"},
                    {"label": "Gun Standard", "value": "Dual CCS2 Gun"},
                    {"label": "Ingress Rating", "value": "IP54 Outdoor Weatherproof"},
                    {"label": "Protocol", "value": "OCPP 1.6J Cloud Connected"}
                ],
                "pricing": {"base_price": 345000, "currency": "INR"},
                "media_urls": ["https://images.unsplash.com/photo-1558441719-8b449c6ff807?auto=format&fit=crop&w=800&q=80"],
                "badges": ["Dual Gun", "OCPP Cloud Connected"]
            }
        ]
    },
    {
        "segment_code": "ETC_TRAINING",
        "slug": "etc-renewable-certifications",
        "title": "EVolution Training Centre — Professional EV Certifications",
        "subtitle": "1-Week EV Technician & Entrepreneurship Certification | Govt. Polytechnic College, Pendurthi",
        "summary": "Launch a high-paying EV career or your own multi-brand EV service center. Master hands-on diagnostics of electric 2-wheelers, BLDC motors, wiring harnesses, lithium-ion battery packs & BMS debugging with 100% placement support at Govt. Polytechnic College, Pendurthi. Standard fee ₹19,999 with special scholarship discount of ₹10,000 — Final fee only ₹9,999!",
        "hero_media_url": "/public/images/etc_training/ev_practical_scooter_lab.jpg",
        "theme_config": {"primary_color": "#2563eb", "accent_color": "#f59e0b", "dark_mode": False},
        "default_language": "en",
        "active_languages": ["en", "te", "hi", "ta"],
        "sections": [
            {
                "section_type": "hero",
                "section_key": "hero",
                "title": "EVolution Training Centre — 1-Week EV Technician & Entrepreneurship Certification",
                "subtitle": "Govt. Polytechnic College, Pendurthi, Visakhapatnam | Standard Fee ₹19,999 - ₹10,000 Scholarship = Net Payable ₹9,999",
                "content_variants": {
                    "en": {
                        "title": "EVolution Training Centre — 1-Week EV Technician & Entrepreneurship Certification",
                        "subtitle": "Govt. Polytechnic College, Pendurthi, Visakhapatnam | Standard Fee ₹19,999 - ₹10,000 Scholarship = Net Payable ₹9,999",
                        "cta_text": "Enroll Now for ₹9,999",
                        "cta_phone": "918585852738"
                    },
                    "te": {
                        "title": "EVolution ట్రైనింగ్ సెంటర్ — 1-వారం ఈవీ టెక్నీషియన్ & ఎంట్రప్రెన్యూర్‌షిప్ సర్టిఫికేషన్",
                        "subtitle": "ప్రభుత్వ పాలిటెక్నిక్ కళాశాల, పెందుర్తి, విశాఖపట్నం | కోర్సు ఫీజు ₹19,999 - ప్రత్యేక స్కాలర్‌షిప్ ₹10,000 = చెల్లించాల్సిన నికర ఫీజు కేవలం ₹9,999/-",
                        "cta_text": "₹9,999 తో ఇప్పుడే నమోదు చేసుకోండి",
                        "cta_phone": "918585852738"
                    },
                    "hi": {
                        "title": "EVolution ट्रेनिंग सेंटर — 1-सप्ताह ईवी तकनीशियन और उद्यमिता सर्टिफिकेशन",
                        "subtitle": "शासकीय पॉलिटेक्निक कॉलेज, पेंदुर्ति, विशाखापट्टनम | कोर्स फीस ₹19,999 - ₹10,000 विशेष स्कॉलरशिप = अंतिम फीस मात्र ₹9,999/-",
                        "cta_text": "₹9,999 में अभी प्रवेश लें",
                        "cta_phone": "918585852738"
                    },
                    "ta": {
                        "title": "EVolution பயிற்சி மையம் — 1-வார மின்சார வாகன தொழில்நுட்ப வல்லுநர் பயிற்சி",
                        "subtitle": "அரசு பாலிடெக்னிக் கல்லூரி, பெந்துர்த்தி, விசாகப்பட்டினம் | கட்டணம் ₹19,999 - ₹10,000 உதவித்தொகை = இறுதி கட்டணம் ரூ.9,999/-",
                        "cta_text": "ரூ.9,999-ல் பதிவு செய்க",
                        "cta_phone": "918585852738"
                    }
                },
                "configuration": {
                    "badge": "🎓 Govt. Polytechnic College, Pendurthi • ISO 9001:2015 Accredited Lab",
                    "stats": [
                        {"label": "Final Net Fee", "value": "₹9,999 (Save ₹10,000)"},
                        {"label": "Training Venue", "value": "Govt. Polytechnic, Pendurthi"},
                        {"label": "Hands-on Practical", "value": "70% Workshop Hours"},
                        {"label": "Career Support", "value": "100% Placement Aid"}
                    ]
                }
            },
            {
                "section_type": "roi_calculator",
                "section_key": "calculator",
                "title": "EV Career & Workshop Earnings Calculator (ఆదాయ & వ్యాపార గణన)",
                "subtitle": "Calculate monthly technician salary or independent EV service center earnings vs your one-time ₹9,999 course investment.",
                "content_variants": {
                    "en": {
                        "title": "EV Career & Workshop Earnings Calculator",
                        "subtitle": "Calculate monthly technician salary or independent EV service center earnings vs your one-time ₹9,999 course investment."
                    },
                    "te": {
                        "title": "ఈవీ కెరీర్ & సర్వీస్ సెంటర్ ఆదాయ కాలిక్యులేటర్",
                        "subtitle": "నెలవారీ టెక్నీషియన్ జీతం లేదా సొంత సర్వీస్ పాయింట్ సంపాదనను కేవలం ₹9,999 వన్-టైమ్ కోర్సు ఫీజుతో సరిపోల్చి చూడండి."
                    },
                    "hi": {
                        "title": "ईवी करियर और सर्विस वर्कशॉप कमाई कैलकुलेटर",
                        "subtitle": "मासिक वेतन या स्वयं के सर्विस सेंटर की कमाई की तुलना ₹9,999 के एकमुश्त कोर्स निवेश से करें।"
                    },
                    "ta": {
                        "title": "மின்சார வாகன தொழில் மற்றும் வருவாய் கால்குலேட்டர்",
                        "subtitle": "மாதாந்திர வருமானம் மற்றும் சுயதொழில் வாய்ப்புகளை ரூ.9,999 பயிற்சி கட்டணத்துடன் கணக்கிடுங்கள்."
                    }
                },
                "configuration": {
                    "course_fee": 9999,
                    "scholarship_discount": 10000,
                    "standard_fee": 19999,
                    "location": "Govt. Polytechnic College, Pendurthi, Visakhapatnam",
                    "roles": [
                        {
                            "id": "technician",
                            "name": "Certified EV Service Specialist / Diagnostician",
                            "salary_range": "₹25,000 - ₹35,000 / month",
                            "payback_days": "10 - 12 Days",
                            "desc": "Placement with authorized EV dealers, fleet hubs (Manthra EV, Zypp, Swiggy/Zomato EV fleets), and OEM service workshops."
                        },
                        {
                            "id": "workshop_owner",
                            "name": "Independent Multi-Brand EV Service Center Owner",
                            "salary_range": "₹45,000 - ₹85,000 / month",
                            "payback_days": "7 - 10 Days",
                            "desc": "Start your own profitable EV repair garage with direct B2B wholesale access to 288+ genuine EV spare parts from MyntReal."
                        }
                    ]
                }
            },
            {
                "section_type": "comparison_table",
                "section_key": "pricing_matrix",
                "title": "Official EV Training Programs & Fee Matrix (కోర్సులు మరియు ఫీజు వివరాలు)",
                "subtitle": "Standard fees, scholarship discounts, net payable amounts & curriculum breakdown at Govt. Polytechnic College, Pendurthi.",
                "content_variants": {
                    "en": {
                        "title": "Official EV Training Programs & Fee Matrix",
                        "subtitle": "Standard fees, scholarship discounts, net payable amounts & curriculum breakdown at Govt. Polytechnic College, Pendurthi."
                    },
                    "te": {
                        "title": "అధికారిక ఈవీ శిక్షణా కోర్సులు & ఫీజు పట్టిక",
                        "subtitle": "స్టాండర్డ్ ఫీజు, స్కాలర్‌షిప్ రాయితీ మరియు ప్రభుత్వ పాలిటెక్నిక్ కళాశాల, పెందుర్తి వద్ద లభించే సదుపాయాల సమగ్ర పట్టిక."
                    },
                    "hi": {
                        "title": "आधिकारिक ईवी ट्रेनिंग कोर्स और फीस मैट्रिक्स",
                        "subtitle": "शासकीय पॉलिटेक्निक कॉलेज, पेंदुर्ति में उपलब्ध कोर्सेस, छात्रवृत्ति छूट और शुद्ध देय फीस की सूची।"
                    },
                    "ta": {
                        "title": "அரசு பாலிடெக்னிக் கல்லூரி பயிற்சி திட்டங்கள் மற்றும் கட்டண விபரம்",
                        "subtitle": "அடிப்படை கட்டணம், உதவித்தொகை தள்ளுபடி மற்றும் இறுதி கட்டண ஒப்பீட்டு அட்டவணை."
                    }
                },
                "configuration": {
                    "columns": [
                        "Course Program",
                        "Duration",
                        "Training Venue",
                        "Standard Fee (₹)",
                        "Scholarship Discount (₹)",
                        "Final Net Fee (₹)",
                        "Practical Ratio",
                        "Tools & Kit",
                        "Certification",
                        "Placement Aid"
                    ],
                    "rows": [
                        {
                            "program": "1-Week EV Technician & Entrepreneurship Certification",
                            "duration": "1 Week (7 Days, 36 Hours)",
                            "venue": "Govt. Polytechnic College, Pendurthi",
                            "standard_fee": 19999,
                            "discount": 10000,
                            "net_fee": 9999,
                            "practical_ratio": "70% Hands-on Lab",
                            "kit": "Optional / Extra Pricing (Lab Tools Provided)",
                            "certification": "ISO 9001:2015 Accredited Certificate",
                            "placement": "100% Placement Support",
                            "is_recommended": True,
                            "badge": "Special Batch Offer — ₹10,000 Scholarship"
                        },
                        {
                            "program": "2-Week EV Workshop & Spares Dealership Setup",
                            "duration": "2 Weeks (14 Days, 72 Hours)",
                            "venue": "Govt. Polytechnic College, Pendurthi",
                            "standard_fee": 29999,
                            "discount": 10000,
                            "net_fee": 19999,
                            "practical_ratio": "75% Practical + Workshop Setup",
                            "kit": "Optional / Extra Pricing (Wholesale Portal Included)",
                            "certification": "Master EV Technician & Franchisee",
                            "placement": "MyntReal Dealership Tie-up",
                            "is_recommended": False
                        }
                    ]
                }
            },
            {
                "section_type": "media_gallery",
                "section_key": "installation_gallery",
                "title": "EV Hands-on Practical Labs & Certificate Distribution Showcase (ల్యాబ్స్ & సర్టిఫికేషన్ గ్యాలరీ)",
                "subtitle": "Live vehicle teardown, motor diagnostic sessions, and graduation ceremonies at Govt. Polytechnic College, Pendurthi",
                "content_variants": {
                    "en": {
                        "title": "EV Hands-on Practical Labs & Certificate Distribution Showcase",
                        "subtitle": "Live vehicle teardown, motor diagnostic sessions, and graduation ceremonies at Govt. Polytechnic College, Pendurthi"
                    },
                    "te": {
                        "title": "ప్రాక్టికల్ ల్యాబ్స్, వర్క్‌షాప్ & సర్టిఫికేట్ ప్రదానోత్సవ గ్యాలరీ",
                        "subtitle": "ప్రభుత్వ పాలిటెక్నిక్ కళాశాల, పెందుర్తిలో జరిగిన లైవ్ వెహికల్ సర్వీసింగ్, మోటార్ టెస్టింగ్ మరియు విద్యార్థులకు సర్టిఫికెట్ల పంపిణీ."
                    },
                    "hi": {
                        "title": "ईवी प्रैक्टिकल लैब्स और सर्टिफिकेट वितरण गैलरी",
                        "subtitle": "शासकीय पॉलिटेक्निक कॉलेज, पेंदुर्ति में लाइव वाहन डिसमेंटलिंग, मोटर टेस्टिंग और प्रमाण-पत्र वितरण।"
                    },
                    "ta": {
                        "title": "மின்சார வாகன செய்முறை கூடம் மற்றும் சான்றிதழ் வழங்கும் விழா",
                        "subtitle": "அரசு பாலிடெக்னிக் கல்லூரி பயிற்சி பட்டறை மற்றும் மாணவர்களுக்கான சான்றிதழ் விநியோகம்."
                    }
                },
                "media_gallery": [
                    {
                        "url": "/public/images/etc_training/ev_practical_scooter_lab.jpg",
                        "caption": "Live Practical Lab: Hands-on EV 2-Wheeler Chassis & Motor Teardown at Govt. Polytechnic College Workshop",
                        "tag": "Practical Lab",
                        "location": "Govt. Polytechnic College, Pendurthi"
                    },
                    {
                        "url": "/public/images/etc_training/etc_student_certificate_award.jpg",
                        "caption": "Official Graduation: EV Technician Certificate Distribution Ceremony with Distinguished Guests",
                        "tag": "Certification Award",
                        "location": "Govt. Polytechnic College, Pendurthi"
                    },
                    {
                        "url": "/public/images/etc_training/etc_certified_students_group_1.png",
                        "caption": "Graduated EV Technicians & Alumni Cohort at MyntReal Operations Center",
                        "tag": "Alumni Group",
                        "location": "Visakhapatnam"
                    },
                    {
                        "url": "/public/images/etc_training/etc_certified_students_group_2.jpg",
                        "caption": "Certified EV Technicians Team Commissioning Electric Vehicles at Manthra EV Hub",
                        "tag": "Industry Placement",
                        "location": "Visakhapatnam"
                    }
                ],
                "configuration": {
                    "auto_play_interval_ms": 3000,
                    "enable_lightbox": True,
                    "videos": [
                        {
                            "title": "EVolution Training Centre — Hands-on Practical Lab & Live Vehicle Servicing at Govt. Polytechnic College, Pendurthi",
                            "youtube_id": "hD72pSe31_o",
                            "url": "https://youtu.be/hD72pSe31_o?si=yX8STTkesTjaXZgc",
                            "embed_url": "https://www.youtube-nocookie.com/embed/hD72pSe31_o"
                        }
                    ]
                }
            },
            {
                "section_type": "highlights_grid",
                "section_key": "banking",
                "title": "Transparent Fee Payment & Financial Support (ఫీజు చెల్లింపు & ఆర్థిక సదుపాయాలు)",
                "subtitle": "Direct ₹10,000 scholarship discount applied upfront. Instant UPI, net banking, and PM Mudra loan assistance.",
                "content_variants": {
                    "en": {
                        "title": "Transparent Fee Payment & Financial Support",
                        "subtitle": "Direct ₹10,000 institutional scholarship applied upfront. Instant digital payment and PM Mudra startup loan assistance."
                    },
                    "te": {
                        "title": "పారదర్శక ఫీజు చెల్లింపు & ఆర్థిక సదుపాయం",
                        "subtitle": "₹10,000 ప్రత్యేక స్కాలర్‌షిప్ తక్షణమే వర్తిస్తుంది. ఇన్‌స్టంట్ UPI డిజిటల్ పేమెంట్ మరియు ముద్ర స్టార్టప్ లోన్ మార్గదర్శకత్వం."
                    }
                },
                "configuration": {
                    "banks": [
                        {
                            "name": "Instant Digital UPI / QR",
                            "badge": "1-Tap Payment",
                            "logo": "/public/favicon.ico",
                            "tenure": "Instant",
                            "highlights": "GPay, PhonePe, Paytm, Net Banking • Instant Seat Confirmation"
                        },
                        {
                            "name": "₹10,000 Direct Scholarship",
                            "badge": "Govt Polytechnic Center",
                            "logo": "/public/favicon.ico",
                            "tenure": "Upfront Waiver",
                            "highlights": "₹19,999 Standard Fee reduced to ₹9,999 Net Payable"
                        },
                        {
                            "name": "PM Mudra & MSME Loan",
                            "badge": "Startup Aid",
                            "logo": "/public/images/banks/sbi.svg",
                            "tenure": "Up to ₹5 Lakhs",
                            "highlights": "Project report & banking assistance for establishing independent EV repair workshop"
                        },
                        {
                            "name": "ISO 9001:2015 Accredited",
                            "badge": "Govt Recognized",
                            "logo": "/public/favicon.ico",
                            "tenure": "Verified",
                            "highlights": "Endorsed certificate recognized across dealerships, OEMs, and bank credit"
                        }
                    ]
                }
            },
            {
                "section_type": "highlights_grid",
                "section_key": "benefits",
                "title": "Why Train at EVolution Training Centre? (మా ప్రత్యేకతలు)",
                "subtitle": "Industry-aligned practical curriculum inside a premier government polytechnic campus",
                "content_variants": {
                    "en": {
                        "title": "Why Train at EVolution Training Centre?",
                        "subtitle": "Industry-aligned practical curriculum inside a premier government polytechnic campus"
                    },
                    "te": {
                        "title": "EVolution ట్రైనింగ్ సెంటర్‌ను ఎందుకు ఎంచుకోవాలి?",
                        "subtitle": "ప్రభుత్వ పాలిటెక్నిక్ కళాశాల ప్రాంగణంలో పరిశ్రమల అవసరాలకు తగిన ప్రాక్టికల్ శిక్షణ"
                    },
                    "hi": {
                        "title": "EVolution ट्रेनिंग सेंटर ही क्यों चुनें?",
                        "subtitle": "शासकीय पॉलिटेक्निक कॉलेज परिसर में अत्याधुनिक प्रैक्टिकल ट्रेनिंग"
                    },
                    "ta": {
                        "title": "EVolution பயிற்சி மையத்தை ஏன் தேர்வு செய்ய வேண்டும்?",
                        "subtitle": "அரசு பாலிடெக்னிக் கல்லூரி வளாகத்தில் தொழிற்துறை சார்ந்த செய்முறை பயிற்சி"
                    }
                },
                "configuration": {
                    "cards": [
                        {
                            "icon": "build",
                            "title": "70% Practical Hands-on Lab",
                            "desc": "Disassemble and reassemble real EV scooters, motor controllers, wiring harnesses, and training on basics of battery and chargers with individual toolstations."
                        },
                        {
                            "icon": "account_balance",
                            "title": "Govt. Polytechnic College Campus",
                            "desc": "Training conducted at Govt. Polytechnic College, Pendurthi, Visakhapatnam with state-of-the-art lab and workshop safety infrastructure."
                        },
                        {
                            "icon": "verified",
                            "title": "ISO 9001:2015 Accredited Certificate",
                            "desc": "Earn a recognized professional certificate endorsed by industry leaders, valued across EV OEMs, dealerships, and fleet operators."
                        },
                        {
                            "icon": "storefront",
                            "title": "Dealership & Spares Supply Support",
                            "desc": "Direct access to 288+ genuine EV spares on wholesale B2B terms to start your own profitable EV repair workshop immediately."
                        }
                    ]
                }
            },
            {
                "section_type": "packages_pricing",
                "section_key": "packages",
                "title": "Featured EV Certification Courses & Programs (కోర్సులు)",
                "subtitle": "Structured technical modules designed for technicians, engineers, and future EV entrepreneurs",
                "content_variants": {
                    "en": {
                        "title": "Featured EV Certification Courses & Programs",
                        "subtitle": "Structured technical modules designed for technicians, engineers, and future EV entrepreneurs"
                    },
                    "te": {
                        "title": "ప్రముఖ ఈవీ సర్టిఫికేషన్ కోర్సులు & ప్యాకేజీలు",
                        "subtitle": "టెక్నీషియన్లు, ఇంజనీర్లు మరియు ఈవీ వ్యాపారవేత్తల కోసం ప్రత్యేక శిక్షణా ప్రణాళికలు"
                    },
                    "hi": {
                        "title": "प्रमुख ईवी सर्टिफिकेशन कोर्सेस और प्रोग्राम",
                        "subtitle": "तकनीशियनों और उद्यमियों के लिए विशेष व्यावहारिक पाठ्यक्रम"
                    },
                    "ta": {
                        "title": "முக்கிய மின்சார வாகன பயிற்சி திட்டங்கள்",
                        "subtitle": "தொழில்நுட்ப வல்லுநர்கள் மற்றும் புதிய தொழில் முனைவோருக்கான படிப்புகள்"
                    }
                },
                "configuration": {
                    "plans": [
                        {
                            "name": "1-Week EV Technician & Entrepreneurship Certification",
                            "ideal_for": "Diploma / ITI / B.Tech / Auto Mechanics / EV Enthusiasts",
                            "price": "₹19,999",
                            "subsidy": "₹10,000 Special Scholarship Discount",
                            "net_cost": "₹9,999 Final Net Fee",
                            "features": [
                                "7 Days / 36 Hours Intensive Hands-on Workshop Lab",
                                "Govt. Polytechnic College, Pendurthi Campus Venue",
                                "Live Electric Scooter Teardown & Testing",
                                "Training on basics of battery and chargers",
                                "BLDC Motor Diagnostics & Controller Calibration",
                                "Professional EV Hardware Toolkit (Optional / Extra Pricing)",
                                "ISO 9001:2015 Accredited Course Certificate",
                                "100% Placement & Service Center Setup Support"
                            ],
                            "is_popular": True,
                            "rupee_tag": "₹10,000 Scholarship Applied"
                        },
                        {
                            "name": "2-Week EV Workshop & Spares Dealership Setup",
                            "ideal_for": "Entrepreneurs / Garage Owners / Business Starters",
                            "price": "₹29,999",
                            "subsidy": "₹10,000 Entrepreneur Scholarship",
                            "net_cost": "₹19,999 Final Net Fee",
                            "features": [
                                "14 Days / 72 Hours Advanced Hands-on & Incubation Program",
                                "Govt. Polytechnic College & Workshop Bay Venue",
                                "Multi-Brand EV Diagnostics & Electrical Systems",
                                "Training on basics of battery and chargers",
                                "Workshop Machinery Sourcing & Layout Blueprint",
                                "Direct Wholesale Dealership Access to 288+ Genuine EV Spares",
                                "ISO 9001:2015 Accredited Master Certificate",
                                "Lifetime Technical Support & EVolution Franchise Network Access"
                            ],
                            "is_popular": False,
                            "rupee_tag": "Business Startup"
                        }
                    ]
                }
            },
            {
                "section_type": "faqs",
                "section_key": "faqs",
                "title": "Frequently Asked Questions (తరచుగా అడిగే ప్రశ్నలు)",
                "subtitle": "All questions about EV training, ₹10,000 scholarship discount, Govt. Polytechnic venue & career placements",
                "content_variants": {
                    "en": {
                        "title": "Frequently Asked Questions (FAQs)",
                        "subtitle": "All questions about EV training, ₹10,000 scholarship discount, Govt. Polytechnic venue & career placements",
                        "faqs": [
                            {"q": "Who is eligible to join this 1-Week EV training program?", "a": "ITI, Polytechnic Diploma, B.Tech students and graduates, auto mechanics, garage owners, two-wheeler technicians, and EV career enthusiasts are all eligible. No prior advanced electrical background is mandatory — the program starts with fundamental safety and builds up to practical vehicle diagnostics and training on basics of battery and chargers."},
                            {"q": "Where is the training conducted?", "a": "The training is conducted at Govt. Polytechnic College, Pendurthi, Visakhapatnam, Andhra Pradesh - 531173. The campus features high-voltage practical labs, vehicle teardown bays, and state-of-the-art testing equipment."},
                            {"q": "How does the ₹10,000 scholarship discount work?", "a": "The standard course fee is ₹19,999/-. Under our Special Green Skill Scholarship Scheme at Govt. Polytechnic College Pendurthi, a direct ₹10,000 discount is deducted upfront. You pay only ₹9,999/- (inclusive of workshop practical lab, study materials, safety gear & ISO 9001:2015 certificate)."},
                            {"q": "Is the hardware toolkit included or extra pricing?", "a": "All laboratory tools, diagnostic meters, and testing equipment are freely provided for practical hands-on use during workshop sessions inside the campus. Personal toolkits for take-home or garage setup are available optionally at special student subsidized extra pricing."},
                            {"q": "What certificate will I receive after completion?", "a": "You will receive an official ISO 9001:2015 Accredited 'Certified Electric Vehicle Technician & Entrepreneur' Certificate issued by EVolution Training Centre in collaboration with institutional partners, recognized by EV manufacturers, dealerships, and fleet operators across India."},
                            {"q": "Does EVolution Training Centre provide job placement or business setup assistance?", "a": "Yes, 100%! We provide direct placement assistance with leading EV dealerships, service networks, and fleet operators. If you wish to start your own EV workshop or spares retail store, we provide wholesale access to 288+ genuine EV spare parts and complete workshop layout guidance."}
                        ]
                    },
                    "te": {
                        "title": "తరచుగా అడిగే ప్రశ్నలు & సమాధానాలు (FAQs)",
                        "subtitle": "ఈవీ శిక్షణ, ₹10,000 స్కాలర్‌షిప్ రాయితీ, ప్రభుత్వ పాలిటెక్నిక్ కేంద్రం మరియు ఉద్యోగ అవకాశాల సమగ్ర వివరాలు",
                        "faqs": [
                            {"q": "ఈ 1-వారం ఈవీ ట్రైనింగ్ ప్రోగ్రామ్‌లో ఎవరు చేరవచ్చు (అర్హతలు ఏమిటి)?", "a": "ఐటీఐ (ITI), పాలిటెక్నిక్ డిప్లొమా, బీటెక్ (B.Tech) విద్యార్థులు మరియు గ్రాడ్యుయేట్లు, ఆటో మొబైల్ మెకానిక్‌లు, గ్యారేజ్ యజమానులు మరియు ఈవీ రంగంలో రాణించాలనుకునే ఎవరైనా చేరవచ్చు. ముందస్తు ఎలక్ట్రికల్ అనుభవం లేకపోయినా బేసిక్స్ మరియు బ్యాటరీ, ఛార్జర్ల ప్రాథమికాంశాల నుండి ప్రాక్టికల్స్‌తో సులభంగా నేర్పించబడుతుంది."},
                            {"q": "శిక్షణ ఎక్కడ నిర్వహించబడుతుంది?", "a": "ఈ ప్రాక్టికల్ శిక్షణ ఆంధ్రప్రదేశ్, విశాఖపట్నంలోని ప్రభుత్వ పాలిటెక్నిక్ కళాశాల, పెందుర్తి (Govt. Polytechnic College, Pendurthi, Visakhapatnam - 531173) క్యాంపస్‌లో జరుగుతుంది."},
                            {"q": "₹10,000 స్కాలర్‌షిప్ రాయితీ ఎలా వర్తిస్తుంది? నేను చెల్లించాల్సిన ఫీజు ఎంత?", "a": "కోర్సు సాధారణ ఫీజు ₹19,999/-. అయితే ప్రభుత్వ పాలిటెక్నిక్ కళాశాల పెందుర్తి స్పెషల్ బ్యాచ్ కింద ₹10,000 నేరుగా స్కాలర్‌షిప్ రూపంలో తగ్గించబడుతుంది. మీరు చెల్లించాల్సిన నికర ఫీజు కేవలం ₹9,999/- మాత్రమే (వర్క్‌షాప్ ప్రాక్టికల్స్, స్టడీ మెటీరియల్స్ మరియు ISO సర్టిఫికెట్‌తో సహా)."},
                            {"q": "టూల్‌కిట్ ఉచితమా లేదా అదనపు ఛార్జీ ఉంటుందా?", "a": "క్యాంపస్ వర్క్‌షాప్ సమయంలో అవసరమైన అన్ని రకాల ల్యాబ్ టూల్స్, మీటర్లు మరియు పరికరాలు ఉచితంగా ప్రాక్టీస్ చేయడానికి ఇవ్వబడతాయి. సొంతంగా లేదా ఇంటికి తీసుకెళ్లడానికి వ్యక్తిగత టూల్‌కిట్ కావాలనుకుంటే విద్యార్థులకు ప్రత్యేక సబ్సిడీ ధరతో (Extra Pricing) అందుబాటులో ఉంటుంది."},
                            {"q": "కోర్సు పూర్తయిన తర్వాత ఎలాంటి సర్టిఫికేట్ లభిస్తుంది?", "a": "కోర్సు మరియు ప్రాక్టికల్ అసెస్‌మెంట్ విజయవంతంగా పూర్తి చేసిన తర్వాత మీకు దేశవ్యాప్తంగా గుర్తింపు పొందిన ISO 9001:2015 అక్రిడిటెడ్ 'సర్టిఫైడ్ ఈవీ టెక్నీషియన్ & ఎంట్రప్రెన్యూర్‌షిప్ సర్టిఫికేట్' అందించబడుతుంది."},
                            {"q": "శిక్షణ తర్వాత ఉద్యోగ అవకాశాలు లేదా సొంత వర్క్‌షాప్ ప్రారంభించడానికి సహాయం లభిస్తుందా?", "a": "ఖచ్చితంగా! ప్రముఖ ఈవీ కంపెనీలు, డీలర్‌షిప్‌లు మరియు సర్వీస్ సెంటర్లలో 100% ప్లేస్‌మెంట్ అసిస్టెన్స్ అందించబడుతుంది. సొంత వర్క్‌షాప్ లేదా విడిభాగాల షాప్ పెట్టాలనుకునే వారికి 288+ ఒరిజినల్ ఈవీ స్పేర్స్ హోల్‌సేల్ సప్లై మరియు పూర్తి బిజినెస్ గైడెన్స్ అందించబడుతుంది."}
                        ]
                    },
                    "hi": {
                        "title": "अक्सर पूछे जाने वाले सवाल (FAQs)",
                        "subtitle": "ईवी ट्रेनिंग, ₹10,000 स्कॉलरशिप छूट, शासकीय पॉलिटेक्निक पेंदुर्ति और प्लेसमेंट की पूरी जानकारी",
                        "faqs": [
                            {"q": "इस 1-सप्ताह के ईवी ट्रेनिंग प्रोग्राम में कौन शामिल हो सकता है?", "a": "आईटीआई, डिप्लोमा, बीटेक छात्र, ऑटो मैकेनिक, वर्कशॉप मालिक और ईवी क्षेत्र में करियर बनाने के इच्छुक सभी लोग पात्र हैं।"},
                            {"q": "ट्रेनिंग कहाँ आयोजित की जाएगी?", "a": "ट्रेनिंग शासकीय पॉलिटेक्निक कॉलेज, पेंदुर्ति, विशाखापट्टनम - 531173 में अत्याधुनिक लैब्स और वर्कशॉप में आयोजित की जाएगी।"},
                            {"q": "₹10,000 स्कॉलरशिप छूट कैसे प्राप्त होगी?", "a": "कोर्स की मानक फीस ₹19,999/- है। विशेष छात्रवृत्ति के तहत ₹10,000 की छूट के बाद आपको केवल ₹9,999/- का भुगतान करना होगा।"},
                            {"q": "क्या टूलकिट शामिल है या अतिरिक्त मूल्य है?", "a": "वर्कशॉप के दौरान प्रैक्टिकल हेतु सभी उपकरण कैंपस में उपलब्ध कराए जाते हैं। व्यक्तिगत टूलकिट रियायती छात्र मूल्य (Extra Pricing) पर वैकल्पिक रूप से उपलब्ध है।"},
                            {"q": "कोर्स समाप्ति पर कौन सा प्रमाण-पत्र मिलेगा?", "a": "सफलतापूर्वक प्रशिक्षण पूर्ण करने पर ISO 9001:2015 मान्यता प्राप्त ईवी तकनीशियन प्रमाण-पत्र प्रदान किया जाएगा।"},
                            {"q": "क्या नौकरी या स्वयं का वर्कशॉप खोलने में सहायता दी जाएगी?", "a": "हाँ, 100% प्लेसमेंट सहायता और स्वयं का ईवी सर्विस सेंटर शुरू करने के लिए 288+ स्पेयर पार्ट्स की डायरेक्ट होलसेल सप्लाई दी जाएगी।"}
                        ]
                    },
                    "ta": {
                        "title": "அடிக்கடி கேட்கப்படும் கேள்விகள் (FAQs)",
                        "subtitle": "மின்சார வாகன பயிற்சி, ரூ.10,000 உதவித்தொகை மற்றும் வேலைவாய்ப்பு விபரம்",
                        "faqs": [
                            {"q": "இந்த 1-வார பயிற்சியில் யார் சேரலாம்?", "a": "ஐடிஐ, பாலிடெக்னிக் டிப்ளமோ, பி.டெக் மாணவர்கள், மெக்கானிக்குகள் மற்றும் மின்சார வாகன தொழில் ஆர்வலர்கள் அனைவரும் சேரலாம்."},
                            {"q": "பயிற்சி எங்கு நடைபெறும்?", "a": "அரசு பாலிடெக்னிக் கல்லூரி, பெந்துர்த்தி, விசாகப்பட்டினம் - 531173 வளாகத்தில் நடைபெறும்."},
                            {"q": "ரூ.10,000 உதவித்தொகை தள்ளுபடி எவ்வாறு பெறலாம்?", "a": "பொது கட்டணம் ரூ.19,999/-. உதவித்தொகை போக நீங்கள் செலுத்த வேண்டிய இறுதி கட்டணம் ரூ.9,999/- மட்டுமே."},
                            {"q": "டூல்கிட் இலவசமா அல்லது கூடுதல் கட்டணமா?", "a": "பயிற்சியின் போது செய்முறை உபகரணங்கள் அனைத்தும் வளாகத்தில் வழங்கப்படும். சொந்த டூல்கிட் தேவைப்பட்டால் சிறப்பு மாணவர் சலுகை விலையில் (Extra Pricing) பெற்றுக்கொள்ளலாம்."},
                            {"q": "பயிற்சிக்கு பின் என்ன சான்றிதழ் வழங்கப்படும்?", "a": "அகில இந்திய அளவில் செல்லுபடியாகும் ISO 9001:2015 தரச்சான்றிதழ் வழங்கப்படும்."},
                            {"q": "வேலைவாய்ப்பு உதவி வழங்கப்படுமா?", "a": "ஆம், 100% வேலைவாய்ப்பு உதவி மற்றும் சுயதொழில் தொடங்குவதற்கான உதிரிபாகங்கள் சப்ளை உதவி வழங்கப்படும்."}
                        ]
                    }
                },
                "configuration": {
                    "faqs": [
                        {"q": "Who is eligible to join this 1-Week EV training program?", "a": "ITI, Polytechnic Diploma, B.Tech students and graduates, auto mechanics, garage owners, two-wheeler technicians, and EV career enthusiasts are all eligible. No prior advanced electrical background is mandatory — the program starts with fundamental safety and builds up to practical vehicle diagnostics and training on basics of battery and chargers."},
                        {"q": "Where is the training conducted?", "a": "The training is conducted at Govt. Polytechnic College, Pendurthi, Visakhapatnam, Andhra Pradesh - 531173. The campus features high-voltage practical labs, vehicle teardown bays, and state-of-the-art testing equipment."},
                        {"q": "How does the ₹10,000 scholarship discount work?", "a": "The standard course fee is ₹19,999/-. Under our Special Green Skill Scholarship Scheme at Govt. Polytechnic College Pendurthi, a direct ₹10,000 discount is deducted upfront. You pay only ₹9,999/- (inclusive of workshop practical lab, study materials, safety gear & ISO 9001:2015 certificate)."},
                        {"q": "Is the hardware toolkit included or extra pricing?", "a": "All laboratory tools, diagnostic meters, and testing equipment are freely provided for practical hands-on use during workshop sessions inside the campus. Personal toolkits for take-home or garage setup are available optionally at special student subsidized extra pricing."},
                        {"q": "What certificate will I receive after completion?", "a": "You will receive an official ISO 9001:2015 Accredited 'Certified Electric Vehicle Technician & Entrepreneur' Certificate issued by EVolution Training Centre in collaboration with institutional partners, recognized by EV manufacturers, dealerships, and fleet operators across India."},
                        {"q": "Does EVolution Training Centre provide job placement or business setup assistance?", "a": "Yes, 100%! We provide direct placement assistance with leading EV dealerships, service networks, and fleet operators. If you wish to start your own EV workshop or spares retail store, we provide wholesale access to 288+ genuine EV spare parts and complete workshop layout guidance."}
                    ]
                }
            },
            {
                "section_type": "contact_cta",
                "section_key": "cta",
                "title": "Enroll in the Upcoming EV Training Batch (ఇప్పుడే అడ్మిషన్ పొందండి)",
                "subtitle": "Limited to 25 candidates per batch for individual practical workstation access. Reserve your seat for just ₹9,999!",
                "content_variants": {
                    "en": {
                        "title": "Enroll in the Upcoming EV Training Batch",
                        "subtitle": "Limited to 25 candidates per batch for individual practical workstation access. Reserve your seat for just ₹9,999!"
                    },
                    "te": {
                        "title": "రాబోయే ఈవీ ట్రైనింగ్ బ్యాచ్‌లో ఇప్పుడే అడ్మిషన్ పొందండి",
                        "subtitle": "ప్రతి అభ్యర్థికి వ్యక్తిగత ప్రాక్టికల్ వర్క్‌స్టేషన్ అందించడానికి బ్యాచ్‌కు కేవలం 25 సీట్లు మాత్రమే. ₹9,999 తో మీ సీటును రిజర్వ్ చేసుకోండి!"
                    },
                    "hi": {
                        "title": "आगामी ईवी ट्रेनिंग बैच में अभी प्रवेश लें",
                        "subtitle": "व्यक्तिगत प्रैक्टिकल वर्कस्टेशन के लिए प्रति बैच केवल 25 सीटें उपलब्ध। मात्र ₹9,999 में अपनी सीट सुरक्षित करें!"
                    },
                    "ta": {
                        "title": "அடுத்த பயிற்சி வகுப்பில் இப்போதே பதிவு செய்க",
                        "subtitle": "ஒரு வகுப்பிற்கு 25 இடங்கள் மட்டுமே. வெறும் ரூ.9,999-ல் உங்கள் இடத்தை உறுதி செய்யுங்கள்!"
                    }
                },
                "configuration": {
                    "whatsapp_number": "918585852738",
                    "helpline": "+91 858585 2738",
                    "office_address": "Govt. Polytechnic College, Pendurthi, Visakhapatnam, Andhra Pradesh - 531173",
                    "working_hours": "Mon - Sat: 9:00 AM - 6:00 PM",
                    "prefill_message": "Hello! I want to enroll in the 1-Week EV Technician & Entrepreneurship Certification (₹9,999) at Govt. Polytechnic College, Pendurthi."
                }
            }
        ],
        "items": [
            {
                "item_type": "COURSE",
                "item_code": "ETC-EV-1WK",
                "title": "1-Week EV Technician & Entrepreneurship Certification Training",
                "subtitle": "Intensive hands-on EV 2-wheeler diagnostics, training on basics of battery and chargers, BLDC motors & workshop setup at Govt. Polytechnic College, Pendurthi",
                "specifications": [
                    {"label": "Duration", "value": "1 Week (7 Days, 36 Hours Hands-on)"},
                    {"label": "Training Venue", "value": "Govt. Polytechnic College, Pendurthi, Visakhapatnam"},
                    {"label": "Standard Course Fee", "value": "₹19,999/-"},
                    {"label": "Special Scholarship", "value": "₹10,000/- (Instant Deduction)"},
                    {"label": "Final Net Payable", "value": "₹9,999/- (Inclusive of Lab & Certificate)"},
                    {"label": "Practical Lab Ratio", "value": "70% Hands-on Workshop Practice"},
                    {"label": "Battery & Chargers", "value": "Training on basics of battery and chargers"},
                    {"label": "Hardware Toolkit", "value": "Professional EV Toolkit (Optional / Extra Pricing)"},
                    {"label": "Certification", "value": "ISO 9001:2015 Accredited EV Technician Certificate"},
                    {"label": "Career Support", "value": "100% Placement & Dealership Spares Support"}
                ],
                "pricing": {"base_price": 19999, "discount": 10000, "net_cost": 9999, "currency": "INR"},
                "media_urls": ["/public/images/etc_training/ev_practical_scooter_lab.jpg"],
                "badges": ["Most Popular", "₹10,000 Scholarship", "Govt. Polytechnic Pendurthi"]
            },
            {
                "item_type": "COURSE",
                "item_code": "ETC-FRANCHISE-2W",
                "title": "2-Week EV Workshop & Spares Dealership Setup",
                "subtitle": "Master multi-brand EV diagnostics, training on basics of battery and chargers, workshop machinery setup, and wholesale access to 288+ genuine EV spares",
                "specifications": [
                    {"label": "Duration", "value": "2 Weeks (14 Days, 72 Hours Comprehensive)"},
                    {"label": "Training Venue", "value": "Govt. Polytechnic College, Pendurthi, Visakhapatnam"},
                    {"label": "Standard Course Fee", "value": "₹29,999/-"},
                    {"label": "Special Scholarship", "value": "₹10,000/- Entrepreneur Aid"},
                    {"label": "Final Net Payable", "value": "₹19,999/-"},
                    {"label": "Battery & Chargers", "value": "Training on basics of battery and chargers"},
                    {"label": "Hardware Toolkit", "value": "Professional EV Toolkit (Optional / Extra Pricing)"},
                    {"label": "Franchise Support", "value": "Direct B2B Dealership & Spares Supply"}
                ],
                "pricing": {"base_price": 29999, "discount": 10000, "net_cost": 19999, "currency": "INR"},
                "media_urls": ["/public/images/etc_training/etc_certified_students_group_1.png"],
                "badges": ["Entrepreneurship", "Franchise Setup"]
            }
        ]
    },
    {
        "segment_code": "REAL_DREAMS",
        "slug": "real-dreams-premium-properties",
        "title": "Premium Real Estate & Integrated Townships",
        "subtitle": "RERA-Approved Luxury Villas, Gated Community Plots & Commercial Retail Spaces",
        "summary": "Invest in future-ready gated communities with sustainable solar infrastructure, EV charging provisions, wide blacktop roads, underground utilities, and guaranteed high land appreciation.",
        "hero_media_url": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1600&q=80",
        "theme_config": {"primary_color": "#047857", "accent_color": "#b45309", "dark_mode": False},
        "default_language": "en",
        "active_languages": ["en", "te", "hi", "ta"],
        "sections": [
            {
                "section_type": "hero",
                "section_key": "hero",
                "title": "Build Your Dream Home in Prime Fast-Appreciating Townships",
                "subtitle": "100% Clear Title, RERA & DTCP Approved Plots and Villas with Solar-Powered Infrastructure",
                "content_variants": {
                    "en": {"title": "Build Your Dream Home in Prime Fast-Appreciating Townships", "subtitle": "100% Clear Title, RERA & DTCP Approved Plots and Villas with Solar-Powered Infrastructure"},
                    "te": {"title": "వేగంగా విలువ పెరిగే ప్రైమ్ టౌన్‌షిప్‌లలో మీ కలల ఇల్లు నిర్మించుకోండి", "subtitle": "100% క్లియర్ టైటిల్, RERA & DTCP ఆమోదిత ప్లాట్లు మరియు సోలార్ విల్లాలు"},
                    "hi": {"title": "प्राइम लोकेशनों पर अपने सपनों का आशियाना बनाएं", "subtitle": "100% कानूनी मंजूरी, RERA और DTCP अप्रूव्ड प्लॉट्स और सोलर विला"},
                    "ta": {"title": "பிரதான இடங்களில் உங்கள் கனவு இல்லத்தை உருவாக்குங்கள்", "subtitle": "100% சட்டபூர்வ அங்கீகாரம் பெற்ற நிலங்கள் மற்றும் நவீன வீடுகள்"}
                },
                "configuration": {
                    "badge": "🏡 100% Clear Title & Bank Approved",
                    "stats": [
                        {"label": "Project Size", "value": "50+ Acres"},
                        {"label": "Amenities", "value": "40+ World Class"},
                        {"label": "Approvals", "value": "RERA & DTCP"},
                        {"label": "Bank Loans", "value": "Up to 80% Available"}
                    ]
                }
            },
            {
                "section_type": "media_gallery",
                "section_key": "installation_gallery",
                "title": "Real Dreams Township & Luxury Villas Showcase (రియల్ డ్రీమ్స్ టౌన్‌షిప్ గ్యాలరీ)",
                "subtitle": "RERA-approved premium gated community layouts, solar luxury villas & scenic amenities",
                "content_variants": {
                    "en": {
                        "title": "Real Dreams Township & Luxury Villas Showcase",
                        "subtitle": "Tour our RERA-approved luxury villas, underground solar infrastructure, green parks, and wide avenues."
                    },
                    "te": {
                        "title": "రియల్ డ్రీమ్స్ టౌన్‌షిప్ మరియు లగ్జరీ విల్లాస్ గ్యాలరీ",
                        "subtitle": "RERA ఆమోదిత విల్లా ప్లాట్లు, సోలార్ వీధి దీపాలు మరియు ఆహ్లాదకరమైన క్లబ్‌హౌస్."
                    }
                },
                "media_gallery": [
                    {
                        "url": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Grand Entrance Arch & Security Command Post — Green Valley Township",
                        "tag": "Entrance Arch"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1613490493576-7fde63acd811?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Signature 4BHK Eco-Luxury Triplex Villa with 5kW Solar Rooftop",
                        "tag": "Luxury Villa"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Contemporary Architectural Elevation & Landscaped Front Porch",
                        "tag": "Villa Architecture"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=1200&q=80",
                        "caption": "60-Feet Wide Blacktop Avenue Roads with Tree-Lined Walkways",
                        "tag": "Avenue Roads"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Resort-Style Clubhouse with Infinity Swimming Pool & Sun Deck",
                        "tag": "Clubhouse & Pool"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1576013551627-0cc20b96c2a7?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Children's Play Arena & Senior Citizen Green Meditation Garden",
                        "tag": "Landscaped Park"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1509391365360-2e959784a276?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Central 100kW Community Solar Grid Powering All Streetlights & Pumps",
                        "tag": "Green Infrastructure"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1600565193348-f74bd3c7ccdf?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Plotted Layout Demarcation with Clear Corner Boundary Stones",
                        "tag": "Demarcated Plots"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Designer Modular Kitchen & Spacious Living Lounge Inside Villa",
                        "tag": "Interior Design"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=1200&q=80",
                        "caption": "On-Site Plot Registration & Immediate Legal Document Handover to Buyer",
                        "tag": "Registration Ready"
                    }
                ],
                "configuration": {
                    "auto_play_interval_ms": 3000,
                    "enable_lightbox": True,
                    "videos": [
                        {
                            "title": "Green Valley Integrated Solar Township & Luxury Villas Drone Walkthrough",
                            "youtube_id": "kYJmQ6X2q38",
                            "url": "https://www.youtube.com/watch?v=kYJmQ6X2q38",
                            "embed_url": "https://www.youtube-nocookie.com/embed/kYJmQ6X2q38"
                        },
                        {
                            "title": "Eco-Friendly Triplex Villa Tour: 5kW Rooftop Solar & EV Charging",
                            "youtube_id": "0k7yF_G0lQ8",
                            "url": "https://www.youtube.com/watch?v=0k7yF_G0lQ8",
                            "embed_url": "https://www.youtube-nocookie.com/embed/0k7yF_G0lQ8"
                        }
                    ]
                }
            }
        ],
        "items": [
            {
                "item_type": "PROPERTY",
                "item_code": "RD-VILLA-PLOT",
                "title": "Gated Community Luxury Villa Plots",
                "subtitle": "200 to 400 Sq. Yards clear-title plots with clubhouse, solar streetlights and avenue plantation",
                "specifications": [
                    {"label": "Plot Size", "value": "200, 267 & 400 Sq. Yards"},
                    {"label": "Approvals", "value": "RERA Registered & DTCP Approved"},
                    {"label": "Road Width", "value": "40 & 60 Feet BT Roads"},
                    {"label": "Possession", "value": "Immediate Registration Ready"}
                ],
                "pricing": {"base_price": 2800000, "price_text": "From ₹14,000 / Sq. Yd", "currency": "INR"},
                "media_urls": ["https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=800&q=80"],
                "badges": ["RERA Approved", "Immediate Registration"]
            },
            {
                "item_type": "PROPERTY",
                "item_code": "RD-GREEN-VILLA",
                "title": "Signature 4BHK Eco-Luxury Villa",
                "subtitle": "Contemporary triplex villa with pre-installed 5kW solar rooftop and EV charging point",
                "specifications": [
                    {"label": "Built-up Area", "value": "3,200 Sq. Ft. Triplex"},
                    {"label": "Plot Size", "value": "240 Sq. Yards"},
                    {"label": "Green Features", "value": "5kW Rooftop Solar + Rainwater Harvesting"},
                    {"label": "Community", "value": "Grand Clubhouse, Swimming Pool, Gym"}
                ],
                "pricing": {"base_price": 11500000, "price_text": "₹1.15 Cr All-Inclusive", "currency": "INR"},
                "media_urls": ["https://images.unsplash.com/photo-1613490493576-7fde63acd811?auto=format&fit=crop&w=800&q=80"],
                "badges": ["Solar Included", "Triplex Villa"]
            }
        ]
    },
    {
        "segment_code": "INSURANCE",
        "slug": "comprehensive-insurance-advisory",
        "title": "General, Commercial & Life Insurance Advisory",
        "subtitle": "Tailored Risk Protection for Electric Vehicles, Solar Installations, Businesses & Families",
        "summary": "Complete 360-degree security. Specialist insurance coverage for commercial EV fleets, solar plant all-risk damage, business property, and comprehensive health & term life plans with swift claims support.",
        "hero_media_url": "https://images.unsplash.com/photo-1450133064473-71024230f91b?auto=format&fit=crop&w=1600&q=80",
        "theme_config": {"primary_color": "#0f766e", "accent_color": "#6366f1", "dark_mode": False},
        "default_language": "en",
        "active_languages": ["en", "te", "hi", "ta"],
        "sections": [
            {
                "section_type": "hero",
                "section_key": "hero",
                "title": "Comprehensive Asset & Business Protection",
                "subtitle": "Specialized EV Battery Covers, Solar EPC All-Risk Insurance, and Commercial Liability",
                "content_variants": {
                    "en": {"title": "Comprehensive Asset & Business Protection", "subtitle": "Specialized EV Battery Covers, Solar EPC All-Risk Insurance, and Commercial Liability"},
                    "te": {"title": "మీ వ్యాపారం మరియు ఆస్తులకు సమగ్ర భద్రత", "subtitle": "ఈవీ బ్యాటరీ ప్రొటెక్షన్, సోలార్ ప్లాంట్ ఇన్సూరెన్స్ మరియు కమర్షియల్ పాలసీలు"},
                    "hi": {"title": "आपके व्यापार और संपत्तियों के लिए संपूर्ण सुरक्षा", "subtitle": "ईवी बैटरी कवर, सोलर प्लांट इन्श्योरेंस और व्यापारिक पॉलिसियां"},
                    "ta": {"title": "உங்கள் வணிகத்திற்கான முழுமையான காப்பீடு", "subtitle": "மின்சார வாகனம், சோலார் மற்றும் வணிகத்திற்கான சிறந்த திட்டங்கள்"}
                },
                "configuration": {
                    "badge": "🛡️ 98.6% Claim Settlement Ratio",
                    "stats": [
                        {"label": "Cashless Garages", "value": "4,500+"},
                        {"label": "Avg Claim Approval", "value": "4 Hours"},
                        {"label": "Asset Coverage", "value": "100% Value"},
                        {"label": "Partner Insurers", "value": "Top 12 IRDAI Firms"}
                    ]
                }
            },
            {
                "section_type": "media_gallery",
                "section_key": "installation_gallery",
                "title": "Comprehensive Insurance Advisory Showcase (ఇన్సూరెన్స్ సేవల గ్యాలరీ)",
                "subtitle": "Specialized protection for electric vehicles, rooftop solar, businesses and families",
                "content_variants": {
                    "en": {
                        "title": "Comprehensive Insurance Advisory Showcase",
                        "subtitle": "Explore specialized EV battery policies, solar EPC risk protection, corporate coverage, and claims assistance."
                    },
                    "te": {
                        "title": "సమగ్ర బీమా సేవల గ్యాలరీ & సమాచారం",
                        "subtitle": "ఈవీ బ్యాటరీ ఇన్సూరెన్స్, సోలార్ ప్లాంట్ రక్షణ మరియు సులభ క్లెయిమ్ ప్రక్రియ."
                    }
                },
                "media_gallery": [
                    {
                        "url": "https://images.unsplash.com/photo-1450133064473-71024230f91b?auto=format&fit=crop&w=1200&q=80",
                        "caption": "One-on-One Insurance Portfolio Review & Policy Advisory Consultation",
                        "tag": "Financial Advisory"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1558981806-ec527fa84c39?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Dedicated EV Comprehensive Cover with Zero-Depreciation Battery Protection",
                        "tag": "EV Policy"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1509391365360-2e959784a276?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Commercial Solar EPC All-Risk Insurance Policy Against Cyclone & Hail Damage",
                        "tag": "Solar Insurance"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1578575437130-527eed3abbec?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Cashless Garage Network Inspection & Fast Spot Survey Approval",
                        "tag": "Cashless Network"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1554224155-8d04cb21cd6c?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Corporate Commercial Liability & Factory Fire Safety Insurance Audit",
                        "tag": "Commercial Policy"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Family Comprehensive Health Insurance with Cashless Hospital Admission",
                        "tag": "Health Insurance"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1508974239320-0a029497e820?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Instant Paperless Digital Policy Issuance with Direct WhatsApp Delivery",
                        "tag": "Digital Issuance"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1521791136064-7986c2920216?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Express Claim Settlement Handover: 4-Hour Turnaround Time Guarantee",
                        "tag": "Express Claims"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1563986768609-322da13575f3?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Commercial Fleet Telematics-Linked Usage-Based Insurance (UBI) Dashboard",
                        "tag": "Fleet Telematics"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1600880292203-757bb62b4baf?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Customer Appreciation: 98.6% Claim Settlement Ratio Milestone Celebration",
                        "tag": "Trust & Milestones"
                    }
                ],
                "configuration": {
                    "auto_play_interval_ms": 3000,
                    "enable_lightbox": True,
                    "videos": [
                        {
                            "title": "Complete Guide to Electric Vehicle & Battery Insurance in India",
                            "youtube_id": "kYJmQ6X2q38",
                            "url": "https://www.youtube.com/watch?v=kYJmQ6X2q38",
                            "embed_url": "https://www.youtube-nocookie.com/embed/kYJmQ6X2q38"
                        },
                        {
                            "title": "Solar Plant All-Risk Insurance & Fast Cashless Claim Process",
                            "youtube_id": "0k7yF_G0lQ8",
                            "url": "https://www.youtube.com/watch?v=0k7yF_G0lQ8",
                            "embed_url": "https://www.youtube-nocookie.com/embed/0k7yF_G0lQ8"
                        }
                    ]
                }
            }
        ],
        "items": [
            {
                "item_type": "SERVICE",
                "item_code": "INS-EV-COMP",
                "title": "Electric Vehicle Comprehensive Package Policy",
                "subtitle": "Zero-depreciation motor insurance with explicit battery replacement and roadside charging assistance",
                "specifications": [
                    {"label": "Coverage", "value": "Bumper-to-Bumper Zero Depreciation"},
                    {"label": "Battery Cover", "value": "Dedicated Water Ingress & Electrical Surge Add-on"},
                    {"label": "Emergency", "value": "24/7 Mobile Towing & Spot Charging"},
                    {"label": "Cashless Network", "value": "4,500+ Authorized EV Garages"}
                ],
                "pricing": {"base_price": 2899, "price_text": "Starting at ₹2,899 / Year", "currency": "INR"},
                "media_urls": ["https://images.unsplash.com/photo-1450133064473-71024230f91b?auto=format&fit=crop&w=800&q=80"],
                "badges": ["Battery Protection", "Zero Depreciation"]
            },
            {
                "item_type": "SERVICE",
                "item_code": "INS-SOLAR-EPC",
                "title": "Solar Rooftop & Ground Plant All-Risk Insurance",
                "subtitle": "Complete natural calamity, cyclone, fire, theft and electrical breakdown protection for solar installations",
                "specifications": [
                    {"label": "Calamity Cover", "value": "Cyclone, Flood, Hailstorm & Lightning"},
                    {"label": "Performance", "value": "Business Interruption Revenue Loss Cover"},
                    {"label": "Third Party", "value": "Public Liability up to ₹1 Crore"},
                    {"label": "Inspection", "value": "Instant Digital Drone Survey"}
                ],
                "pricing": {"base_price": 4999, "price_text": "Custom Quote Based on kW Capacity", "currency": "INR"},
                "media_urls": ["https://images.unsplash.com/photo-1509391365360-2e959784a276?auto=format&fit=crop&w=800&q=80"],
                "badges": ["Cyclone & Fire Shield", "Loss of Generation"]
            }
        ]
    }
]


def seed_default_catalogs(db_session=None):
    """
    Seeds default digital catalogs for all 8 verticals if not already present.
    Safe and idempotent — preserves existing customizations.
    """
    close_db = False
    if db_session is None:
        db = SessionLocal()
        close_db = True
    else:
        db = db_session

    try:
        # Default company ID is 4 (MyntReal LLP) or fallback to first company
        default_company = db.query(AssociatedCompany).filter(AssociatedCompany.id == 4).first()
        if not default_company:
            default_company = db.query(AssociatedCompany).first()

        company_id = default_company.id if default_company else 4
        logger.info(f"Seeding digital catalogs for company_id={company_id}")

        created_count = 0
        updated_count = 0

        for cat_data in SEED_CATALOGS_DATA:
            segment_code = cat_data["segment_code"]
            slug = cat_data["slug"]

            # Match SignupCategory if exists
            cat_record = db.query(SignupCategory).filter(
                (SignupCategory.slug.ilike(f"%{segment_code.lower().replace('_', '-')}%")) |
                (SignupCategory.name.ilike(f"%{segment_code.replace('_', ' ')}%"))
            ).first()
            category_id = cat_record.id if cat_record else None

            existing = db.query(DigitalCatalog).filter(
                DigitalCatalog.company_id == company_id,
                DigitalCatalog.slug == slug
            ).first()

            if not existing:
                catalog = DigitalCatalog(
                    company_id=company_id,
                    tenant_id=None,
                    category_id=category_id,
                    segment_code=segment_code,
                    slug=slug,
                    title=cat_data["title"],
                    subtitle=cat_data["subtitle"],
                    summary=cat_data["summary"],
                    hero_media_url=cat_data["hero_media_url"],
                    catalog_type="SINGLE_PAGE",
                    status="published",
                    is_active=True,
                    is_featured=True,
                    sort_order=created_count,
                    seo_title=f"{cat_data['title']} | Official Digital Catalog",
                    seo_description=cat_data["summary"],
                    theme_config=cat_data["theme_config"],
                    default_language=cat_data["default_language"],
                    active_languages=cat_data["active_languages"],
                    published_at=get_indian_time(),
                    created_at=get_indian_time(),
                    updated_at=get_indian_time()
                )
                db.add(catalog)
                db.flush()

                # Add Sections
                for s_idx, sec_data in enumerate(cat_data.get("sections", [])):
                    section = CatalogSection(
                        catalog_id=catalog.id,
                        section_type=sec_data["section_type"],
                        section_key=sec_data["section_key"],
                        title=sec_data["title"],
                        subtitle=sec_data.get("subtitle"),
                        content_variants=sec_data.get("content_variants", {}),
                        media_gallery=sec_data.get("media_gallery", []),
                        configuration=sec_data.get("configuration", {}),
                        sort_order=s_idx,
                        is_visible=True,
                        is_active=True,
                        created_at=get_indian_time(),
                        updated_at=get_indian_time()
                    )
                    db.add(section)

                # Add Items
                for i_idx, it_data in enumerate(cat_data.get("items", [])):
                    item = CatalogItem(
                        catalog_id=catalog.id,
                        item_type=it_data.get("item_type", "PRODUCT"),
                        item_code=it_data.get("item_code"),
                        title=it_data["title"],
                        subtitle=it_data.get("subtitle"),
                        specifications=it_data.get("specifications", []),
                        pricing=it_data.get("pricing", {}),
                        media_urls=it_data.get("media_urls", []),
                        badges=it_data.get("badges", []),
                        sort_order=i_idx,
                        is_featured=True,
                        is_active=True,
                        created_at=get_indian_time(),
                        updated_at=get_indian_time()
                    )
                    db.add(item)

                created_count += 1
                logger.info(f"✅ Created default catalog: {cat_data['title']} (slug: {slug})")
            else:
                updated_count += 1
                catalog = existing
                logger.info(f"ℹ️ Catalog already exists: {cat_data['title']} (slug: {slug}), synchronizing sections...")
                catalog.title = cat_data["title"]
                catalog.subtitle = cat_data.get("subtitle")
                catalog.summary = cat_data.get("summary")
                catalog.hero_media_url = cat_data.get("hero_media_url")
                catalog.theme_config = cat_data.get("theme_config", {})
                catalog.active_languages = cat_data.get("active_languages", ["en", "te", "hi", "ta"])

                # Synchronize sections by section_key
                existing_sections = {s.section_key: s for s in catalog.sections}
                new_section_keys = {sec_data["section_key"] for sec_data in cat_data.get("sections", [])}
                for s_key, s_obj in existing_sections.items():
                    if s_key not in new_section_keys:
                        db.delete(s_obj)

                for s_idx, sec_data in enumerate(cat_data.get("sections", [])):
                    s_key = sec_data["section_key"]
                    if s_key in existing_sections:
                        sec = existing_sections[s_key]
                        sec.section_type = sec_data["section_type"]
                        sec.title = sec_data["title"]
                        sec.subtitle = sec_data.get("subtitle")
                        sec.content_variants = sec_data.get("content_variants", {})
                        sec.media_gallery = sec_data.get("media_gallery", [])
                        sec.configuration = sec_data.get("configuration", {})
                        sec.sort_order = s_idx
                        sec.is_visible = True
                        sec.is_active = True
                        sec.updated_at = get_indian_time()
                    else:
                        new_sec = CatalogSection(
                            catalog_id=catalog.id,
                            section_type=sec_data["section_type"],
                            section_key=s_key,
                            title=sec_data["title"],
                            subtitle=sec_data.get("subtitle"),
                            content_variants=sec_data.get("content_variants", {}),
                            media_gallery=sec_data.get("media_gallery", []),
                            configuration=sec_data.get("configuration", {}),
                            sort_order=s_idx,
                            is_visible=True,
                            is_active=True,
                            created_at=get_indian_time(),
                            updated_at=get_indian_time()
                        )
                        db.add(new_sec)

                # Synchronize items by item_code
                existing_items = {it.item_code: it for it in catalog.items}
                new_item_codes = {it_data.get("item_code") for it_data in cat_data.get("items", []) if it_data.get("item_code")}
                for it_code, it_obj in existing_items.items():
                    if it_code not in new_item_codes:
                        db.delete(it_obj)

                for it_idx, it_data in enumerate(cat_data.get("items", [])):
                    it_code = it_data.get("item_code")
                    if it_code and it_code in existing_items:
                        item = existing_items[it_code]
                        item.title = it_data["title"]
                        item.subtitle = it_data.get("subtitle")
                        item.specifications = it_data.get("specifications", [])
                        item.pricing = it_data.get("pricing", {})
                        item.media_urls = it_data.get("media_urls", [])
                        item.badges = it_data.get("badges", [])
                        item.sort_order = it_idx
                        item.is_active = True
                        item.updated_at = get_indian_time()
                    else:
                        new_item = CatalogItem(
                            catalog_id=catalog.id,
                            item_type=it_data.get("item_type", "COURSE"),
                            item_code=it_code,
                            title=it_data["title"],
                            subtitle=it_data.get("subtitle"),
                            specifications=it_data.get("specifications", []),
                            pricing=it_data.get("pricing", {}),
                            media_urls=it_data.get("media_urls", []),
                            badges=it_data.get("badges", []),
                            is_active=True,
                            sort_order=it_idx,
                            created_at=get_indian_time(),
                            updated_at=get_indian_time()
                        )
                        db.add(new_item)

        # Also ensure StaffMenuRegistry has STAFF_CATALOG_LIBRARY
        seed_catalog_menu_registry(db)

        db.commit()
        logger.info(f"Catalog seeding complete. Created: {created_count}, Existing: {updated_count}")

    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding digital catalogs: {e}", exc_info=True)
        raise
    finally:
        if close_db:
            db.close()


def seed_catalog_menu_registry(db=None):
    """Ensure STAFF_CATALOG_LIBRARY is in StaffMenuRegistry so sales staff and leadership see it in sidebar/drawer."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        from app.models.staff import StaffMenuRegistry
        reg = db.query(StaffMenuRegistry).filter(StaffMenuRegistry.menu_code == 'STAFF_CATALOG_LIBRARY').first()
        if not reg:
            reg = StaffMenuRegistry(
                menu_code='STAFF_CATALOG_LIBRARY',
                menu_name='Catalog Library',
                route_path='/staff/catalog-library',
                menu_category='crm',
                menu_icon='fas fa-book-open',
                sidebar_section='crm',
                sidebar_section_title='CRM & LEADS',
                sidebar_section_order=4,
                display_order=288,
                audience_scope='staff',
                source='discovered',
                source_file='backend/scripts/seed_digital_catalogs.py',
                is_default_visible=True,
                is_default_accessible=True,
                is_active=True,
                is_system_default=True,
                created_at=get_indian_time(),
                updated_at=get_indian_time()
            )
            db.add(reg)
            logger.info("Created StaffMenuRegistry entry for STAFF_CATALOG_LIBRARY")
        else:
            reg.menu_name = 'Catalog Library'
            reg.route_path = '/staff/catalog-library'
            reg.sidebar_section = 'crm'
            reg.sidebar_section_title = 'CRM & LEADS'
            reg.sidebar_section_order = 4
            reg.display_order = 288
            reg.is_default_visible = True
            reg.is_default_accessible = True
            reg.is_active = True
            reg.updated_at = get_indian_time()
            logger.info("Updated existing StaffMenuRegistry entry for STAFF_CATALOG_LIBRARY")
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Error seeding catalog menu registry: {e}")
    finally:
        if close_db:
            db.close()


if __name__ == "__main__":
    seed_default_catalogs()

