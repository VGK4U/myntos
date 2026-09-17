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
        # ==========================================
        # JIO PLANS (Extensive List - 2026 Verified)
        # ==========================================
        {"operator": "Jio", "category": "Value", "amount": 189, "validity": "28 Days", "data_benefit": "2 GB Total", "description": "Unlimited calls, 300 SMS total.", "tags": "Affordable"},
        {"operator": "Jio", "category": "Unlimited", "amount": 249, "validity": "28 Days", "data_benefit": "1 GB/Day", "description": "Unlimited calls, 100 SMS/day.", "tags": ""},
        {"operator": "Jio", "category": "Unlimited", "amount": 299, "validity": "28 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day. JioTV, JioCinema.", "tags": "Popular"},
        {"operator": "Jio", "category": "Unlimited", "amount": 349, "validity": "28 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day. True Unlimited 5G Data.", "tags": "True 5G"},
        {"operator": "Jio", "category": "Unlimited", "amount": 399, "validity": "28 Days", "data_benefit": "2.5 GB/Day", "description": "Unlimited calls, 100 SMS/day. True Unlimited 5G Data.", "tags": "True 5G"},
        {"operator": "Jio", "category": "Unlimited", "amount": 449, "validity": "28 Days", "data_benefit": "3 GB/Day", "description": "Unlimited calls, 100 SMS/day. True Unlimited 5G Data.", "tags": "True 5G, Heavy Data"},
        {"operator": "Jio", "category": "Unlimited", "amount": 579, "validity": "56 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day.", "tags": ""},
        {"operator": "Jio", "category": "Unlimited", "amount": 629, "validity": "56 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day. Includes True Unlimited 5G Data.", "tags": "True 5G"},
        {"operator": "Jio", "category": "Unlimited", "amount": 799, "validity": "84 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day. Long term pack.", "tags": "Popular"},
        {"operator": "Jio", "category": "Unlimited", "amount": 859, "validity": "84 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day. Includes True Unlimited 5G Data.", "tags": "True 5G"},
        {"operator": "Jio", "category": "Unlimited", "amount": 1199, "validity": "84 Days", "data_benefit": "3 GB/Day", "description": "Unlimited calls, True Unlimited 5G Data.", "tags": "True 5G, Heavy Data"},
        {"operator": "Jio", "category": "Annual", "amount": 3599, "validity": "365 Days", "data_benefit": "2.5 GB/Day", "description": "Unlimited calls, 100 SMS/day. True Unlimited 5G Data.", "tags": "Annual, True 5G"},
        {"operator": "Jio", "category": "Data Add-on", "amount": 19, "validity": "Base Plan", "data_benefit": "1 GB Total", "description": "Data booster pack.", "tags": "Booster"},
        {"operator": "Jio", "category": "Data Add-on", "amount": 29, "validity": "Base Plan", "data_benefit": "2 GB Total", "description": "Data booster pack.", "tags": "Booster"},
        {"operator": "Jio", "category": "Data Add-on", "amount": 69, "validity": "Base Plan", "data_benefit": "6 GB Total", "description": "Data booster pack.", "tags": "Booster"},

        # ==========================================
        # AIRTEL PLANS (Extensive List - 2026 Verified)
        # ==========================================
        {"operator": "Airtel", "category": "Value", "amount": 199, "validity": "28 Days", "data_benefit": "2 GB Total", "description": "Unlimited calls, 100 SMS/day.", "tags": "Affordable"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 299, "validity": "28 Days", "data_benefit": "1 GB/Day", "description": "Unlimited calls, 100 SMS/day.", "tags": ""},
        {"operator": "Airtel", "category": "Unlimited", "amount": 349, "validity": "28 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day. Xstream Play.", "tags": "Popular"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 409, "validity": "28 Days", "data_benefit": "2.5 GB/Day", "description": "Unlimited calls, 100 SMS/day. Unlimited 5G Data.", "tags": "5G"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 449, "validity": "28 Days", "data_benefit": "3 GB/Day", "description": "Unlimited calls, 100 SMS/day. Unlimited 5G Data.", "tags": "5G, Heavy Data"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 579, "validity": "56 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day.", "tags": ""},
        {"operator": "Airtel", "category": "Unlimited", "amount": 649, "validity": "56 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day. Unlimited 5G Data.", "tags": "5G"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 859, "validity": "84 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day.", "tags": "Popular"},
        {"operator": "Airtel", "category": "Unlimited", "amount": 979, "validity": "84 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day. Unlimited 5G Data.", "tags": "5G"},
        {"operator": "Airtel", "category": "Annual", "amount": 3599, "validity": "365 Days", "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day. Unlimited 5G Data.", "tags": "Annual, 5G"},
        {"operator": "Airtel", "category": "Data Add-on", "amount": 22, "validity": "1 Day", "data_benefit": "1 GB Total", "description": "Data booster pack.", "tags": "Booster"},
        {"operator": "Airtel", "category": "Data Add-on", "amount": 33, "validity": "1 Day", "data_benefit": "2 GB Total", "description": "Data booster pack.", "tags": "Booster"},

        # ==========================================
        # VI (VODAFONE IDEA) PLANS (Extensive List - 2026 Verified)
        # ==========================================
        {"operator": "Vi", "category": "Value", "amount": 199, "validity": "28 Days", "data_benefit": "2 GB Total", "description": "Unlimited calls, 300 SMS total.", "tags": "Affordable"},
        {"operator": "Vi", "category": "Unlimited", "amount": 299, "validity": "28 Days", "data_benefit": "1 GB/Day", "description": "Unlimited calls, 100 SMS/day.", "tags": ""},
        {"operator": "Vi", "category": "Unlimited", "amount": 349, "validity": "28 Days", "data_benefit": "1.5 GB/Day", "description": "Hero Unlimited: Binge All Night (12AM-6AM), Weekend Data Rollover.", "tags": "Hero Unlimited"},
        {"operator": "Vi", "category": "Unlimited", "amount": 409, "validity": "28 Days", "data_benefit": "2.5 GB/Day", "description": "Hero Unlimited: Binge All Night, Weekend Data Rollover.", "tags": "Hero"},
        {"operator": "Vi", "category": "Unlimited", "amount": 449, "validity": "28 Days", "data_benefit": "3 GB/Day", "description": "Hero Unlimited: Binge All Night, Weekend Data Rollover.", "tags": "Hero, Heavy Data"},
        {"operator": "Vi", "category": "Unlimited", "amount": 579, "validity": "56 Days", "data_benefit": "1.5 GB/Day", "description": "Hero Unlimited: Binge All Night, Weekend Data Rollover.", "tags": "Hero"},
        {"operator": "Vi", "category": "Unlimited", "amount": 649, "validity": "56 Days", "data_benefit": "2 GB/Day", "description": "Hero Unlimited: Binge All Night, Weekend Data Rollover.", "tags": "Hero"},
        {"operator": "Vi", "category": "Unlimited", "amount": 859, "validity": "84 Days", "data_benefit": "1.5 GB/Day", "description": "Hero Unlimited: Binge All Night, Weekend Data Rollover.", "tags": "Hero Unlimited"},
        {"operator": "Vi", "category": "Unlimited", "amount": 979, "validity": "84 Days", "data_benefit": "2 GB/Day", "description": "Hero Unlimited: Binge All Night, Weekend Data Rollover.", "tags": "Hero"},
        {"operator": "Vi", "category": "Annual", "amount": 3499, "validity": "365 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, Hero Unlimited Benefits.", "tags": "Annual, Hero"},
        {"operator": "Vi", "category": "Data Add-on", "amount": 22, "validity": "1 Day", "data_benefit": "1 GB Total", "description": "Data booster pack.", "tags": "Booster"},
        {"operator": "Vi", "category": "Data Add-on", "amount": 33, "validity": "1 Day", "data_benefit": "2 GB Total", "description": "Data booster pack.", "tags": "Booster"},

        # ==========================================
        # BSNL PLANS (Extensive List - 2026 Verified)
        # ==========================================
        {"operator": "BSNL", "category": "Value", "amount": 107, "validity": "35 Days", "data_benefit": "3 GB Total", "description": "200 min voice calls, BSNL Tunes.", "tags": "Validity"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 153, "validity": "26 Days", "data_benefit": "1 GB/Day", "description": "Unlimited voice calls, 100 SMS/day. 4G network.", "tags": "Affordable"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 199, "validity": "30 Days", "data_benefit": "2 GB/Day", "description": "Unlimited voice calls, 100 SMS/day.", "tags": "Value"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 239, "validity": "28 Days", "data_benefit": "2 GB/Day", "description": "Unlimited voice calls, 100 SMS/day.", "tags": "Popular"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 398, "validity": "30 Days", "data_benefit": "120 GB Total", "description": "Unlimited voice calls, 100 SMS/day. High Data Volume.", "tags": "Heavy Data"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 599, "validity": "84 Days", "data_benefit": "3 GB/Day", "description": "Unlimited voice calls, 100 SMS/day. Free BSNL Tunes.", "tags": "Popular"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 666, "validity": "105 Days", "data_benefit": "2 GB/Day", "description": "Unlimited voice calls, 100 SMS/day.", "tags": "Long Term"},
        {"operator": "BSNL", "category": "Unlimited", "amount": 997, "validity": "160 Days", "data_benefit": "2 GB/Day", "description": "Unlimited voice calls, 100 SMS/day.", "tags": "Long Term"},
        {"operator": "BSNL", "category": "Annual", "amount": 1499, "validity": "336 Days", "data_benefit": "24 GB Total", "description": "Unlimited voice calls, 100 SMS/day. Extended validity plan.", "tags": "Annual"},
        {"operator": "BSNL", "category": "Annual", "amount": 1999, "validity": "365 Days", "data_benefit": "600 GB Total", "description": "Unlimited voice calls, 100 SMS/day. Massive data pool.", "tags": "Annual, Heavy Data"},
        {"operator": "BSNL", "category": "Annual", "amount": 2399, "validity": "395 Days", "data_benefit": "2 GB/Day", "description": "Unlimited voice calls, 100 SMS/day. Eros Now entertainment.", "tags": "Annual"}
    ]

    # Insert into DB
    db = next(get_db())
    try:
        for plan_data in plans:
            db.add(RechargePlan(**plan_data))
        db.commit()
        print(f"Successfully seeded {len(plans)} updated telecom plans.")
    except Exception as e:
        print(f"Error seeding plans: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(seed_plans())
