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
    
    plans = [
        # ==========================================
        # JIO PLANS (JULY 2024 UPDATED)
        # ==========================================
        {
            "operator": "Jio", "category": "Unlimited", "amount": 189, "validity": "28 Days",
            "data_benefit": "2 GB Total", "description": "Unlimited calls, 300 SMS total. Affordable base pack.",
            "tags": "Affordable"
        },
        {
            "operator": "Jio", "category": "Unlimited", "amount": 299, "validity": "28 Days",
            "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day. JioTV, JioCinema.",
            "tags": "Popular"
        },
        {
            "operator": "Jio", "category": "Unlimited", "amount": 349, "validity": "28 Days",
            "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day. Includes True Unlimited 5G Data.",
            "tags": "True 5G"
        },
        {
            "operator": "Jio", "category": "Unlimited", "amount": 449, "validity": "28 Days",
            "data_benefit": "3 GB/Day", "description": "Unlimited calls, 100 SMS/day. Includes True Unlimited 5G Data.",
            "tags": "True 5G, Heavy Data"
        },
        {
            "operator": "Jio", "category": "Unlimited", "amount": 579, "validity": "56 Days",
            "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day.",
            "tags": "Popular"
        },
        {
            "operator": "Jio", "category": "Unlimited", "amount": 629, "validity": "56 Days",
            "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day. Includes True Unlimited 5G Data.",
            "tags": "True 5G"
        },
        {
            "operator": "Jio", "category": "Unlimited", "amount": 799, "validity": "84 Days",
            "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day. Long term pack.",
            "tags": "Popular"
        },
        {
            "operator": "Jio", "category": "Unlimited", "amount": 859, "validity": "84 Days",
            "data_benefit": "2 GB/Day", "description": "Unlimited calls. Includes True Unlimited 5G Data.",
            "tags": "True 5G"
        },
        {
            "operator": "Jio", "category": "Unlimited", "amount": 1199, "validity": "84 Days",
            "data_benefit": "3 GB/Day", "description": "Unlimited calls, True Unlimited 5G Data.",
            "tags": "True 5G, Heavy Data"
        },
        {
            "operator": "Jio", "category": "Annual", "amount": 3599, "validity": "365 Days",
            "data_benefit": "2.5 GB/Day", "description": "Unlimited calls, 100 SMS/day. True 5G.",
            "tags": "Annual, True 5G"
        },
        {
            "operator": "Jio", "category": "Data Add-on", "amount": 19, "validity": "Base Plan",
            "data_benefit": "1 GB Total", "description": "Data booster pack. Active till base plan validity.",
            "tags": "Booster"
        },
        {
            "operator": "Jio", "category": "Data Add-on", "amount": 29, "validity": "Base Plan",
            "data_benefit": "2 GB Total", "description": "Data booster pack. Active till base plan validity.",
            "tags": "Booster"
        },
        
        # ==========================================
        # AIRTEL PLANS (JULY 2024 UPDATED)
        # ==========================================
        {
            "operator": "Airtel", "category": "Unlimited", "amount": 199, "validity": "28 Days",
            "data_benefit": "2 GB Total", "description": "Unlimited calls, 100 SMS/day. Affordable plan.",
            "tags": "Affordable"
        },
        {
            "operator": "Airtel", "category": "Unlimited", "amount": 299, "validity": "28 Days",
            "data_benefit": "1 GB/Day", "description": "Unlimited calls, 100 SMS/day.",
            "tags": "1GB/Day"
        },
        {
            "operator": "Airtel", "category": "Unlimited", "amount": 349, "validity": "28 Days",
            "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day. Xstream Play.",
            "tags": "Popular"
        },
        {
            "operator": "Airtel", "category": "Unlimited", "amount": 409, "validity": "28 Days",
            "data_benefit": "2.5 GB/Day", "description": "Unlimited calls, 100 SMS/day. Unlimited 5G.",
            "tags": "5G, Heavy Data"
        },
        {
            "operator": "Airtel", "category": "Unlimited", "amount": 579, "validity": "56 Days",
            "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day.",
            "tags": "Popular"
        },
        {
            "operator": "Airtel", "category": "Unlimited", "amount": 649, "validity": "56 Days",
            "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day. Unlimited 5G.",
            "tags": "5G"
        },
        {
            "operator": "Airtel", "category": "Unlimited", "amount": 859, "validity": "84 Days",
            "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, 100 SMS/day.",
            "tags": "Popular"
        },
        {
            "operator": "Airtel", "category": "Unlimited", "amount": 979, "validity": "84 Days",
            "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day. Unlimited 5G.",
            "tags": "5G"
        },
        {
            "operator": "Airtel", "category": "Annual", "amount": 3599, "validity": "365 Days",
            "data_benefit": "2 GB/Day", "description": "Unlimited calls, 100 SMS/day. Unlimited 5G.",
            "tags": "Annual, 5G"
        },
        {
            "operator": "Airtel", "category": "Data Add-on", "amount": 22, "validity": "1 Day",
            "data_benefit": "1 GB Total", "description": "Data booster pack.",
            "tags": "Booster"
        },

        # ==========================================
        # VI (VODAFONE IDEA) PLANS (JULY 2024 UPDATED)
        # ==========================================
        {
            "operator": "Vi", "category": "Unlimited", "amount": 199, "validity": "28 Days",
            "data_benefit": "2 GB Total", "description": "Unlimited calls, 300 SMS total.",
            "tags": "Affordable"
        },
        {
            "operator": "Vi", "category": "Unlimited", "amount": 299, "validity": "28 Days",
            "data_benefit": "1 GB/Day", "description": "Unlimited calls, 100 SMS/day.",
            "tags": "1GB/Day"
        },
        {
            "operator": "Vi", "category": "Unlimited", "amount": 349, "validity": "28 Days",
            "data_benefit": "1.5 GB/Day", "description": "Hero Unlimited: Binge All Night, Weekend Data Rollover.",
            "tags": "Hero Unlimited"
        },
        {
            "operator": "Vi", "category": "Unlimited", "amount": 579, "validity": "56 Days",
            "data_benefit": "1.5 GB/Day", "description": "Hero Unlimited: Binge All Night, Weekend Data Rollover.",
            "tags": "Hero Unlimited"
        },
        {
            "operator": "Vi", "category": "Unlimited", "amount": 859, "validity": "84 Days",
            "data_benefit": "1.5 GB/Day", "description": "Hero Unlimited: Binge All Night, Weekend Data Rollover.",
            "tags": "Hero Unlimited"
        },
        {
            "operator": "Vi", "category": "Annual", "amount": 3499, "validity": "365 Days",
            "data_benefit": "1.5 GB/Day", "description": "Unlimited calls, Hero Unlimited Benefits.",
            "tags": "Annual, Hero"
        },
        {
            "operator": "Vi", "category": "Data Add-on", "amount": 22, "validity": "1 Day",
            "data_benefit": "1 GB Total", "description": "Data booster pack.",
            "tags": "Booster"
        },

        # ==========================================
        # BSNL PLANS (NO MAJOR HIKE, REMAINS BUDGET)
        # ==========================================
        {
            "operator": "BSNL", "category": "Unlimited", "amount": 153, "validity": "26 Days",
            "data_benefit": "1 GB/Day", "description": "Unlimited voice calls, 100 SMS/day.",
            "tags": "Affordable"
        },
        {
            "operator": "BSNL", "category": "Unlimited", "amount": 199, "validity": "30 Days",
            "data_benefit": "2 GB/Day", "description": "Unlimited voice calls, 100 SMS/day.",
            "tags": "Value"
        },
        {
            "operator": "BSNL", "category": "Unlimited", "amount": 398, "validity": "30 Days",
            "data_benefit": "120 GB Total", "description": "Unlimited voice calls, 100 SMS/day. Truly unlimited data without speed restriction up to 120GB.",
            "tags": "Heavy Data"
        },
        {
            "operator": "BSNL", "category": "Unlimited", "amount": 599, "validity": "84 Days",
            "data_benefit": "3 GB/Day", "description": "Unlimited voice calls, 100 SMS/day. Free BSNL Tunes.",
            "tags": "Popular"
        },
        {
            "operator": "BSNL", "category": "Annual", "amount": 2399, "validity": "395 Days",
            "data_benefit": "2 GB/Day", "description": "Unlimited voice calls, 100 SMS/day. Eros Now entertainment.",
            "tags": "Annual"
        }
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
