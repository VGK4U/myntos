"""
Initialize EV Models in Database
Run this script to populate initial Royal EV models
"""

import sys
import os

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models import Base, EVModel

def init_ev_models():
    """Initialize 6 Royal EV models with discount configuration"""
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    
    try:
        # Check if models already exist
        existing_count = db.query(EVModel).count()
        if existing_count > 0:
            print(f"⚠️  EV models already exist ({existing_count} models). Skipping initialization.")
            return
        
        # Define the 6 EV models (Pre-approved by RVZ for initial setup)
        ev_models = [
            # 100% Benefit Models (max ₹15k/₹7.5k based on package)
            {
                "model_name": "Royal EV K9",
                "manufacturer": "Royal EV",
                "base_price": 80000.0,
                "max_discount_percentage": 100.0,
                "coupon_benefit_enabled": True,
                "description": "100% benefit on coupon (max ₹15,000 for Platinum, ₹7,500 for Diamond)",
                "is_active": True,
                "approval_status": "Approved",
                "display_order": 1
            },
            {
                "model_name": "Royal EV Trango",
                "manufacturer": "Royal EV",
                "base_price": 90000.0,
                "max_discount_percentage": 100.0,
                "coupon_benefit_enabled": True,
                "description": "100% benefit on coupon (max ₹15,000 for Platinum, ₹7,500 for Diamond)",
                "is_active": True,
                "approval_status": "Approved",
                "display_order": 2
            },
            
            # 5% Invoice Discount Models
            {
                "model_name": "Royal Vegas",
                "manufacturer": "Royal EV",
                "base_price": 70000.0,
                "max_discount_percentage": 5.0,
                "coupon_benefit_enabled": True,
                "description": "5% discount on invoice value",
                "is_active": True,
                "approval_status": "Approved",
                "display_order": 3
            },
            {
                "model_name": "Royal Maze",
                "manufacturer": "Royal EV",
                "base_price": 75000.0,
                "max_discount_percentage": 5.0,
                "coupon_benefit_enabled": True,
                "description": "5% discount on invoice value",
                "is_active": True,
                "approval_status": "Approved",
                "display_order": 4
            },
            {
                "model_name": "Royal K2",
                "manufacturer": "Royal EV",
                "base_price": 85000.0,
                "max_discount_percentage": 5.0,
                "coupon_benefit_enabled": True,
                "description": "5% discount on invoice value",
                "is_active": True,
                "approval_status": "Approved",
                "display_order": 5
            },
            {
                "model_name": "Royal Sirius",
                "manufacturer": "Royal EV",
                "base_price": 95000.0,
                "max_discount_percentage": 5.0,
                "coupon_benefit_enabled": True,
                "description": "5% discount on invoice value",
                "is_active": True,
                "approval_status": "Approved",
                "display_order": 6
            }
        ]
        
        # Insert models
        for model_data in ev_models:
            ev_model = EVModel(**model_data)
            db.add(ev_model)
        
        db.commit()
        print(f"✅ Successfully initialized {len(ev_models)} EV models!")
        
        # Display summary
        print("\n📊 EV Models Summary:")
        print("\n100% Coupon Benefit Models:")
        for model in db.query(EVModel).filter(EVModel.max_discount_percentage == 100.0).all():
            print(f"  • {model.model_name} - ₹{model.base_price:,.0f}")
        
        print("\n5% Invoice Discount Models:")
        for model in db.query(EVModel).filter(EVModel.max_discount_percentage == 5.0).all():
            print(f"  • {model.model_name} - ₹{model.base_price:,.0f}")
        
    except Exception as e:
        print(f"❌ Error initializing EV models: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Initializing EV Models...")
    init_ev_models()
    print("\n✨ Initialization complete!")
