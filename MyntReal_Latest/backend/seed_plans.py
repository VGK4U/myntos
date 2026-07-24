import sys
import os

# Add the project root to the python path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal, engine
from app.models.base import Base
from app.models.recharge import RechargePlan

def seed():
    # Ensure tables are created
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Check if plans already exist
    existing_plans = db.query(RechargePlan).count()
    if existing_plans > 0:
        print(f"Database already has {existing_plans} plans. Clearing them to reseed...")
        db.query(RechargePlan).delete()
        db.commit()

    plans = [
        # Jio Plans
        {"operator": "RELIANCE - JIO", "circle": "All India", "amount": 299, "validity": "28 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited Calls + 1.5 GB/Day Data + 100 SMS/Day"},
        {"operator": "RELIANCE - JIO", "circle": "All India", "amount": 666, "validity": "84 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited Calls + 1.5 GB/Day Data + 100 SMS/Day"},
        {"operator": "RELIANCE - JIO", "circle": "All India", "amount": 719, "validity": "84 Days", "data_benefit": "2 GB/Day", "description": "Unlimited Calls + 2 GB/Day Data + 100 SMS/Day"},
        {"operator": "RELIANCE - JIO", "circle": "All India", "amount": 239, "validity": "28 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited Calls + 1.5 GB/Day Data + 100 SMS/Day"},
        {"operator": "RELIANCE - JIO", "circle": "All India", "amount": 149, "validity": "20 Days", "data_benefit": "1 GB/Day", "description": "Unlimited Calls + 1 GB/Day Data + 100 SMS/Day"},

        # Airtel Plans
        {"operator": "Airtel", "circle": "All India", "amount": 299, "validity": "28 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited Calls + 1.5 GB/Day Data + 100 SMS/Day"},
        {"operator": "Airtel", "circle": "All India", "amount": 479, "validity": "56 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited Calls + 1.5 GB/Day Data + 100 SMS/Day"},
        {"operator": "Airtel", "circle": "All India", "amount": 719, "validity": "84 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited Calls + 1.5 GB/Day Data + 100 SMS/Day"},
        {"operator": "Airtel", "circle": "All India", "amount": 399, "validity": "28 Days", "data_benefit": "2.5 GB/Day", "description": "Unlimited Calls + 2.5 GB/Day Data + 100 SMS/Day"},
        {"operator": "Airtel", "circle": "All India", "amount": 155, "validity": "24 Days", "data_benefit": "1 GB Total", "description": "Unlimited Calls + 1 GB Data + 300 SMS"},
        
        # VI (Vodafone Idea) Plans
        {"operator": "Vodafone", "circle": "All India", "amount": 299, "validity": "28 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited Calls + 1.5 GB/Day Data + Binge All Night"},
        {"operator": "Vodafone", "circle": "All India", "amount": 479, "validity": "56 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited Calls + 1.5 GB/Day Data + Binge All Night"},
        {"operator": "Vodafone", "circle": "All India", "amount": 719, "validity": "84 Days", "data_benefit": "1.5 GB/Day", "description": "Unlimited Calls + 1.5 GB/Day Data + Binge All Night"},
        {"operator": "Vodafone", "circle": "All India", "amount": 179, "validity": "28 Days", "data_benefit": "2 GB Total", "description": "Unlimited Calls + 2 GB Data + 300 SMS"},

        # BSNL Plans
        {"operator": "BSNL - TOPUP", "circle": "All India", "amount": 153, "validity": "26 Days", "data_benefit": "1 GB/Day", "description": "Unlimited Calls + 1 GB/Day Data"},
        {"operator": "BSNL - TOPUP", "circle": "All India", "amount": 199, "validity": "30 Days", "data_benefit": "2 GB/Day", "description": "Unlimited Calls + 2 GB/Day Data"},
        {"operator": "BSNL - TOPUP", "circle": "All India", "amount": 398, "validity": "30 Days", "data_benefit": "120 GB Total", "description": "Unlimited Calls + 120 GB Data"},
        {"operator": "BSNL - TOPUP", "circle": "All India", "amount": 599, "validity": "84 Days", "data_benefit": "3 GB/Day", "description": "Unlimited Calls + 3 GB/Day Data + 100 SMS/Day"},
    ]

    for plan_data in plans:
        plan = RechargePlan(**plan_data)
        db.add(plan)
    
    db.commit()
    print(f"Successfully seeded {len(plans)} plans into the database!")

if __name__ == "__main__":
    seed()
