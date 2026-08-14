import os
from dotenv import load_dotenv

load_dotenv(".env")
from app.core.database import SessionLocal
from app.services.ai_marketing_pro_service import AIMarketingProService
import logging

logging.basicConfig(level=logging.INFO)

def test_service():
    db = SessionLocal()
    service = AIMarketingProService(db=db, company_id=1, staff_id=1)
    
    # We will patch generate_content temporarily to see exactly what's being sent and received
    original_generate = service.client.models.generate_content
    
    def hooked_generate(*args, **kwargs):
        print(f"\n--- GENERATE_CONTENT CALL ---")
        print(f"Contents length: {len(kwargs.get('contents', []))}")
        resp = original_generate(*args, **kwargs)
        print(f"Response function calls: {resp.function_calls}")
        print(f"Response text: {repr(resp.text)}")
        return resp
        
    service.client.models.generate_content = hooked_generate
    
    print("\nTesting: Analyze my active campaigns...")
    result1 = service.process_chat("Analyze my active campaigns and tell me if I should optimize the budget.")
    print(f"Result 1: {result1}")

if __name__ == "__main__":
    test_service()
