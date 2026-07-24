import asyncio
from app.core.database import get_db, engine
from app.models.recharge import RechargePlan
from app.models.base import Base

async def seed_plans():
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS recharge_plans CASCADE"))
    RechargePlan.__table__.create(bind=engine, checkfirst=True)

    plans = [
        # ---------------------------------------------
        # JIO PLANS (2026 Updated Pricing)
        # ---------------------------------------------
        # Unlimited Plans
        {"operator": "Jio", "category": "Unlimited", "amount": 299, "validity": "28 Days", "data_benefit": "1.5 GB/Day", "description": "Truly unlimited calls, 100 SMS/day, JioTV, JioCinema.", "tags": "True 5G"},
        {"operator": "Jio", "category": "Unlimited", "amount": 349, "validity": "28 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day, JioTV, JioCinema.", "tags": "True 5G, Popular"},
        {"operator": "Jio", "category": "Unlimited", "amount": 399, "validity": "28 Days", "data_benefit": "2.5 GB/Day", "description": "Unlimited calls, 100 SMS/day, Jio apps.", "tags": "True 5G"},
        {"operator": "Jio", "category": "Unlimited", "amount": 579, "validity": "56 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day, JioTV.", "tags": "True 5G"},
        {"operator": "Jio", "category": "Unlimited", "amount": 629, "validity": "56 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day, Jio apps.", "tags": "True 5G"},
        {"operator": "Jio", "category": "Unlimited", "amount": 799, "validity": "84 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day.", "tags": "True 5G, Best Value"},
        {"operator": "Jio", "category": "Unlimited", "amount": 859, "validity": "84 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day, Jio apps.", "tags": "True 5G"},
        {"operator": "Jio", "category": "Unlimited", "amount": 1099, "validity": "84 Days", "data_benefit": "3 GB/Day", "description": "Heavy data plan, unlimited calls, 100 SMS/day.", "tags": "True 5G, Heavy Data"},
        {"operator": "Jio", "category": "Unlimited", "amount": 189, "validity": "28 Days", "data_benefit": "2 GB Total", "description": "Unlimited calls, 300 SMS total. Affordable base pack.", "tags": "Affordable"},
        {"operator": "Jio", "category": "Unlimited", "amount": 479, "validity": "84 Days", "data_benefit": "6 GB Total", "description": "Unlimited calls, 1000 SMS total. Long validity affordable pack.", "tags": "Affordable"},
        
        # Annual Plans
        {"operator": "Jio", "category": "Annual", "amount": 3599, "validity": "365 Days", "data_benefit": "2.5 GB/Day", "description": "Year-long peace of mind with heavy daily data.", "tags": "True 5G, Hero Plan"},
        {"operator": "Jio", "category": "Annual", "amount": 2999, "validity": "365 Days", "data_benefit": "2 GB/Day", "description": "Standard annual plan with 5G.", "tags": "True 5G"},
        {"operator": "Jio", "category": "Annual", "amount": 1899, "validity": "336 Days", "data_benefit": "24 GB Total", "description": "Affordable annual pack for voice-first users.", "tags": "Affordable, Annual"},
        
        # Entertainment Plans
        {"operator": "Jio", "category": "Entertainment", "amount": 1049, "validity": "84 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls + Sony LIV & ZEE5 Premium.", "tags": "True 5G, SonyLIV, ZEE5"},
        {"operator": "Jio", "category": "Entertainment", "amount": 1198, "validity": "84 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls + Prime Video Lite & Disney+ Hotstar.", "tags": "True 5G, Prime Video, Hotstar"},
        {"operator": "Jio", "category": "Entertainment", "amount": 398, "validity": "28 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls + Sony LIV & ZEE5 Premium.", "tags": "True 5G, OTT Combo"},
        {"operator": "Jio", "category": "Entertainment", "amount": 898, "validity": "90 Days", "data_benefit": "2 GB/Day", "description": "JioTV Premium (14 OTT apps bundled).", "tags": "True 5G, 14 OTTs"},
        
        # Data Add-ons
        {"operator": "Jio", "category": "Data Add-on", "amount": 19, "validity": "Active Plan", "data_benefit": "1 GB", "description": "Instant 1GB high-speed data booster.", "tags": "Data Booster"},
        {"operator": "Jio", "category": "Data Add-on", "amount": 29, "validity": "Active Plan", "data_benefit": "2 GB", "description": "Instant 2GB high-speed data booster.", "tags": "Data Booster"},
        {"operator": "Jio", "category": "Data Add-on", "amount": 69, "validity": "Active Plan", "data_benefit": "6 GB", "description": "High-volume data booster.", "tags": "Data Booster"},
        {"operator": "Jio", "category": "Data Add-on", "amount": 139, "validity": "Active Plan", "data_benefit": "12 GB", "description": "Massive data booster for heavy usage.", "tags": "Data Booster"},
        {"operator": "Jio", "category": "Data Add-on", "amount": 51, "validity": "Active Plan", "data_benefit": "Unlimited 5G", "description": "True 5G Upgrade voucher for 4G plans.", "tags": "True 5G"},

        # ---------------------------------------------
        # AIRTEL PLANS (2026 Updated Pricing)
        # ---------------------------------------------
        # Unlimited Plans
        {"operator": "Airtel", "category": "Unlimited", "amount": 299, "validity": "28 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day, Wynk Music.", "tags": "5G Plus"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 349, "validity": "28 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day, Wynk Music.", "tags": "5G Plus, Popular"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 409, "validity": "28 Days", "data_benefit": "2.5 GB/Day", "description": "Unlimited calls, 100 SMS/day, Xstream Play.", "tags": "5G Plus"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 579, "validity": "56 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day, Apollo 24|7.", "tags": "5G Plus"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 649, "validity": "56 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day.", "tags": "5G Plus"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 859, "validity": "84 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day. Long validity.", "tags": "5G Plus, Best Value"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 979, "validity": "84 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day, Xstream Play.", "tags": "5G Plus"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 199, "validity": "28 Days", "data_benefit": "2 GB Total", "description": "Affordable calling pack.", "tags": "Affordable"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 509, "validity": "84 Days", "data_benefit": "6 GB Total", "description": "Affordable calling pack for long validity.", "tags": "Affordable"},
        
        # Annual Plans
        {"operator": "Airtel", "category": "Annual", "amount": 3599, "validity": "365 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day, Apollo 24|7 Circle.", "tags": "5G Plus, Annual"},
        {"operator": "Airtel", "category": "Annual", "amount": 1999, "validity": "365 Days", "data_benefit": "24 GB Total", "description": "Voice-centric annual plan.", "tags": "Affordable, Annual"},
        
        # Entertainment Plans
        {"operator": "Airtel", "category": "Entertainment", "amount": 899, "validity": "84 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls + Amazon Prime Membership (84 Days).", "tags": "5G Plus, Prime Video"},
        {"operator": "Airtel", "category": "Entertainment", "amount": 1049, "validity": "84 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls + Disney+ Hotstar Mobile.", "tags": "5G Plus, Hotstar"},
        {"operator": "Airtel", "category": "Entertainment", "amount": 499, "validity": "28 Days", "data_benefit": "3 GB/Day", "description": "Unlimited calls + Disney+ Hotstar.", "tags": "5G Plus, Hotstar"},
        {"operator": "Airtel", "category": "Entertainment", "amount": 839, "validity": "84 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls + Airtel Xstream Play.", "tags": "5G Plus, Xstream"},
        
        # Data Add-ons
        {"operator": "Airtel", "category": "Data Add-on", "amount": 22, "validity": "1 Day", "data_benefit": "1 GB", "description": "1 Day data booster.", "tags": "Data Booster"},
        {"operator": "Airtel", "category": "Data Add-on", "amount": 33, "validity": "1 Day", "data_benefit": "2 GB", "description": "1 Day 2GB data booster.", "tags": "Data Booster"},
        {"operator": "Airtel", "category": "Data Add-on", "amount": 77, "validity": "Active Plan", "data_benefit": "5 GB", "description": "Base validity data booster.", "tags": "Data Booster"},
        {"operator": "Airtel", "category": "Data Add-on", "amount": 121, "validity": "Active Plan", "data_benefit": "6 GB", "description": "Large data booster.", "tags": "Data Booster"},
        {"operator": "Airtel", "category": "Data Add-on", "amount": 149, "validity": "Active Plan", "data_benefit": "15 GB", "description": "Massive data booster + Xstream.", "tags": "Data Booster, Xstream"},

        # ---------------------------------------------
        # VODAFONE IDEA (VI) PLANS (2026 Updated Pricing)
        # ---------------------------------------------
        # Unlimited Plans
        {"operator": "VI", "category": "Unlimited", "amount": 299, "validity": "28 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day, Vi Movies & TV.", "tags": ""},
        {"operator": "VI", "category": "Unlimited", "amount": 349, "validity": "28 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, Hero Unlimited (Binge All Night + Rollover).", "tags": "Hero Unlimited"},
        {"operator": "VI", "category": "Unlimited", "amount": 409, "validity": "28 Days", "data_benefit": "2.5 GB/Day", "description": "Unlimited calls, Hero Unlimited.", "tags": "Hero Unlimited"},
        {"operator": "VI", "category": "Unlimited", "amount": 579, "validity": "56 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, Vi Movies & TV.", "tags": ""},
        {"operator": "VI", "category": "Unlimited", "amount": 649, "validity": "56 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, Hero Unlimited.", "tags": "Hero Unlimited"},
        {"operator": "VI", "category": "Unlimited", "amount": 859, "validity": "84 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, Hero Unlimited.", "tags": "Hero Unlimited"},
        {"operator": "VI", "category": "Unlimited", "amount": 979, "validity": "84 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, Hero Unlimited.", "tags": "Hero Unlimited, Popular"},
        {"operator": "VI", "category": "Unlimited", "amount": 199, "validity": "28 Days", "data_benefit": "2 GB Total", "description": "Affordable calling pack.", "tags": "Affordable"},
        {"operator": "VI", "category": "Unlimited", "amount": 509, "validity": "84 Days", "data_benefit": "6 GB Total", "description": "Long validity basic pack.", "tags": "Affordable"},
        
        # Annual Plans
        {"operator": "VI", "category": "Annual", "amount": 3499, "validity": "365 Days", "data_benefit": "2 GB/Day", "description": "Hero Unlimited (Binge All Night, Weekend Data Rollover, Data Delights).", "tags": "Hero Unlimited, Annual"},
        {"operator": "VI", "category": "Annual", "amount": 1999, "validity": "365 Days", "data_benefit": "24 GB Total", "description": "Voice-centric annual plan.", "tags": "Affordable, Annual"},
        
        # Entertainment Plans
        {"operator": "VI", "category": "Entertainment", "amount": 499, "validity": "28 Days", "data_benefit": "3 GB/Day", "description": "Hero Unlimited + Disney+ Hotstar.", "tags": "Hero Unlimited, Hotstar"},
        {"operator": "VI", "category": "Entertainment", "amount": 903, "validity": "90 Days", "data_benefit": "2 GB/Day", "description": "Hero Unlimited + Amazon Prime.", "tags": "Hero Unlimited, Prime Video"},
        {"operator": "VI", "category": "Entertainment", "amount": 1049, "validity": "84 Days", "data_benefit": "2 GB/Day", "description": "Hero Unlimited + Disney+ Hotstar.", "tags": "Hero Unlimited, Hotstar"},
        {"operator": "VI", "category": "Entertainment", "amount": 408, "validity": "28 Days", "data_benefit": "2.5 GB/Day", "description": "Hero Unlimited + SunNXT.", "tags": "Hero Unlimited, SunNXT"},

        # Data Add-ons
        {"operator": "VI", "category": "Data Add-on", "amount": 22, "validity": "1 Day", "data_benefit": "1 GB", "description": "Quick data booster.", "tags": "Data Booster"},
        {"operator": "VI", "category": "Data Add-on", "amount": 33, "validity": "1 Day", "data_benefit": "2 GB", "description": "Quick 2GB data booster.", "tags": "Data Booster"},
        {"operator": "VI", "category": "Data Add-on", "amount": 75, "validity": "7 Days", "data_benefit": "6 GB", "description": "Week-long data booster.", "tags": "Data Booster"},
        {"operator": "VI", "category": "Data Add-on", "amount": 118, "validity": "28 Days", "data_benefit": "12 GB", "description": "Month-long data booster.", "tags": "Data Booster"},

        # ---------------------------------------------
        # BSNL PLANS (2026 Updated Pricing)
        # ---------------------------------------------
        # Unlimited Plans
        {"operator": "BSNL", "category": "Unlimited", "amount": 153, "validity": "26 Days", "data_benefit": "1 GB/Day", "description": "Unlimited calls, 100 SMS/day. PRBT.", "tags": "Affordable"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 199, "validity": "30 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day.", "tags": "Popular"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 228, "validity": "1 Month", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day + Challenges Arena.", "tags": ""},
        {"operator": "BSNL", "category": "Unlimited", "amount": 347, "validity": "54 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day.", "tags": ""},
        {"operator": "BSNL", "category": "Unlimited", "amount": 397, "validity": "150 Days", "data_benefit": "2 GB/Day (for 30 Days)", "description": "Unlimited calls & 2GB/day for first 30 days, then validity extension.", "tags": "Validity Extension"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 599, "validity": "84 Days", "data_benefit": "3 GB/Day", "description": "Unlimited calls, 100 SMS/day. Night free data.", "tags": "Heavy Data, Night Free"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 666, "validity": "105 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day. BSNL Tunes.", "tags": "Long Validity"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 797, "validity": "300 Days", "data_benefit": "2 GB/Day (for 60 Days)", "description": "Plan extension pack with 60 days of freebies.", "tags": "Validity Extension"},
        
        # Annual Plans
        {"operator": "BSNL", "category": "Annual", "amount": 1999, "validity": "365 Days", "data_benefit": "600 GB Total", "description": "Unlimited calls, 100 SMS/day. Bulk data for a year.", "tags": "Annual"},
        {"operator": "BSNL", "category": "Annual", "amount": 2999, "validity": "365 Days", "data_benefit": "3 GB/Day", "description": "Unlimited calls, heavy daily data.", "tags": "Annual, Heavy Data"},
        
        # Top-ups & Data Add-ons
        {"operator": "BSNL", "category": "Top-up", "amount": 10, "validity": "Unlimited", "data_benefit": "Talktime", "description": "Talktime value of ₹7.47", "tags": "Top-up"},
        {"operator": "BSNL", "category": "Top-up", "amount": 50, "validity": "Unlimited", "data_benefit": "Talktime", "description": "Talktime value of ₹39.37", "tags": "Top-up"},
        {"operator": "BSNL", "category": "Top-up", "amount": 100, "validity": "Unlimited", "data_benefit": "Talktime", "description": "Talktime value of ₹81.75", "tags": "Top-up"},
        {"operator": "BSNL", "category": "Data Add-on", "amount": 16, "validity": "1 Day", "data_benefit": "2 GB", "description": "1 Day data booster.", "tags": "Data Booster"},
        {"operator": "BSNL", "category": "Data Add-on", "amount": 94, "validity": "30 Days", "data_benefit": "3 GB", "description": "Data voucher.", "tags": "Data Booster"},
        {"operator": "BSNL", "category": "Data Add-on", "amount": 151, "validity": "28 Days", "data_benefit": "40 GB", "description": "Massive data booster for WFH.", "tags": "Data Booster"},
        {"operator": "BSNL", "category": "Data Add-on", "amount": 251, "validity": "28 Days", "data_benefit": "70 GB", "description": "Massive data booster + Zing.", "tags": "Data Booster"},
    ]

    db = next(get_db())
    for plan_data in plans:
        db_plan = RechargePlan(**plan_data)
        db.add(db_plan)
        
    db.commit()
    print(f"Successfully seeded {len(plans)} highly detailed 2026 telecom plans with categories and tags!")

if __name__ == "__main__":
    asyncio.run(seed_plans())
