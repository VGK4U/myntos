"""
Seed Default Digital Catalogs — MyntOS Single-Page Digital Catalog Platform
Initializes official high-converting catalogs for all 8 business verticals:
1. SOLAR
2. INDUSTRIAL_HUB
3. EV_B2B
4. EV_B2C
5. EV_SPARES
6. ETC_TRAINING
7. REAL_DREAMS
8. INSURANCE

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
                        "cta_phone": "919053899899"
                    },
                    "te": {
                        "title": "హర్ ఘర్ సోలార్ — ప్రధానమంత్రి సూర్య ఘర్ ఉచిత విద్యుత్ యోజన",
                        "subtitle": "ప్రతి ఇంటికి సౌర విద్యుత్ — ₹78,000 వరకు నేరుగా బ్యాంక్ ఖాతాలో సబ్సిడీ మరియు 25 సంవత్సరాల వారంటీతో కరెంట్ బిల్లులను 90% వరకు ఆదా చేయండి.",
                        "cta_text": "ఉచిత సైట్ సర్వే & పొదుపు గణన",
                        "cta_phone": "919053899899"
                    },
                    "hi": {
                        "title": "हर घर सोलर — प्रधानमंत्री सूर्य घर मुफ्त बिजली योजना",
                        "subtitle": "अपने घर को बनाएं बिजली का पावर हाउस — ₹78,000 तक सीधी बैंक सब्सिडी और 90% तक बिजली बिल में बचत।",
                        "cta_text": "मुफ्त साइट सर्वे बुक करें",
                        "cta_phone": "919053899899"
                    },
                    "ta": {
                        "title": "ஹர் கர் சோலார் — பிரதம மந்திரி சூர்ய கர் இலவச மின் திட்டம்",
                        "subtitle": "உங்கள் வீட்டிற்கு சூரிய மின்சக்தி — ₹78,000 வரை நேரடி வங்கி மானியம் மற்றும் 90% வரை மின் கட்டண சேமிப்பு.",
                        "cta_text": "இலவச தள ஆய்வு பெறுக",
                        "cta_phone": "919053899899"
                    }
                },
                "configuration": {
                    "badge": "⚡ PM Surya Ghar Approved EPC Partner",
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
                            "tag": "Best Value EPC Tier • 25-Yr Performance Warranty",
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
                            "name": "Punjab National Bank (PNB)",
                            "badge": "PNB Surya",
                            "logo": "/public/images/banks/pnb.svg",
                            "tenure": "Up to 10 Years",
                            "highlights": "Concessional Margin Money • Direct DBT Credit"
                        }
                    ]
                }
            },
            {
                "section_type": "highlights_grid",
                "section_key": "benefits",
                "title": "Why Switch to Solar with MyntReal & VGK4U?",
                "subtitle": "Engineering excellence meets seamless government subsidy execution",
                "content_variants": {
                    "en": {
                        "title": "Why Switch to Solar with MyntReal & VGK4U?",
                        "subtitle": "Engineering excellence meets seamless government subsidy execution"
                    },
                    "te": {
                        "title": "MyntReal & VGK4U సోలార్ ఎందుకు ఎంచుకోవాలి?",
                        "subtitle": "అత్యుత్తమ సాంకేతిక పరిజ్ఞానం మరియు వేగవంతమైన ప్రభుత్వ సబ్సిడీ ప్రాసెసింగ్"
                    },
                    "hi": {
                        "title": "MyntReal & VGK4U सोलर ही क्यों चुनें?",
                        "subtitle": "विश्वस्तरीय तकनीक और तुरंत सरकारी सब्सिडी का लाभ"
                    },
                    "ta": {
                        "title": "MyntReal & VGK4U சோலாரை ஏன் தேர்வு செய்ய வேண்டும்?",
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
                            "subsidy": "₹78,000 DBT or 40% Tax Depreciation",
                            "net_cost": "₹5,42,000 Effective Price",
                            "features": ["10 kW Three-Phase High-Capacity Inverter", "High-Generation Half-Cut Arrays", "Wind-Resistant Aluminium/HDG Mounting", "2-Year Complimentary Maintenance SLA", "🔥 Special: Commercial Green Loan Available"],
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
                    "en": {"title": "Frequently Asked Questions", "subtitle": "Everything you need to know about rooftop solar and subsidies"},
                    "te": {"title": "తరచుగా అడిగే ప్రశ్నలు (FAQ)", "subtitle": "సోలార్ రూఫ్‌టాప్ మరియు సబ్సిడీ గురించి సమగ్ర సమాచారం"},
                    "hi": {"title": "अक्सर पूछे जाने वाले सवाल", "subtitle": "सोलर पैनल और सब्सिडी से जुड़ी पूरी जानकारी"},
                    "ta": {"title": "அடிக்கடி கேட்கப்படும் கேள்விகள்", "subtitle": "சோலார் திட்டங்கள் மற்றும் மானியம் குறித்த விவரங்கள்"}
                },
                "configuration": {
                    "faqs": [
                        {"q": "How does net metering work?", "a": "During daytime, excess solar power generated is sent to the grid. At night, you draw power from the grid. You only pay for the net units consumed, or receive credits for excess power sent!"},
                        {"q": "How is the subsidy deposited into my account?", "a": "Under PM Surya Ghar, the subsidy is credited directly to your bank account via Direct Benefit Transfer (DBT) within 30 days of net meter commissioning."},
                        {"q": "What happens on cloudy or rainy days?", "a": "Solar panels generate power from ambient daylight even during overcast weather, typically yielding 30% to 50% of peak output."},
                        {"q": "What is the warranty on panels and inverters?", "a": "Solar panels carry a 25-year linear generation warranty (minimum 80% output after 25 years). Inverters come with a standard 5 to 10 year manufacturer warranty with extended support."}
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
                    "whatsapp_number": "919053899899",
                    "prefill_message": "Hello! I am interested in Har Ghar Solar Rooftop Solutions for my premises. Please share quotation and arrange site audit.",
                    "office_address": "D.No. 4-48, Main Road, Saripalli, Pendurthy, Visakhapatnam, AP - 531173",
                    "working_hours": "Mon - Sat: 9:00 AM - 7:30 PM",
                    "helpline": "+91 90538 99899"
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
        "title": "Industrial Hub & Franchise Opportunities",
        "subtitle": "Turnkey Regional Franchise, Distribution & Charging Hub Infrastructure",
        "summary": "Join India's fastest growing green mobility & energy ecosystem. Build a multi-revenue franchise hub spanning EV sales, battery swapping, fast charging, spare parts supply, and solar EPC distribution.",
        "hero_media_url": "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=1600&q=80",
        "theme_config": {"primary_color": "#1e40af", "accent_color": "#f59e0b", "dark_mode": False},
        "default_language": "en",
        "active_languages": ["en", "te", "hi", "ta"],
        "sections": [
            {
                "section_type": "hero",
                "section_key": "hero",
                "title": "Own an Integrated Green Energy & EV Franchise in Your District",
                "subtitle": "Earn across 5 High-Margin Streams: EV Sales, Battery Swapping, Fast Charging, Spares & Solar EPC",
                "content_variants": {
                    "en": {
                        "title": "Own an Integrated Green Energy & EV Franchise in Your District",
                        "subtitle": "Earn across 5 High-Margin Streams: EV Sales, Battery Swapping, Fast Charging, Spares & Solar EPC",
                        "cta_text": "Request Franchise Prospectus",
                        "cta_phone": "919053899899"
                    },
                    "te": {
                        "title": "మీ జిల్లాలో గ్రీన్ ఎనర్జీ & ఈవీ ఫ్రాంచైజీ హబ్‌ను ప్రారంభించండి",
                        "subtitle": "5 స్థిరమైన ఆదాయ మార్గాలు: ఈవీ విక్రయాలు, బ్యాటరీ స్వాప్, ఫాస్ట్ ఛార్జింగ్, స్పేర్స్ & సోలార్",
                        "cta_text": "ఫ్రాంచైజీ సమాచారం పొందండి",
                        "cta_phone": "919053899899"
                    },
                    "hi": {
                        "title": "अपने जिले में ग्रीन एनर्जी और ईवी फ्रेंचाइजी हब के मालिक बनें",
                        "subtitle": "5 बड़े मुनाफे वाले व्यवसाय: ईवी बिक्री, बैटरी स्वैपिंग, फास्ट चार्जिंग, स्पेयर पार्ट्स और सोलर",
                        "cta_text": "फ्रेंचाइजी विवरण प्राप्त करें",
                        "cta_phone": "919053899899"
                    },
                    "ta": {
                        "title": "உங்கள் மாவட்டத்தில் பசுமை ஆற்றல் & மின்சார வாகன உரிமை மையத்தை தொடங்குங்கள்",
                        "subtitle": "5 லாபகரமான வணிக வழிகள்: வாகன விற்பனை, பேட்டரி மாற்று மையம், சார்ஜிங், உதிரிபாகங்கள் & சோலார்",
                        "cta_text": "வணிக வாய்ப்பு விவரங்கள் பெறுக",
                        "cta_phone": "919053899899"
                    }
                },
                "configuration": {
                    "badge": "🚀 Exclusive District Territorial Rights",
                    "stats": [
                        {"label": "Revenue Streams", "value": "5 Streams"},
                        {"label": "Territory Protection", "value": "Exclusive Pin Codes"},
                        {"label": "Expected Monthly ROI", "value": "28% - 35%"},
                        {"label": "Setup Timeline", "value": "30 Days"}
                    ]
                }
            },
            {
                "section_type": "highlights_grid",
                "section_key": "revenue_streams",
                "title": "5 High-Margin Revenue Verticals in One Hub",
                "subtitle": "Comprehensive commercial model built for sustained year-round profitability",
                "content_variants": {
                    "en": {"title": "5 High-Margin Revenue Verticals in One Hub", "subtitle": "Comprehensive commercial model built for sustained year-round profitability"},
                    "te": {"title": "ఒకే హబ్‌లో 5 లాభదాయక ఆదాయ మార్గాలు", "subtitle": "సంవత్సరం పొడవునా స్థిరమైన లాభాలను అందించే వాణిజ్య నమూనా"},
                    "hi": {"title": "एक ही हब में 5 मुनाफे वाले व्यापार", "subtitle": "सालाना शानदार कमाई के लिए पूरी तरह से तैयार बिजनेस मॉडल"},
                    "ta": {"title": "ஒரே மையத்தில் 5 பிரதான வருவாய் வழிகள்", "subtitle": "ஆண்டு முழுவதும் நிலையான லாபம் ஈட்டும் வணிக முறை"}
                },
                "configuration": {
                    "cards": [
                        {"icon": "electric_rickshaw", "title": "EV 2W & 3W Dealership", "desc": "Exclusive showroom distribution rights for high-demand passenger and commercial delivery EVs."},
                        {"icon": "battery_charging_full", "title": "BaaS & Battery Swapping", "desc": "Automated 60-second battery swapping station generating recurring daily revenue from delivery fleets."},
                        {"icon": "ev_station", "title": "Public DC Fast Charging", "desc": "High-output fast charging station with smart app billing, open to all commercial and private EVs."},
                        {"icon": "build", "title": "OEM Spares & Service Center", "desc": "Authorized spares depot supplying local garages, fleet operators, and certified technicians."}
                    ]
                }
            },
            {
                "section_type": "packages_pricing",
                "section_key": "models",
                "title": "Franchise Investment Models",
                "subtitle": "Tailored for town centers, highway junctions, and industrial transport corridors",
                "content_variants": {
                    "en": {"title": "Franchise Investment Models", "subtitle": "Select the ideal tier for your capital and commercial property location"},
                    "te": {"title": "ఫ్రాంచైజీ పెట్టుబడి నమూనాలు", "subtitle": "మీ మూలధనం మరియు స్థలానికి తగిన ప్యాకేజీని ఎంచుకోండి"},
                    "hi": {"title": "फ्रेंचाइजी निवेश के विकल्प", "subtitle": "अपनी पूंजी और लोकेशन के अनुसार सही मॉडल चुनें"},
                    "ta": {"title": "உரிமை வணிக முதலீட்டு முறைகள்", "subtitle": "உங்கள் முதலீட்டிற்கு ஏற்ற சிறந்த தேர்வு"}
                },
                "configuration": {
                    "plans": [
                        {
                            "name": "District Express Hub",
                            "ideal_for": "Town Center / 1,500 - 2,000 sq.ft.",
                            "price": "₹15,00,000",
                            "features": ["EV 2W Display & Delivery Depot", "1x Battery Swap Station (8 Slots)", "Standard Spares Inventory Pack", "CRM & ERP Software Access"],
                            "is_popular": False
                        },
                        {
                            "name": "Regional Mega Hub",
                            "ideal_for": "District HQ / 3,000 - 5,000 sq.ft.",
                            "price": "₹35,00,000",
                            "features": ["EV 2W + 3W Cargo Full Dealership", "2x Dual-Gun DC Fast Chargers (30kW)", "2x Automated Battery Swapping Cabinets", "Authorized Regional Service Center", "Exclusive 30km District Protection"],
                            "is_popular": True
                        }
                    ]
                }
            },
            {
                "section_type": "media_gallery",
                "section_key": "installation_gallery",
                "title": "Industrial Hub & Infrastructure Showcase (ఇండస్ట్రియల్ హబ్ గ్యాలరీ)",
                "subtitle": "State-of-the-art green mobility hubs, battery swapping infrastructure & franchise operations",
                "content_variants": {
                    "en": {
                        "title": "Industrial Hub & Infrastructure Showcase",
                        "subtitle": "Experience our integrated regional franchise hubs, fast charging stations, and logistics infrastructure."
                    },
                    "te": {
                        "title": "ఇండస్ట్రియల్ హబ్ మరియు మౌలిక వసతుల గ్యాలరీ",
                        "subtitle": "మా రీజినల్ ఫ్రాంచైజీ హబ్‌లు, బ్యాటరీ స్వాపింగ్ మరియు ఫాస్ట్ ఛార్జింగ్ కేంద్రాల దృశ్యాలు."
                    }
                },
                "media_gallery": [
                    {
                        "url": "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Integrated Multi-Bay EV Franchise Hub — Visakhapatnam Regional Depot",
                        "tag": "Franchise Hub"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Automated 8-Slot Quick Battery Swapping Station in Operation — Vijayawada",
                        "tag": "Battery Swapping"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1558441719-8b449c6ff807?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Dual-Gun 30kW DC Fast Charging Station with RFID Billing — Gajuwaka",
                        "tag": "DC Fast Charging"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1504917599217-d4dc5ebe6122?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Regional Spare Parts & Battery Inventory Depot — Autonagar, Vizag",
                        "tag": "Parts Depot"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1617788138017-80ad40651399?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Commercial EV 2W & 3W Showroom Display Floor — Rajahmundry",
                        "tag": "Showroom Display"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1578575437130-527eed3abbec?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Certified EV Fleet Maintenance & Diagnostic Service Bay — Guntur",
                        "tag": "Service Workshop"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1580674684081-7617fbf3d745?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Heavy-Duty Electrical Transformer & Power Substation Setup — Kakinada",
                        "tag": "Infrastructure"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1563986768609-322da13575f3?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Fleet Telematics & Central Cloud Operations Control Desk",
                        "tag": "Smart Operations"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1521737604893-d14cc237f11d?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Franchise Partner Onboarding & Business Orientation Session",
                        "tag": "Franchise Onboarding"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1600880292203-757bb62b4baf?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Master Franchise Agreement Signing & Territory Handover",
                        "tag": "Partner Milestones"
                    }
                ],
                "configuration": {
                    "auto_play_interval_ms": 3000,
                    "enable_lightbox": True,
                    "videos": [
                        {
                            "title": "MyntReal Integrated EV & Green Energy Franchise Hub Walkthrough",
                            "youtube_id": "kYJmQ6X2q38",
                            "url": "https://www.youtube.com/watch?v=kYJmQ6X2q38",
                            "embed_url": "https://www.youtube-nocookie.com/embed/kYJmQ6X2q38"
                        },
                        {
                            "title": "Automated Battery Swapping & DC Fast Charging Commercial Operations",
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
                "item_type": "PACKAGE",
                "item_code": "HUB-DIST-EXP",
                "title": "District Express Franchise Hub",
                "subtitle": "Turnkey green mobility hub for Tier-2 & Tier-3 commercial towns",
                "specifications": [
                    {"label": "Space Needed", "value": "1,500 - 2,000 sq.ft."},
                    {"label": "Power Connected", "value": "25 kVA 3-Phase"},
                    {"label": "Territory Rights", "value": "Single Mandate Pincodes"},
                    {"label": "Expected Monthly Net", "value": "₹1.5L - ₹2.8L"}
                ],
                "pricing": {"base_price": 1500000, "currency": "INR"},
                "media_urls": ["https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=800&q=80"],
                "badges": ["Fast Payback", "Turnkey"]
            },
            {
                "item_type": "PACKAGE",
                "item_code": "HUB-REG-MEGA",
                "title": "Regional Mega Industrial Hub",
                "subtitle": "Full-scale regional hub with DC fast charging, battery swapping & EV distribution",
                "specifications": [
                    {"label": "Space Needed", "value": "3,000 - 5,000 sq.ft."},
                    {"label": "Power Connected", "value": "63 kVA Dedicated Transformer"},
                    {"label": "Territory Rights", "value": "Exclusive 30km Radius"},
                    {"label": "Expected Monthly Net", "value": "₹3.8L - ₹6.5L"}
                ],
                "pricing": {"base_price": 3500000, "currency": "INR"},
                "media_urls": ["https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=800&q=80"],
                "badges": ["Master Franchise", "High Yield"]
            }
        ]
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
                        "cta_phone": "919053899899"
                    },
                    "te": {
                        "title": "లాజిస్టిక్స్ మరియు డెలివరీ కోసం ప్రత్యేకంగా రూపొందించిన కమర్షియల్ ఈవీలు",
                        "subtitle": "ప్రతి వాహనంపై నెలకు ₹6,000+ ఆదా చేసుకోండి — తక్కువ ఖర్చు మరియు వేగవంతమైన బ్యాటరీ మార్పిడి",
                        "cta_text": "ఫ్లీట్ టెస్ట్ డ్రైవ్ బుక్ చేయండి",
                        "cta_phone": "919053899899"
                    },
                    "hi": {
                        "title": "डिलीवरी और लॉजिस्टिक्स के लिए विशेष रूप से निर्मित कमर्शियल ईवी",
                        "subtitle": "हर गाड़ी पर प्रति माह ₹6,000+ की बचत — शून्य पेट्रोल खर्च और तुरंत बैटरी स्वैपिंग",
                        "cta_text": "फ्लीट ट्रायल और कोटेशन प्राप्त करें",
                        "cta_phone": "919053899899"
                    },
                    "ta": {
                        "title": "லாஜிஸ்டிக்ஸ் மற்றும் வணிக விநியோகத்திற்கான சக்திவாய்ந்த மின்சார வாகனங்கள்",
                        "subtitle": "ஒவ்வொரு வாகனத்திற்கும் மாதம் ₹6,000+ வரை சேமிப்பு — எரிபொருள் செலவின்றி உடனடி இயக்கம்",
                        "cta_text": "வணிக மாதிரி சோதனை செய்க",
                        "cta_phone": "919053899899"
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
        "slug": "ev-smart-commuter",
        "title": "Smart Electric 2-Wheelers & Passenger EVs",
        "subtitle": "Next-Gen High-Speed Commuter Electric Scooters & Bikes for Everyday Riders",
        "summary": "Experience the ultimate daily commute. Modern styling, fast acceleration, 120km real-world range, mobile app tracking, and zero maintenance with long-lasting LFP battery tech.",
        "hero_media_url": "https://images.unsplash.com/photo-1558981403-c5f9899a28bc?auto=format&fit=crop&w=1600&q=80",
        "theme_config": {"primary_color": "#7c3aed", "accent_color": "#ec4899", "dark_mode": False},
        "default_language": "en",
        "active_languages": ["en", "te", "hi", "ta"],
        "sections": [
            {
                "section_type": "hero",
                "section_key": "hero",
                "title": "Style, Power & Unlimited Savings — Meet Zynova Smart EVs",
                "subtitle": "120 km True Range, ₹0.20 per Kilometer Commute, 3-Year Comprehensive Warranty",
                "content_variants": {
                    "en": {"title": "Style, Power & Unlimited Savings — Meet Zynova Smart EVs", "subtitle": "120 km True Range, ₹0.20 per Kilometer Commute, 3-Year Comprehensive Warranty"},
                    "te": {"title": "స్టైల్, శక్తి మరియు అపారమైన పొదుపు — జైనోవా స్మార్ట్ ఈవీలు", "subtitle": "120 కి.మీ నిజమైన రేంజ్, కి.మీకి కేవలం 20 పైసల ఖర్చు మరియు 3 ఏళ్ళ వారంటీ"},
                    "hi": {"title": "स्टाइल, पावर और बेमिसाल बचत — ज़ाइनोवा स्मार्ट इलेक्ट्रिक स्कूटर्स", "subtitle": "120 किमी की रियल रेंज, मात्र 20 पैसे प्रति किमी खर्च और 3 साल की वारंटी"},
                    "ta": {"title": "அழகும் ஆற்றலும் நிறைந்த ஜைனோவா ஸ்மார்ட் மின்சார வாகனங்கள்", "subtitle": "120 கி.மீ தூர இயக்கம், கி.மீக்கு 20 பைசா மட்டுமே மற்றும் 3 ஆண்டுகள் உத்தரவாதம்"}
                },
                "configuration": {
                    "badge": "🌟 Premium Commuter Electric Scooters",
                    "stats": [
                        {"label": "True Range", "value": "120 km"},
                        {"label": "Top Speed", "value": "65 km/h"},
                        {"label": "Charging Time", "value": "3.5 Hours"},
                        {"label": "Warranty", "value": "3 Years / 50k km"}
                    ]
                }
            },
            {
                "section_type": "media_gallery",
                "section_key": "installation_gallery",
                "title": "Smart Commuter EV Scooters Gallery (స్మార్ట్ ఈవీ స్కూటర్స్ గ్యాలరీ)",
                "subtitle": "High-speed commuter electric scooters designed for daily comfort, style and savings",
                "content_variants": {
                    "en": {
                        "title": "Smart Commuter EV Scooters Gallery",
                        "subtitle": "Explore stylish commuter scooters, vibrant color variants, digital cockpit features and happy rider deliveries."
                    },
                    "te": {
                        "title": "స్మార్ట్ కమ్యూటర్ ఈవీ స్కూటర్ల గ్యాలరీ",
                        "subtitle": "స్టైలిష్ డిజైన్, డిజిటల్ ఫీచర్లు మరియు రోజువారీ ప్రయాణానికి అత్యుత్తమ స్కూటర్లు."
                    }
                },
                "media_gallery": [
                    {
                        "url": "https://images.unsplash.com/photo-1558981403-c5f9899a28bc?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Zynova EcoRide City Commuter in Pearl White — Daily Urban Mobility",
                        "tag": "Commuter EV"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1558981806-ec527fa84c39?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Zynova Sprint XR Sport Flagship in Crimson Red — 65 km/h Top Speed",
                        "tag": "Flagship Sport"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1508873696983-2df5293cb32f?auto=format&fit=crop&w=1200&q=80",
                        "caption": "All-Digital Full-Color LCD Dashboard with Navigation & Call Alerts",
                        "tag": "Digital Cockpit"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1593941707882-a5bba14938c7?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Compact Portable 60V Lithium Battery Pack with Home Wall Charger",
                        "tag": "Home Charging"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1558441719-8b449c6ff807?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Dual Front & Rear Hydraulic Disc Brakes with CBS Braking Safety",
                        "tag": "Safety Features"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Spacious 28L Under-Seat Storage Accommodating Full-Face Helmet",
                        "tag": "Utility Design"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1517524008697-84bbe3c3fd98?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Night-Ride High-Intensity Dual LED Projector Headlamp Beam",
                        "tag": "LED Lighting"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=1200&q=80",
                        "caption": "College Students Test Riding the Zynova Sprint XR — Smooth Acceleration",
                        "tag": "Test Drive"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1521791136064-7986c2920216?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Happy Family Festive Delivery Key Handover Ceremony — Vizag Showroom",
                        "tag": "Customer Delivery"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1600880292203-757bb62b4baf?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Zero Petrol Expense Milestone — Customer Celebrating 10,000 Clean KM",
                        "tag": "Green Milestone"
                    }
                ],
                "configuration": {
                    "auto_play_interval_ms": 3000,
                    "enable_lightbox": True,
                    "videos": [
                        {
                            "title": "Zynova Smart Commuter Electric Scooter Comprehensive Review & Range Test",
                            "youtube_id": "kYJmQ6X2q38",
                            "url": "https://www.youtube.com/watch?v=kYJmQ6X2q38",
                            "embed_url": "https://www.youtube-nocookie.com/embed/kYJmQ6X2q38"
                        },
                        {
                            "title": "Smart Connectivity, Mobile App & Portable Battery Demonstration",
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
                "item_code": "EV-B2C-ECORIDE",
                "title": "Zynova EcoRide City",
                "subtitle": "Effortless city mobility with digital speedometer, reverse assist, and USB charging",
                "specifications": [
                    {"label": "Range", "value": "90 km True Range"},
                    {"label": "Top Speed", "value": "45 km/h"},
                    {"label": "Battery", "value": "60V 26Ah Portable Lithium"},
                    {"label": "Brakes", "value": "Front Disc + Rear Drum with CBS"}
                ],
                "pricing": {"base_price": 68999, "currency": "INR"},
                "media_urls": ["https://images.unsplash.com/photo-1558981403-c5f9899a28bc?auto=format&fit=crop&w=800&q=80"],
                "badges": ["Daily Commuter", "Portable Battery"]
            },
            {
                "item_type": "PRODUCT",
                "item_code": "EV-B2C-SPRINTXR",
                "title": "Zynova Sprint XR Sport",
                "subtitle": "High-speed flagship electric scooter with cruise control and smartphone connectivity",
                "specifications": [
                    {"label": "Range", "value": "125 km Sport Range"},
                    {"label": "Top Speed", "value": "65 km/h"},
                    {"label": "Motor", "value": "2.5 kW Peak BLDC Hub Motor"},
                    {"label": "App Features", "value": "GPS Navigation, Anti-theft Geofence"}
                ],
                "pricing": {"base_price": 89999, "currency": "INR"},
                "media_urls": ["https://images.unsplash.com/photo-1558981806-ec527fa84c39?auto=format&fit=crop&w=800&q=80"],
                "badges": ["Flagship Sport", "App Connected"]
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
        "title": "Executive Training Center & Professional Certifications",
        "subtitle": "Hands-on EV Technology, Solar EPC & Renewable Energy Skill Programs",
        "summary": "Launch a high-paying green career. Master hands-on diagnostics of electric vehicle powertrains, lithium battery servicing, and commercial rooftop solar installation with 100% placement support.",
        "hero_media_url": "https://images.unsplash.com/photo-1524178232363-1fb2b075b655?auto=format&fit=crop&w=1600&q=80",
        "theme_config": {"primary_color": "#4338ca", "accent_color": "#06b6d4", "dark_mode": False},
        "default_language": "en",
        "active_languages": ["en", "te", "hi", "ta"],
        "sections": [
            {
                "section_type": "hero",
                "section_key": "hero",
                "title": "Become a Certified Green Technology Professional",
                "subtitle": "Hands-on Lab Training in EV Diagnostics, Lithium Battery Repair, and Solar EPC Engineering",
                "content_variants": {
                    "en": {"title": "Become a Certified Green Technology Professional", "subtitle": "Hands-on Lab Training in EV Diagnostics, Lithium Battery Repair, and Solar EPC Engineering"},
                    "te": {"title": "సర్టిఫైడ్ గ్రీన్ టెక్నాలజీ ప్రొఫెషనల్ అవ్వండి", "subtitle": "ఈవీ డయాగ్నస్టిక్స్, లిథియం బ్యాటరీ సర్వీసింగ్ మరియు సోలార్ ప్లాంట్లలో ప్రాక్టికల్ ల్యాబ్ శిక్షణ"},
                    "hi": {"title": "सर्टिफाइड ग्रीन टेक्नोलॉजी प्रोफेशनल बनें", "subtitle": "ईवी डायग्नोस्टिक्स, लिथियम बैटरी रिपेयर और सोलर इंजीनियरिंग में प्रैक्टिकल ट्रेनिंग"},
                    "ta": {"title": "பசுமை தொழில்நுட்ப வல்லுநராகுங்கள்", "subtitle": "மின்சார வாகனம் மற்றும் சோலார் தொழில்நுட்பத்தில் செய்முறை பயிற்சி"}
                },
                "configuration": {
                    "badge": "🎓 Govt Recognized Certification + 100% Placement Assistance",
                    "stats": [
                        {"label": "Trained Alumni", "value": "1,200+"},
                        {"label": "Placement Rate", "value": "94%"},
                        {"label": "Hands-on Practical", "value": "70% Lab Hours"},
                        {"label": "Hiring Partners", "value": "85+ Companies"}
                    ]
                }
            },
            {
                "section_type": "media_gallery",
                "section_key": "installation_gallery",
                "title": "Executive Training Center & Labs Showcase (శిక్షణ కేంద్రం & ప్రాక్టికల్ ల్యాబ్స్)",
                "subtitle": "State-of-the-art hands-on labs for EV diagnostics, battery servicing and solar EPC engineering",
                "content_variants": {
                    "en": {
                        "title": "Executive Training Center & Labs Showcase",
                        "subtitle": "See our state-of-the-art labs, hands-on EV diagnostics, solar EPC simulations, and student placement drives."
                    },
                    "te": {
                        "title": "శిక్షణ కేంద్రం మరియు ప్రాక్టికల్ ల్యాబ్స్ గ్యాలరీ",
                        "subtitle": "ఈవీ సర్వీసింగ్, లిథియం బ్యాటరీ రిపేర్ మరియు సోలార్ డిజైనింగ్ శిక్షణా తరగతులు."
                    }
                },
                "media_gallery": [
                    {
                        "url": "https://images.unsplash.com/photo-1524178232363-1fb2b075b655?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Advanced EV Powertrain Diagnostics Lab with Cut-Section Vehicle Simulator",
                        "tag": "EV Diagnostics Lab"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1581092160607-ee22621dd758?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Students Practical BMS Debugging & Cell Balancing Hands-on Session",
                        "tag": "Battery Lab"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1509391365360-2e959784a276?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Live Solar Rooftop Mounting & Structure Alignment Practical Workshop",
                        "tag": "Solar EPC Workshop"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Oscilloscope CAN Bus Signal Analysis & Sensor Fault Diagnosis Training",
                        "tag": "Electronics & CAN"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1531482615713-2afd69097998?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Interactive Classroom Lecture on Electric Vehicle Architecture & Safety",
                        "tag": "Theory Session"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?auto=format&fit=crop&w=1200&q=80",
                        "caption": "PVSyst & AutoCAD Solar Plant 3D Shadow Simulation Computer Lab",
                        "tag": "CAD Simulation"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1577495508048-b635879837f1?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Instructor Demonstrating BLDC Hub Motor Stator Rewinding & Hall Sensors",
                        "tag": "Motor Workshop"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1523240795612-9a054b0db644?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Group Capstone Project: Commissioning a 5kW Dual-Battery Setup",
                        "tag": "Capstone Project"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1521737604893-d14cc237f11d?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Campus Placement Drive with Leading EV OEMs & Solar EPC Employers",
                        "tag": "Campus Placement"
                    },
                    {
                        "url": "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=1200&q=80",
                        "caption": "Graduation Day: Certified Green Energy Technicians Receiving Certificates",
                        "tag": "Graduation Day"
                    }
                ],
                "configuration": {
                    "auto_play_interval_ms": 3000,
                    "enable_lightbox": True,
                    "videos": [
                        {
                            "title": "Master Certificate in EV Powertrain Diagnostics — Practical Lab Tour",
                            "youtube_id": "kYJmQ6X2q38",
                            "url": "https://www.youtube.com/watch?v=kYJmQ6X2q38",
                            "embed_url": "https://www.youtube-nocookie.com/embed/kYJmQ6X2q38"
                        },
                        {
                            "title": "Hands-on Rooftop Solar EPC Design & HelioScope Simulation Training",
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
                "item_type": "COURSE",
                "item_code": "ETC-EV-TECH",
                "title": "Master Certificate in EV Powertrain & Battery Tech",
                "subtitle": "Comprehensive 6-week program covering EV controllers, BMS debugging, and CAN bus protocols",
                "specifications": [
                    {"label": "Duration", "value": "6 Weeks (Weekend / Weekday Batches)"},
                    {"label": "Eligibility", "value": "Diploma / B.Tech / ITI / Auto Enthusiasts"},
                    {"label": "Certification", "value": "Government Recognized Skill Certificate"},
                    {"label": "Career Roles", "value": "EV Service Specialist, BMS Diagnostician, Plant QC"}
                ],
                "pricing": {"base_price": 24999, "currency": "INR"},
                "media_urls": ["https://images.unsplash.com/photo-1524178232363-1fb2b075b655?auto=format&fit=crop&w=800&q=80"],
                "badges": ["Most Popular", "100% Placement Aid"]
            },
            {
                "item_type": "COURSE",
                "item_code": "ETC-SOLAR-EPC",
                "title": "Solar EPC Design & Project Management Masterclass",
                "subtitle": "Practical solar design, Helioscope/PVSyst simulation, net-metering liaison, and site commissioning",
                "specifications": [
                    {"label": "Duration", "value": "4 Weeks (Hands-on Project Based)"},
                    {"label": "Software Tools", "value": "HelioScope, AutoCAD Solar, PVSyst"},
                    {"label": "Live Project", "value": "Design a 25 kW Commercial Rooftop Project"},
                    {"label": "Career Roles", "value": "Solar Design Engineer, EPC Project Manager"}
                ],
                "pricing": {"base_price": 18999, "currency": "INR"},
                "media_urls": ["https://images.unsplash.com/photo-1509391365360-2e959784a276?auto=format&fit=crop&w=800&q=80"],
                "badges": ["Project Included", "Design Tools"]
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

        db.commit()
        logger.info(f"Catalog seeding complete. Created: {created_count}, Existing: {updated_count}")

    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding digital catalogs: {e}", exc_info=True)
        raise
    finally:
        if close_db:
            db.close()


if __name__ == "__main__":
    seed_default_catalogs()
