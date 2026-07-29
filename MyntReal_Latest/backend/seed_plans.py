import asyncio
import json
from app.core.database import get_db, engine
from app.models.recharge import RechargePlan
from app.models.base import Base

async def seed_plans():
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS recharge_plans CASCADE"))
    RechargePlan.__table__.create(bind=engine, checkfirst=True)

    # ---------------------------------------------------------
    # MASSIVE PLAN CATALOG (2026 Updated Pricing & Structures)
    # Total Plans: ~150
    # ---------------------------------------------------------
    plans = [
        # ==========================================
        # JIO (Reliance Jio)
        # ==========================================
        # Jio Unlimited 5G
        {"operator": "Jio", "category": "Unlimited", "amount": 189, "validity": "28 Days", "data_benefit": "2 GB Total", "description": "Unlimited calls, 300 SMS total. Affordable base pack.", "tags": "Affordable"},
        {"operator": "Jio", "category": "Unlimited", "amount": 209, "validity": "22 Days", "data_benefit": "1 GB/Day", "description": "Unlimited calls, 100 SMS/day.", "tags": "1GB/Day"},
        {"operator": "Jio", "category": "Unlimited", "amount": 239, "validity": "22 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day. True 5G.", "tags": "True 5G"},
        {"operator": "Jio", "category": "Unlimited", "amount": 249, "validity": "28 Days", "data_benefit": "1 GB/Day", "description": "Unlimited calls, 100 SMS/day.", "tags": "1GB/Day"},
        {"operator": "Jio", "category": "Unlimited", "amount": 299, "validity": "28 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day, JioTV, JioCinema.", "tags": "True 5G, Popular"},
        {"operator": "Jio", "category": "Unlimited", "amount": 349, "validity": "28 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day, JioTV, JioCinema.", "tags": "True 5G, Popular"},
        {"operator": "Jio", "category": "Unlimited", "amount": 399, "validity": "28 Days", "data_benefit": "2.5 GB/Day", "description": "Unlimited calls, 100 SMS/day.", "tags": "True 5G"},
        {"operator": "Jio", "category": "Unlimited", "amount": 449, "validity": "28 Days", "data_benefit": "3 GB/Day", "description": "Heavy data plan, unlimited calls, 100 SMS/day.", "tags": "True 5G, Heavy Data"},
        {"operator": "Jio", "category": "Unlimited", "amount": 479, "validity": "84 Days", "data_benefit": "6 GB Total", "description": "Unlimited calls, 1000 SMS total. Long validity affordable pack.", "tags": "Affordable"},
        {"operator": "Jio", "category": "Unlimited", "amount": 533, "validity": "56 Days", "data_benefit": "1 GB/Day", "description": "Unlimited calls, 100 SMS/day.", "tags": "1GB/Day"},
        {"operator": "Jio", "category": "Unlimited", "amount": 579, "validity": "56 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day, JioTV.", "tags": "True 5G"},
        {"operator": "Jio", "category": "Unlimited", "amount": 629, "validity": "56 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day, Jio apps.", "tags": "True 5G"},
        {"operator": "Jio", "category": "Unlimited", "amount": 719, "validity": "71 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day, Jio apps.", "tags": "True 5G"},
        {"operator": "Jio", "category": "Unlimited", "amount": 749, "validity": "72 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day, Jio apps.", "tags": "True 5G"},
        {"operator": "Jio", "category": "Unlimited", "amount": 799, "validity": "84 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day.", "tags": "True 5G, Best Value"},
        {"operator": "Jio", "category": "Unlimited", "amount": 859, "validity": "84 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day, Jio apps.", "tags": "True 5G, Hero Plan"},
        {"operator": "Jio", "category": "Unlimited", "amount": 899, "validity": "90 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day, Jio apps.", "tags": "True 5G"},
        {"operator": "Jio", "category": "Unlimited", "amount": 1099, "validity": "84 Days", "data_benefit": "3 GB/Day", "description": "Heavy data plan, unlimited calls, 100 SMS/day.", "tags": "True 5G, Heavy Data"},
        {"operator": "Jio", "category": "Unlimited", "amount": 1199, "validity": "84 Days", "data_benefit": "3 GB/Day", "description": "Unlimited calls, 100 SMS/day + Free Int. Roaming (UAE/US/Canada selected).", "tags": "True 5G, Premium"},
        {"operator": "Jio", "category": "Unlimited", "amount": 1499, "validity": "84 Days", "data_benefit": "3 GB/Day", "description": "Netflix (Basic) included + 3GB/day.", "tags": "True 5G, Netflix"},

        # Jio Annual
        {"operator": "Jio", "category": "Annual", "amount": 1899, "validity": "336 Days", "data_benefit": "24 GB Total", "description": "Affordable annual pack for voice-first users.", "tags": "Affordable, Annual"},
        {"operator": "Jio", "category": "Annual", "amount": 2999, "validity": "365 Days", "data_benefit": "2.5 GB/Day", "description": "Standard annual plan with 5G.", "tags": "True 5G, Annual"},
        {"operator": "Jio", "category": "Annual", "amount": 3599, "validity": "365 Days", "data_benefit": "2.5 GB/Day", "description": "Year-long peace of mind with heavy daily data.", "tags": "True 5G, Hero Plan"},

        # Jio Entertainment
        {"operator": "Jio", "category": "Entertainment", "amount": 398, "validity": "28 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls + Sony LIV, ZEE5, Lionsgate.", "tags": "True 5G, SonyLIV, ZEE5"},
        {"operator": "Jio", "category": "Entertainment", "amount": 448, "validity": "28 Days", "data_benefit": "2 GB/Day", "description": "Sony LIV, ZEE5, Prime Video Mobile Edition, 14 OTTs.", "tags": "True 5G, 14 OTTs"},
        {"operator": "Jio", "category": "Entertainment", "amount": 549, "validity": "28 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls + Disney+ Hotstar Mobile.", "tags": "True 5G, Hotstar"},
        {"operator": "Jio", "category": "Entertainment", "amount": 698, "validity": "28 Days", "data_benefit": "2 GB/Day", "description": "Swiggy One Lite + 14 OTT Apps + Unlimited 5G.", "tags": "True 5G, Swiggy One"},
        {"operator": "Jio", "category": "Entertainment", "amount": 739, "validity": "78 Days", "data_benefit": "1.5 GB/Day", "description": "Saavn Pro + JioTV.", "tags": "True 5G, Saavn Pro"},
        {"operator": "Jio", "category": "Entertainment", "amount": 789, "validity": "78 Days", "data_benefit": "2 GB/Day", "description": "Saavn Pro + JioTV.", "tags": "True 5G, Saavn Pro"},
        {"operator": "Jio", "category": "Entertainment", "amount": 848, "validity": "84 Days", "data_benefit": "2 GB/Day", "description": "JioTV Premium, Zee5, SonyLiv.", "tags": "True 5G, Premium OTT"},
        {"operator": "Jio", "category": "Entertainment", "amount": 898, "validity": "90 Days", "data_benefit": "2 GB/Day", "description": "JioTV Premium (14 OTT apps bundled).", "tags": "True 5G, 14 OTTs"},
        {"operator": "Jio", "category": "Entertainment", "amount": 1049, "validity": "84 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls + Sony LIV & ZEE5 Premium.", "tags": "True 5G, SonyLIV, ZEE5"},
        {"operator": "Jio", "category": "Entertainment", "amount": 1198, "validity": "84 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls + Prime Video Lite & Disney+ Hotstar.", "tags": "True 5G, Prime Video, Hotstar"},
        {"operator": "Jio", "category": "Entertainment", "amount": 1299, "validity": "84 Days", "data_benefit": "2 GB/Day", "description": "Netflix (Mobile) included.", "tags": "True 5G, Netflix"},
        {"operator": "Jio", "category": "Entertainment", "amount": 3178, "validity": "365 Days", "data_benefit": "2 GB/Day", "description": "Disney+ Hotstar Premium Annual.", "tags": "True 5G, Hotstar, Annual"},
        {"operator": "Jio", "category": "Entertainment", "amount": 3227, "validity": "365 Days", "data_benefit": "2 GB/Day", "description": "Prime Video Mobile Edition Annual.", "tags": "True 5G, Prime Video, Annual"},
        {"operator": "Jio", "category": "Entertainment", "amount": 4498, "validity": "365 Days", "data_benefit": "2 GB/Day", "description": "14 OTT Apps Annual + Priority Customer Service.", "tags": "True 5G, 14 OTTs, Annual"},

        # Jio Data Add-ons & Top-up
        {"operator": "Jio", "category": "Data Add-on", "amount": 15, "validity": "Active Plan", "data_benefit": "1 GB", "description": "Instant 1GB high-speed data booster (4G/5G).", "tags": "Data Booster"},
        {"operator": "Jio", "category": "Data Add-on", "amount": 19, "validity": "Active Plan", "data_benefit": "1.5 GB", "description": "Instant 1.5GB high-speed data booster.", "tags": "Data Booster"},
        {"operator": "Jio", "category": "Data Add-on", "amount": 25, "validity": "Active Plan", "data_benefit": "2 GB", "description": "Instant 2GB high-speed data booster.", "tags": "Data Booster"},
        {"operator": "Jio", "category": "Data Add-on", "amount": 29, "validity": "Active Plan", "data_benefit": "2.5 GB", "description": "Instant 2.5GB high-speed data booster.", "tags": "Data Booster"},
        {"operator": "Jio", "category": "Data Add-on", "amount": 51, "validity": "Active Plan", "data_benefit": "Unlimited 5G", "description": "True 5G Upgrade voucher + 3GB 4G Data.", "tags": "True 5G"},
        {"operator": "Jio", "category": "Data Add-on", "amount": 61, "validity": "Active Plan", "data_benefit": "6 GB", "description": "6GB data booster.", "tags": "Data Booster"},
        {"operator": "Jio", "category": "Data Add-on", "amount": 69, "validity": "Active Plan", "data_benefit": "6 GB + Unlimited 5G", "description": "High-volume data booster with 5G.", "tags": "True 5G"},
        {"operator": "Jio", "category": "Data Add-on", "amount": 119, "validity": "Active Plan", "data_benefit": "12 GB", "description": "12GB data booster.", "tags": "Data Booster"},
        {"operator": "Jio", "category": "Data Add-on", "amount": 121, "validity": "Active Plan", "data_benefit": "12 GB + Unlimited 5G", "description": "Massive data booster for heavy usage.", "tags": "True 5G"},
        {"operator": "Jio", "category": "Data Add-on", "amount": 139, "validity": "Active Plan", "data_benefit": "12 GB + Unlimited 5G + OTT", "description": "12GB data booster with JioTV Premium.", "tags": "True 5G, OTT Combo"},
        {"operator": "Jio", "category": "Data Add-on", "amount": 219, "validity": "30 Days", "data_benefit": "30 GB", "description": "Standalone data pack (No active plan required).", "tags": "Data Only"},
        {"operator": "Jio", "category": "Data Add-on", "amount": 287, "validity": "30 Days", "data_benefit": "40 GB", "description": "Heavy data standalone pack.", "tags": "Data Only"},
        {"operator": "Jio", "category": "Top-up", "amount": 10, "validity": "Unlimited", "data_benefit": "Talktime", "description": "Talktime value of ₹7.47", "tags": "Top-up"},
        {"operator": "Jio", "category": "Top-up", "amount": 20, "validity": "Unlimited", "data_benefit": "Talktime", "description": "Talktime value of ₹14.95", "tags": "Top-up"},
        {"operator": "Jio", "category": "Top-up", "amount": 50, "validity": "Unlimited", "data_benefit": "Talktime", "description": "Talktime value of ₹39.37", "tags": "Top-up"},
        {"operator": "Jio", "category": "Top-up", "amount": 100, "validity": "Unlimited", "data_benefit": "Talktime", "description": "Talktime value of ₹81.75", "tags": "Top-up"},

        # JioBharat / JioPhone
        {"operator": "Jio", "category": "JioPhone", "amount": 75, "validity": "23 Days", "data_benefit": "0.1 GB/Day + 200 MB", "description": "JioPhone exclusive. Unlimited calls, 50 SMS/day.", "tags": "JioPhone"},
        {"operator": "Jio", "category": "JioPhone", "amount": 91, "validity": "28 Days", "data_benefit": "0.1 GB/Day + 200 MB", "description": "JioPhone exclusive. Unlimited calls, 50 SMS/day.", "tags": "JioPhone"},
        {"operator": "Jio", "category": "JioPhone", "amount": 125, "validity": "23 Days", "data_benefit": "0.5 GB/Day", "description": "JioPhone exclusive. Unlimited calls, 300 SMS/28 days.", "tags": "JioPhone"},
        {"operator": "Jio", "category": "JioPhone", "amount": 152, "validity": "28 Days", "data_benefit": "0.5 GB/Day", "description": "JioPhone exclusive. Unlimited calls.", "tags": "JioPhone"},
        {"operator": "Jio", "category": "JioPhone", "amount": 186, "validity": "28 Days", "data_benefit": "1 GB/Day", "description": "JioPhone exclusive. Unlimited calls, 100 SMS/day.", "tags": "JioPhone"},
        {"operator": "Jio", "category": "JioPhone", "amount": 223, "validity": "28 Days", "data_benefit": "2 GB/Day", "description": "JioPhone exclusive. Unlimited calls, 100 SMS/day.", "tags": "JioPhone"},
        {"operator": "Jio", "category": "JioPhone", "amount": 895, "validity": "336 Days", "data_benefit": "2 GB / 28 Days", "description": "JioPhone Annual plan.", "tags": "JioPhone, Annual"},

        # Jio ISD / Roaming
        {"operator": "Jio", "category": "Roaming/ISD", "amount": 39, "validity": "7 Days", "data_benefit": "N/A", "description": "Global ISD pack. ISD calls starting at 50p/min.", "tags": "ISD"},
        {"operator": "Jio", "category": "Roaming/ISD", "amount": 399, "validity": "28 Days", "data_benefit": "N/A", "description": "International Roaming without data (Calls & SMS).", "tags": "Roaming"},
        {"operator": "Jio", "category": "Roaming/ISD", "amount": 499, "validity": "1 Day", "data_benefit": "250 MB", "description": "Global Roaming 1-Day Pack. 100 Mins calls, 100 SMS.", "tags": "Roaming, Global"},
        {"operator": "Jio", "category": "Roaming/ISD", "amount": 575, "validity": "1 Day", "data_benefit": "250 MB", "description": "Value Pack Roaming (Selected 22 Countries).", "tags": "Roaming"},
        {"operator": "Jio", "category": "Roaming/ISD", "amount": 1101, "validity": "28 Days", "data_benefit": "N/A", "description": "IR Usage value ₹933.05 for pay-as-you-go.", "tags": "Roaming"},
        {"operator": "Jio", "category": "Roaming/ISD", "amount": 1102, "validity": "28 Days", "data_benefit": "N/A", "description": "IR Usage value ₹933.90 plus WiFi Calling.", "tags": "Roaming"},
        {"operator": "Jio", "category": "Roaming/ISD", "amount": 2799, "validity": "7 Days", "data_benefit": "2 GB", "description": "Global Roaming 7-Day Pack. 100 Mins/Day.", "tags": "Roaming"},
        {"operator": "Jio", "category": "Roaming/ISD", "amount": 2875, "validity": "7 Days", "data_benefit": "250 MB/Day", "description": "Value Pack Roaming 7-Days.", "tags": "Roaming"},
        {"operator": "Jio", "category": "Roaming/ISD", "amount": 2998, "validity": "21 Days", "data_benefit": "5 GB", "description": "Global Roaming 21-Day Pack.", "tags": "Roaming"},


        # ==========================================
        # AIRTEL
        # ==========================================
        # Airtel Unlimited
        {"operator": "Airtel", "category": "Unlimited", "amount": 155, "validity": "24 Days", "data_benefit": "1 GB Total", "description": "Unlimited calls, 300 SMS total. Apollo 24/7.", "tags": "Affordable"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 179, "validity": "28 Days", "data_benefit": "2 GB Total", "description": "Unlimited calls, 300 SMS total. Wynk Music.", "tags": "Affordable"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 199, "validity": "30 Days", "data_benefit": "3 GB Total", "description": "Unlimited calls, 300 SMS total.", "tags": "Affordable"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 209, "validity": "21 Days", "data_benefit": "1 GB/Day", "description": "Unlimited calls, 100 SMS/day.", "tags": "1GB/Day"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 239, "validity": "24 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day. True 5G.", "tags": "5G Plus"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 265, "validity": "28 Days", "data_benefit": "1 GB/Day", "description": "Unlimited calls, 100 SMS/day.", "tags": "1GB/Day"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 296, "validity": "30 Days", "data_benefit": "25 GB Total", "description": "No daily limit, 25GB bulk data, unlimited calls. True 5G.", "tags": "5G Plus, Bulk Data"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 299, "validity": "28 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day, Wynk Music.", "tags": "5G Plus, Popular"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 319, "validity": "1 Month", "data_benefit": "2 GB/Day", "description": "Calendar month validity, unlimited calls.", "tags": "5G Plus, 1 Month"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 359, "validity": "28 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day, Airtel Xstream Play.", "tags": "5G Plus, Xstream"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 399, "validity": "28 Days", "data_benefit": "2.5 GB/Day", "description": "Unlimited calls, Disney+ Hotstar (3 Months).", "tags": "5G Plus, Hotstar"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 455, "validity": "84 Days", "data_benefit": "6 GB Total", "description": "Unlimited calls, 900 SMS. Long validity affordable.", "tags": "Affordable"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 479, "validity": "56 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day.", "tags": "5G Plus"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 499, "validity": "28 Days", "data_benefit": "3 GB/Day", "description": "Heavy data, Disney+ Hotstar Mobile.", "tags": "5G Plus, Heavy Data"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 509, "validity": "1 Month", "data_benefit": "60 GB Total", "description": "Bulk 60GB for a calendar month. Apollo 24/7.", "tags": "5G Plus, Bulk Data"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 519, "validity": "60 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day.", "tags": "5G Plus"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 549, "validity": "56 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, Xstream Premium.", "tags": "5G Plus"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 699, "validity": "56 Days", "data_benefit": "3 GB/Day", "description": "Heavy data + Amazon Prime Membership.", "tags": "5G Plus, Prime"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 719, "validity": "84 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day. RewardsMini.", "tags": "5G Plus, Popular"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 779, "validity": "90 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day.", "tags": "5G Plus"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 839, "validity": "84 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day + Xstream Play.", "tags": "5G Plus, Xstream"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 869, "validity": "84 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls + Disney+ Hotstar (3 Months).", "tags": "5G Plus, Hotstar"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 999, "validity": "84 Days", "data_benefit": "2.5 GB/Day", "description": "Amazon Prime (84 Days) + Xstream.", "tags": "5G Plus, Prime"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 1499, "validity": "84 Days", "data_benefit": "3 GB/Day", "description": "Netflix Basic + Apollo 24/7.", "tags": "5G Plus, Netflix"},
        
        # Airtel Annual
        {"operator": "Airtel", "category": "Annual", "amount": 1799, "validity": "365 Days", "data_benefit": "24 GB Total", "description": "Affordable annual pack, unlimited calls, 3600 SMS.", "tags": "Affordable, Annual"},
        {"operator": "Airtel", "category": "Annual", "amount": 2999, "validity": "365 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, Apollo 24/7, Wynk Music.", "tags": "5G Plus, Annual"},
        {"operator": "Airtel", "category": "Annual", "amount": 3359, "validity": "365 Days", "data_benefit": "2.5 GB/Day", "description": "Disney+ Hotstar Annual + Apollo 24/7.", "tags": "5G Plus, Hotstar, Annual"},

        # Airtel Data Add-ons & Top-ups
        {"operator": "Airtel", "category": "Data Add-on", "amount": 19, "validity": "1 Day", "data_benefit": "1 GB", "description": "Quick 1GB data booster.", "tags": "Data Booster"},
        {"operator": "Airtel", "category": "Data Add-on", "amount": 29, "validity": "1 Day", "data_benefit": "2 GB", "description": "Quick 2GB data booster.", "tags": "Data Booster"},
        {"operator": "Airtel", "category": "Data Add-on", "amount": 49, "validity": "1 Day", "data_benefit": "Unlimited Data", "description": "Unlimited 4G/5G data for 1 day (FUP 20GB).", "tags": "Data Booster, Unlimited"},
        {"operator": "Airtel", "category": "Data Add-on", "amount": 58, "validity": "Active Plan", "data_benefit": "3 GB", "description": "3GB data booster.", "tags": "Data Booster"},
        {"operator": "Airtel", "category": "Data Add-on", "amount": 65, "validity": "Active Plan", "data_benefit": "4 GB", "description": "4GB data booster.", "tags": "Data Booster"},
        {"operator": "Airtel", "category": "Data Add-on", "amount": 98, "validity": "Active Plan", "data_benefit": "5 GB", "description": "5GB + Wynk Music Premium.", "tags": "Data Booster"},
        {"operator": "Airtel", "category": "Data Add-on", "amount": 148, "validity": "Active Plan", "data_benefit": "15 GB", "description": "15GB + Xstream Play (28 Days).", "tags": "Data Booster, Xstream"},
        {"operator": "Airtel", "category": "Data Add-on", "amount": 149, "validity": "Active Plan", "data_benefit": "1 GB", "description": "Xstream Play Premium (28 Days).", "tags": "Xstream"},
        {"operator": "Airtel", "category": "Data Add-on", "amount": 181, "validity": "30 Days", "data_benefit": "1 GB/Day", "description": "1GB/Day extra data for 30 days.", "tags": "Data Booster"},
        {"operator": "Airtel", "category": "Data Add-on", "amount": 211, "validity": "30 Days", "data_benefit": "1 GB/Day", "description": "1GB/Day extra data + Wynk Premium.", "tags": "Data Booster"},
        {"operator": "Airtel", "category": "Data Add-on", "amount": 301, "validity": "Active Plan", "data_benefit": "50 GB", "description": "Heavy 50GB bulk data booster + Wynk Music.", "tags": "Data Booster, Bulk Data"},
        {"operator": "Airtel", "category": "Top-up", "amount": 10, "validity": "Unlimited", "data_benefit": "Talktime", "description": "Talktime ₹7.47", "tags": "Top-up"},
        {"operator": "Airtel", "category": "Top-up", "amount": 20, "validity": "Unlimited", "data_benefit": "Talktime", "description": "Talktime ₹14.95", "tags": "Top-up"},
        {"operator": "Airtel", "category": "Top-up", "amount": 100, "validity": "Unlimited", "data_benefit": "Talktime", "description": "Talktime ₹81.75", "tags": "Top-up"},
        {"operator": "Airtel", "category": "Top-up", "amount": 1000, "validity": "Unlimited", "data_benefit": "Talktime", "description": "Talktime ₹844.46", "tags": "Top-up"},


        # ==========================================
        # VODAFONE IDEA (VI)
        # ==========================================
        # VI Hero Unlimited
        {"operator": "VI", "category": "Unlimited", "amount": 155, "validity": "24 Days", "data_benefit": "1 GB Total", "description": "Unlimited calls, 300 SMS. Basic smart recharge.", "tags": "Affordable"},
        {"operator": "VI", "category": "Unlimited", "amount": 179, "validity": "28 Days", "data_benefit": "2 GB Total", "description": "Unlimited calls, 300 SMS.", "tags": "Affordable"},
        {"operator": "VI", "category": "Unlimited", "amount": 199, "validity": "28 Days", "data_benefit": "1 GB/Day", "description": "Unlimited calls, 100 SMS/day (No Hero benefits).", "tags": "1GB/Day"},
        {"operator": "VI", "category": "Unlimited", "amount": 239, "validity": "24 Days", "data_benefit": "1 GB/Day", "description": "Unlimited calls. Basic data.", "tags": "1GB/Day"},
        {"operator": "VI", "category": "Unlimited", "amount": 299, "validity": "28 Days", "data_benefit": "1.5 GB/Day", "description": "Hero Unlimited (Binge All Night, Weekend Rollover).", "tags": "Hero Unlimited, Popular"},
        {"operator": "VI", "category": "Unlimited", "amount": 349, "validity": "28 Days", "data_benefit": "1.5 GB/Day", "description": "Hero Unlimited + 5GB Extra Data.", "tags": "Hero Unlimited"},
        {"operator": "VI", "category": "Unlimited", "amount": 359, "validity": "28 Days", "data_benefit": "3 GB/Day", "description": "Hero Unlimited + Heavy Data.", "tags": "Hero Unlimited, Heavy Data"},
        {"operator": "VI", "category": "Unlimited", "amount": 399, "validity": "28 Days", "data_benefit": "2.5 GB/Day", "description": "Hero Unlimited + 5GB Extra Data.", "tags": "Hero Unlimited"},
        {"operator": "VI", "category": "Unlimited", "amount": 409, "validity": "28 Days", "data_benefit": "3.5 GB/Day", "description": "Hero Unlimited. Max daily data.", "tags": "Hero Unlimited, Heavy Data"},
        {"operator": "VI", "category": "Unlimited", "amount": 479, "validity": "56 Days", "data_benefit": "1.5 GB/Day", "description": "Hero Unlimited. Long validity.", "tags": "Hero Unlimited"},
        {"operator": "VI", "category": "Unlimited", "amount": 539, "validity": "56 Days", "data_benefit": "2 GB/Day", "description": "Hero Unlimited.", "tags": "Hero Unlimited"},
        {"operator": "VI", "category": "Unlimited", "amount": 599, "validity": "70 Days", "data_benefit": "1.5 GB/Day", "description": "Hero Unlimited. 70 days validity.", "tags": "Hero Unlimited"},
        {"operator": "VI", "category": "Unlimited", "amount": 719, "validity": "84 Days", "data_benefit": "1.5 GB/Day", "description": "Hero Unlimited. Popular quarterly plan.", "tags": "Hero Unlimited, Popular"},
        {"operator": "VI", "category": "Unlimited", "amount": 839, "validity": "84 Days", "data_benefit": "2 GB/Day", "description": "Hero Unlimited + 5GB Extra.", "tags": "Hero Unlimited"},
        {"operator": "VI", "category": "Unlimited", "amount": 901, "validity": "70 Days", "data_benefit": "3 GB/Day", "description": "Hero Unlimited + Disney+ Hotstar.", "tags": "Hero Unlimited, Hotstar"},
        {"operator": "VI", "category": "Unlimited", "amount": 1449, "validity": "180 Days", "data_benefit": "1.5 GB/Day", "description": "Hero Unlimited. Half-yearly pack.", "tags": "Hero Unlimited, Half-Year"},

        # VI Annual
        {"operator": "VI", "category": "Annual", "amount": 1799, "validity": "365 Days", "data_benefit": "24 GB Total", "description": "Voice-centric annual plan, 3600 SMS.", "tags": "Affordable, Annual"},
        {"operator": "VI", "category": "Annual", "amount": 2899, "validity": "365 Days", "data_benefit": "1.5 GB/Day", "description": "Hero Unlimited Annual.", "tags": "Hero Unlimited, Annual"},
        {"operator": "VI", "category": "Annual", "amount": 3099, "validity": "365 Days", "data_benefit": "2 GB/Day", "description": "Hero Unlimited Annual.", "tags": "Hero Unlimited, Annual"},
        {"operator": "VI", "category": "Annual", "amount": 3199, "validity": "365 Days", "data_benefit": "2 GB/Day", "description": "Hero Unlimited + Amazon Prime Video Annual.", "tags": "Hero Unlimited, Prime, Annual"},

        # VI Combo / Smart Recharges
        {"operator": "VI", "category": "Validity", "amount": 99, "validity": "28 Days", "data_benefit": "200 MB", "description": "Full talktime ₹99, calls at 1p/sec.", "tags": "Smart Recharge"},
        {"operator": "VI", "category": "Validity", "amount": 109, "validity": "30 Days", "data_benefit": "200 MB", "description": "Full talktime ₹109, calls at 1p/sec.", "tags": "Smart Recharge"},
        {"operator": "VI", "category": "Validity", "amount": 111, "validity": "31 Days", "data_benefit": "200 MB", "description": "Full talktime ₹111, calls at 1p/sec.", "tags": "Smart Recharge"},

        # VI Entertainment
        {"operator": "VI", "category": "Entertainment", "amount": 151, "validity": "30 Days", "data_benefit": "8 GB", "description": "Disney+ Hotstar (3 Months) + 8GB Data.", "tags": "Hotstar, Data Booster"},
        {"operator": "VI", "category": "Entertainment", "amount": 169, "validity": "30 Days", "data_benefit": "8 GB", "description": "Sony LIV Premium + 8GB Data.", "tags": "SonyLIV, Data Booster"},
        {"operator": "VI", "category": "Entertainment", "amount": 499, "validity": "28 Days", "data_benefit": "3 GB/Day", "description": "Hero Unlimited + Disney+ Hotstar.", "tags": "Hero Unlimited, Hotstar"},
        {"operator": "VI", "category": "Entertainment", "amount": 601, "validity": "28 Days", "data_benefit": "3 GB/Day", "description": "Hero Unlimited + Amazon Prime.", "tags": "Hero Unlimited, Prime"},
        {"operator": "VI", "category": "Entertainment", "amount": 903, "validity": "90 Days", "data_benefit": "2 GB/Day", "description": "Hero Unlimited + Sony LIV.", "tags": "Hero Unlimited, SonyLIV"},
        {"operator": "VI", "category": "Entertainment", "amount": 1066, "validity": "84 Days", "data_benefit": "2 GB/Day", "description": "Hero Unlimited + Disney+ Hotstar (1 Year).", "tags": "Hero Unlimited, Hotstar"},
        {"operator": "VI", "category": "Entertainment", "amount": 408, "validity": "28 Days", "data_benefit": "2.5 GB/Day", "description": "Hero Unlimited + SunNXT.", "tags": "Hero Unlimited, SunNXT"},

        # VI Data Add-ons
        {"operator": "VI", "category": "Data Add-on", "amount": 17, "validity": "1 Day", "data_benefit": "Unlimited Data", "description": "Unlimited night data (12AM-6AM).", "tags": "Data Booster, Night Data"},
        {"operator": "VI", "category": "Data Add-on", "amount": 19, "validity": "1 Day", "data_benefit": "1 GB", "description": "Quick 1GB data booster.", "tags": "Data Booster"},
        {"operator": "VI", "category": "Data Add-on", "amount": 29, "validity": "2 Days", "data_benefit": "2 GB", "description": "Quick 2GB data booster.", "tags": "Data Booster"},
        {"operator": "VI", "category": "Data Add-on", "amount": 39, "validity": "7 Days", "data_benefit": "3 GB", "description": "3GB data booster.", "tags": "Data Booster"},
        {"operator": "VI", "category": "Data Add-on", "amount": 49, "validity": "1 Day", "data_benefit": "20 GB", "description": "Heavy 20GB daily booster.", "tags": "Data Booster, Bulk"},
        {"operator": "VI", "category": "Data Add-on", "amount": 58, "validity": "28 Days", "data_benefit": "3 GB", "description": "3GB data booster, long validity.", "tags": "Data Booster"},
        {"operator": "VI", "category": "Data Add-on", "amount": 75, "validity": "7 Days", "data_benefit": "6 GB", "description": "Week-long data booster + Extra 1.5GB.", "tags": "Data Booster"},
        {"operator": "VI", "category": "Data Add-on", "amount": 82, "validity": "14 Days", "data_benefit": "4 GB", "description": "SonyLIV Mobile + 4GB.", "tags": "Data Booster, SonyLIV"},
        {"operator": "VI", "category": "Data Add-on", "amount": 98, "validity": "21 Days", "data_benefit": "9 GB", "description": "9GB data booster.", "tags": "Data Booster"},
        {"operator": "VI", "category": "Data Add-on", "amount": 118, "validity": "28 Days", "data_benefit": "12 GB", "description": "Month-long data booster.", "tags": "Data Booster"},
        {"operator": "VI", "category": "Data Add-on", "amount": 298, "validity": "28 Days", "data_benefit": "50 GB", "description": "Work From Home bulk data.", "tags": "Data Booster, WFH"},
        {"operator": "VI", "category": "Data Add-on", "amount": 418, "validity": "56 Days", "data_benefit": "100 GB", "description": "Work From Home massive bulk data.", "tags": "Data Booster, WFH"},


        # ==========================================
        # BSNL
        # ==========================================
        # BSNL Unlimited / STV
        {"operator": "BSNL", "category": "Unlimited", "amount": 18, "validity": "2 Days", "data_benefit": "1 GB/Day", "description": "Unlimited calls, 100 SMS/day.", "tags": "Micro Pack"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 29, "validity": "5 Days", "data_benefit": "1 GB Total", "description": "Unlimited calls.", "tags": "Micro Pack"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 87, "validity": "14 Days", "data_benefit": "1 GB/Day", "description": "Unlimited calls, 100 SMS/day + Hardy Games.", "tags": "Affordable"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 97, "validity": "15 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls + Lokdhun.", "tags": "Affordable"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 99, "validity": "18 Days", "data_benefit": "N/A", "description": "Unlimited voice calls only (No Data/SMS).", "tags": "Voice Only"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 105, "validity": "18 Days", "data_benefit": "2 GB Total", "description": "Unlimited calls, 100 SMS/day.", "tags": "Affordable"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 118, "validity": "20 Days", "data_benefit": "0.5 GB/Day", "description": "Unlimited calls.", "tags": "Affordable"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 147, "validity": "30 Days", "data_benefit": "10 GB Total", "description": "Unlimited calls + BSNL Tunes.", "tags": "Affordable"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 153, "validity": "26 Days", "data_benefit": "1 GB/Day", "description": "Unlimited calls, 100 SMS/day. PRBT.", "tags": "Popular"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 184, "validity": "28 Days", "data_benefit": "1 GB/Day", "description": "Unlimited calls + Lystn Podcast.", "tags": "Popular"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 185, "validity": "28 Days", "data_benefit": "1 GB/Day", "description": "Unlimited calls + Challenges Arena.", "tags": "Popular"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 186, "validity": "28 Days", "data_benefit": "1 GB/Day", "description": "Unlimited calls + Hardy Games.", "tags": "Popular"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 187, "validity": "28 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day. BSNL Tunes.", "tags": "Popular"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 197, "validity": "70 Days", "data_benefit": "2 GB/Day (for 15 Days)", "description": "Validity extension. Unlimited calls & data for first 15 days.", "tags": "Validity Extension"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 199, "validity": "30 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day.", "tags": "Popular"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 201, "validity": "90 Days", "data_benefit": "N/A", "description": "Validity extension (GP II users). 300 Mins calls.", "tags": "Validity Extension"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 228, "validity": "1 Month", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day + Challenges Arena.", "tags": "Popular"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 239, "validity": "1 Month", "data_benefit": "2 GB/Day", "description": "Unlimited calls + Gaming.", "tags": "Popular"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 247, "validity": "30 Days", "data_benefit": "50 GB Total", "description": "Bulk data, unlimited calls.", "tags": "Bulk Data"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 269, "validity": "28 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls + Eros Now, Lokdhun.", "tags": "Entertainment"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 298, "validity": "52 Days", "data_benefit": "1 GB/Day", "description": "Unlimited calls, 100 SMS/day.", "tags": "Long Validity"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 299, "validity": "30 Days", "data_benefit": "3 GB/Day", "description": "Heavy data, unlimited calls.", "tags": "Heavy Data"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 319, "validity": "65 Days", "data_benefit": "10 GB Total", "description": "Unlimited calls.", "tags": "Voice Focused"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 347, "validity": "54 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day.", "tags": "Popular"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 397, "validity": "150 Days", "data_benefit": "2 GB/Day (for 30 Days)", "description": "Unlimited calls & 2GB/day for first 30 days, then validity extension.", "tags": "Validity Extension"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 399, "validity": "70 Days", "data_benefit": "1 GB/Day", "description": "Unlimited calls + Lokdhun.", "tags": "Popular"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 439, "validity": "90 Days", "data_benefit": "N/A", "description": "Unlimited voice calls only (No Data).", "tags": "Voice Only"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 485, "validity": "82 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day.", "tags": "Popular"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 499, "validity": "75 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls + Cricket PRBT.", "tags": "Popular"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 599, "validity": "84 Days", "data_benefit": "3 GB/Day", "description": "Unlimited calls, 100 SMS/day. Night free data (12AM-5AM).", "tags": "Heavy Data, Night Free"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 666, "validity": "105 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day. BSNL Tunes.", "tags": "Long Validity"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 699, "validity": "130 Days", "data_benefit": "0.5 GB/Day", "description": "Unlimited calls.", "tags": "Long Validity"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 769, "validity": "84 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls + Eros Now, Lokdhun.", "tags": "Entertainment"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 797, "validity": "300 Days", "data_benefit": "2 GB/Day (for 60 Days)", "description": "Plan extension pack with 60 days of freebies.", "tags": "Validity Extension"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 997, "validity": "160 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls + PRBT for 2 months.", "tags": "Long Validity"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 999, "validity": "200 Days", "data_benefit": "N/A", "description": "Unlimited voice calls only (No Data) for 200 days.", "tags": "Voice Only"},
        
        # BSNL Annual
        {"operator": "BSNL", "category": "Annual", "amount": 1198, "validity": "365 Days", "data_benefit": "3 GB/Month", "description": "Basic annual plan. 3GB data & 300 Mins/Month.", "tags": "Affordable, Annual"},
        {"operator": "BSNL", "category": "Annual", "amount": 1499, "validity": "336 Days", "data_benefit": "24 GB Total", "description": "Unlimited calls, 100 SMS/day.", "tags": "Annual"},
        {"operator": "BSNL", "category": "Annual", "amount": 1999, "validity": "365 Days", "data_benefit": "600 GB Total", "description": "Unlimited calls, 100 SMS/day. Bulk data for a year.", "tags": "Annual, Bulk Data"},
        {"operator": "BSNL", "category": "Annual", "amount": 2399, "validity": "395 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day. 13 Months validity.", "tags": "Annual, Hero Plan"},
        {"operator": "BSNL", "category": "Annual", "amount": 2999, "validity": "365 Days", "data_benefit": "3 GB/Day", "description": "Unlimited calls, heavy daily data.", "tags": "Annual, Heavy Data"},

        # BSNL Data Add-ons & Top-up
        {"operator": "BSNL", "category": "Top-up", "amount": 10, "validity": "Unlimited", "data_benefit": "Talktime", "description": "Talktime value of ₹7.47", "tags": "Top-up"},
        {"operator": "BSNL", "category": "Top-up", "amount": 20, "validity": "Unlimited", "data_benefit": "Talktime", "description": "Talktime value of ₹14.95", "tags": "Top-up"},
        {"operator": "BSNL", "category": "Top-up", "amount": 50, "validity": "Unlimited", "data_benefit": "Talktime", "description": "Talktime value of ₹39.37", "tags": "Top-up"},
        {"operator": "BSNL", "category": "Top-up", "amount": 100, "validity": "Unlimited", "data_benefit": "Talktime", "description": "Talktime value of ₹81.75", "tags": "Top-up"},
        {"operator": "BSNL", "category": "Data Add-on", "amount": 16, "validity": "1 Day", "data_benefit": "2 GB", "description": "1 Day data booster.", "tags": "Data Booster"},
        {"operator": "BSNL", "category": "Data Add-on", "amount": 22, "validity": "Active Plan", "data_benefit": "N/A", "description": "Local/STD calls at 30p/min.", "tags": "Rate Cutter"},
        {"operator": "BSNL", "category": "Data Add-on", "amount": 56, "validity": "10 Days", "data_benefit": "10 GB", "description": "10GB data + Zing.", "tags": "Data Booster"},
        {"operator": "BSNL", "category": "Data Add-on", "amount": 94, "validity": "30 Days", "data_benefit": "3 GB", "description": "Data voucher.", "tags": "Data Booster"},
        {"operator": "BSNL", "category": "Data Add-on", "amount": 98, "validity": "22 Days", "data_benefit": "2 GB/Day", "description": "Data voucher.", "tags": "Data Booster"},
        {"operator": "BSNL", "category": "Data Add-on", "amount": 151, "validity": "28 Days", "data_benefit": "40 GB", "description": "Massive data booster for WFH.", "tags": "Data Booster, WFH"},
        {"operator": "BSNL", "category": "Data Add-on", "amount": 198, "validity": "40 Days", "data_benefit": "2 GB/Day", "description": "Data voucher + Gaming.", "tags": "Data Booster"},
        {"operator": "BSNL", "category": "Data Add-on", "amount": 251, "validity": "28 Days", "data_benefit": "70 GB", "description": "Massive data booster + Zing.", "tags": "Data Booster, WFH"},
        {"operator": "BSNL", "category": "Data Add-on", "amount": 398, "validity": "30 Days", "data_benefit": "120 GB", "description": "Extreme data booster for heavy users.", "tags": "Data Booster, WFH"},
    ]

    db = next(get_db())
    for plan_data in plans:
        db_plan = RechargePlan(**plan_data)
        db.add(db_plan)
        
    db.commit()
    print(f"Successfully seeded {len(plans)} highly detailed 2026 telecom plans with categories and tags!")

if __name__ == "__main__":
    asyncio.run(seed_plans())
