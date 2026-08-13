import json
import logging
from typing import Dict, Any, List
import google.generativeai as genai
from app.core.config import settings
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.services.meta_live_creation_service import execute_first_live_meta_campaign_creation
from app.services.meta_insights_analytics_service import get_meta_ads_dashboard_kpis

logger = logging.getLogger(__name__)

# Configure Gemini
# We use try/except or safe get in case the env isn't loaded properly in some environments
api_key = getattr(settings, 'GEMINI_API_KEY', None) or os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
if api_key:
    genai.configure(api_key=api_key)
else:
    logger.warning("GEMINI_API_KEY / GOOGLE_API_KEY not found in settings/env!")

# Define the Marketing Agent persona
SYSTEM_PROMPT = """
You are an elite, highly professional AI Digital Marketing Expert working internally.
Your goal is to help the user create, manage, and optimize Meta (Facebook & Instagram) ad campaigns.
You are directly connected to the Meta Graph API.
When a user wants to create an ad, you MUST ask for:
1. Campaign Name
2. Target Location (e.g., Andhra Pradesh)
3. Daily Budget in INR
4. Product/Service (e.g., Solar, Real Estate)
5. Headline and Primary Text

Do NOT guess the budget. Always confirm before creating.
Once they confirm, use the `create_meta_campaign` tool to launch it.
"""

def create_meta_campaign(company_id: int, campaign_name: str, daily_budget_inr: float, target_location: str, product_name: str, headline: str, primary_text: str, description: str = "") -> str:
    """Tool for the AI to create a real Meta Campaign."""
    try:
        from app.core.database import SessionLocal
        db = SessionLocal()
        
        lead_form_id = "123456789" # Mock or fetch from DB
        
        result = execute_first_live_meta_campaign_creation(
            db=db,
            company_id=company_id,
            staff_id=1, # Defaulting to admin
            campaign_name=campaign_name,
            daily_budget_inr=daily_budget_inr,
            target_location=target_location,
            product_name=product_name,
            headline=headline,
            primary_text=primary_text,
            description=description,
            lead_form_id=lead_form_id
        )
        db.close()
        return json.dumps(result)
    except Exception as e:
        return f"Error creating campaign: {str(e)}"

def get_campaign_insights(company_id: int, date_preset: str = 'last_30d') -> str:
    """Tool for the AI to fetch performance metrics of campaigns."""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        results = get_meta_ads_dashboard_kpis(db, company_id)
        db.close()
        return json.dumps(results)
    except Exception as e:
        db.close()
        return f"Error fetching insights: {str(e)}"

marketing_tools = [create_meta_campaign, get_campaign_insights]

class AIMarketingAgentService:
    def __init__(self, db: Session, company_id: int, staff_id: int):
        self.db = db
        self.company_id = company_id
        self.staff_id = staff_id
        
        # Define a fallback list of models to prevent rate limiting or temporary outages
        # Prioritize the most advanced (3.x and 2.x) series first, falling back to 1.x
        self.model_names = [
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-2.0-flash",
            "gemini-1.5-flash-8b"
        ]

    def process_message(self, message: str) -> str:
        """Process a user message and return the AI's response with model fallback."""
        context_injected_message = f"[System Context: Company ID is {self.company_id}. User says:]\n{message}"
        last_error = None
        
        for model_name in self.model_names:
            try:
                # Initialize the specific model
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=SYSTEM_PROMPT,
                    tools=marketing_tools
                )
                
                chat = model.start_chat(enable_automatic_function_calling=True)
                response = chat.send_message(context_injected_message)
                
                # If successful, return the text
                return response.text
                
            except Exception as e:
                logger.warning(f"Model {model_name} failed: {str(e)}. Falling back to next model...")
                last_error = str(e)
                continue # Try the next model in the list
                
        # If all models failed
        logger.error(f"All Gemini models failed. Last error: {last_error}")
        return f"I encountered an error connecting to my core reasoning engines. Please check the logs. Last Error: {last_error}"

