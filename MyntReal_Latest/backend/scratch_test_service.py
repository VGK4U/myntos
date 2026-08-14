import os
import asyncio
from dotenv import load_dotenv

load_dotenv(".env")

from app.core.database import SessionLocal
from app.services.ai_marketing_pro_service import AIMarketingProService

def test_service():
    db = SessionLocal()
    service = AIMarketingProService(db=db, company_id=1, staff_id=1)
    
    print("Testing: Analyze my active campaigns...")
    result1 = service.process_chat("Analyze my active campaigns and tell me if I should optimize the budget.")
    print(f"Result 1: {result1}")
    
    print("\nTesting: who is the president of usa?")
    result2 = service.process_chat("who is the president of usa ?")
    print(f"Result 2: {result2}")

if __name__ == "__main__":
    test_service()
