import os
import json
import logging
import requests
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    genai = None
    types = None
    HAS_GENAI = False

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v19.0"

SYSTEM_PROMPT = """
You are a highly capable AI Marketing Agent functioning as a fully autonomous Meta Ads Manager (Model Context Protocol).
You have direct integration with the Meta Graph API.
Your goal is to help users manage, create, and analyze Meta Ads (Facebook & Instagram) entirely through conversation.
You are professional, concise, and proactive. Do not hallucinate data; always use your tools to fetch real data from the Meta Ads account.

# Key Capabilities & Rules
1. You can fetch active campaigns and their performance insights directly from Meta.
2. You can create new campaigns.
3. You can update campaign daily budgets and statuses (PAUSED/ACTIVE).
4. CRITICAL: For any action that spends money or modifies live campaigns (create_meta_campaign, update_campaign_budget, update_campaign_status), YOU MUST FIRST ASK THE USER FOR EXPLICIT PERMISSION before calling the tool. For example: "I am ready to increase the budget to ₹1000. Please confirm if I should proceed."
5. If the user gives permission, proceed to call the tool immediately.
6. When displaying data to the user, format it neatly in Markdown tables or bulleted lists. 
7. Do not mention "tools" or "backend functions" to the user. Just provide the information seamlessly.
"""

get_meta_campaigns_schema = {"function_declarations": [{
    "name": "get_meta_campaigns",
    "description": "Fetches a list of all Meta Ads campaigns with their ID, name, status, and objective.",
    "parameters": {"type": "OBJECT", "properties": {}}
}]}

get_meta_insights_schema = {"function_declarations": [{
    "name": "get_meta_insights",
    "description": "Fetches real-time performance metrics (Spend, Impressions, Clicks) for the ad account or a specific campaign.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "campaign_id": {
                "type": "STRING",
                "description": "Optional. The ID of the campaign to get insights for. If omitted, gets account-level insights."
            },
            "date_preset": {
                "type": "STRING",
                "description": "Date preset, e.g., 'last_30d', 'last_7d', 'today', 'lifetime'. Defaults to 'last_30d'."
            }
        }
    }
}]}

create_meta_campaign_schema = {"function_declarations": [{
    "name": "create_meta_campaign",
    "description": "Creates a new Meta Ads campaign. MUST ask for permission before calling.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "campaign_name": {"type": "STRING", "description": "Name of the campaign."},
            "daily_budget_inr": {"type": "NUMBER", "description": "Daily budget in INR."},
            "objective": {"type": "STRING", "description": "Campaign objective, default 'OUTCOME_LEADS'."}
        },
        "required": ["campaign_name", "daily_budget_inr"]
    }
}]}

update_campaign_status_schema = {"function_declarations": [{
    "name": "update_campaign_status",
    "description": "Pauses or resumes a campaign. MUST ask for permission before calling.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "campaign_id": {"type": "STRING", "description": "The Meta ID of the campaign."},
            "status": {"type": "STRING", "description": "The new status: 'PAUSED' or 'ACTIVE'."}
        },
        "required": ["campaign_id", "status"]
    }
}]}

update_campaign_budget_schema = {"function_declarations": [{
    "name": "update_campaign_budget",
    "description": "Updates the daily budget of a campaign (actually updates the adset budget). MUST ask for permission before calling.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "campaign_id": {"type": "STRING", "description": "The Meta ID of the campaign."},
            "new_daily_budget_inr": {"type": "NUMBER", "description": "The new daily budget in INR."}
        },
        "required": ["campaign_id", "new_daily_budget_inr"]
    }
}]}

class AIMarketingProService:
    def __init__(self, db: Session, company_id: int, staff_id: int):
        self.db = db
        self.company_id = company_id
        self.staff_id = staff_id
        self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        
        # Meta Credentials
        self.meta_token = os.environ.get("META_SYSTEM_USER_TOKEN") or os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")
        self.ad_account_id = os.environ.get("META_AD_ACCOUNT_ID")
        if self.ad_account_id and not self.ad_account_id.startswith('act_'):
            self.ad_account_id = f"act_{self.ad_account_id}"
            
        if HAS_GENAI and self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None
            
        self.candidate_models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"]

    def process_chat(self, user_message: str, history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.client:
            return {
                "response": "AI Marketing Assistant is currently unavailable. Please configure GEMINI_API_KEY or GOOGLE_API_KEY in backend/.env file.",
                "components": None
            }

        if not history:
            history = []

        contents = []
        for msg in history:
            role = 'user' if msg.get('role') == 'user' else 'model'
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg.get('content', ''))]
                )
            )
            
        contents.append(
            types.Content(
                role='user',
                parts=[types.Part.from_text(text=user_message)]
            )
        )
        
        tools = [
            get_meta_campaigns_schema, 
            get_meta_insights_schema, 
            create_meta_campaign_schema, 
            update_campaign_status_schema, 
            update_campaign_budget_schema
        ]

        last_error = None
        for model_name in self.candidate_models:
            try:
                # 1st turn: User message -> Model
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.3,
                        tools=tools
                    )
                )

                # Handle Function Calls recursively until the model returns a text response
                max_turns = 3
                turns = 0
                
                while response.function_calls and turns < max_turns:
                    turns += 1
                    
                    # Add the model's entire response to history (preserves thoughts + all function calls)
                    contents.append(response.candidates[0].content)
                    
                    tool_responses = []
                    for fn in response.function_calls:
                        tool_name = fn.name
                        tool_args = fn.args or {}
                        
                        logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                        
                        tool_result = {}
                        
                        if tool_name == "get_meta_campaigns":
                            tool_result = self._get_meta_campaigns()
                        elif tool_name == "get_meta_insights":
                            tool_result = self._get_meta_insights(tool_args)
                        elif tool_name == "create_meta_campaign":
                            tool_result = self._create_meta_campaign(tool_args)
                        elif tool_name == "update_campaign_status":
                            tool_result = self._update_campaign_status(tool_args)
                        elif tool_name == "update_campaign_budget":
                            tool_result = self._update_campaign_budget(tool_args)
                        else:
                            tool_result = {"error": "Unknown function"}
                            
                        tool_responses.append(
                            types.Part.from_function_response(name=tool_name, response={"result": tool_result})
                        )
                    
                    # Add all tool responses to history as a single user message
                    contents.append(
                        types.Content(
                            role="user",
                            parts=tool_responses
                        )
                    )
                    
                    # Ask model to generate the next response based on the tool result
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.3,
                            tools=tools
                        )
                    )

                return {
                    "response": response.text,
                    "components": None
                }
            except Exception as e:
                err_str = str(e)
                logger.error(f"Error in AIMarketingProService with model {model_name}: {err_str}")
                if any(term in err_str for term in ["PERMISSION_DENIED", "leaked", "404", "no longer available", "not found"]):
                    return {
                        "response": "⚠️ Google Gemini API key needs to be updated. The key configured in .env was flagged/deprecated by Google. Please generate a new API key from Google AI Studio (https://aistudio.google.com/app/apikey) and update GOOGLE_API_KEY in backend/.env.",
                        "components": None
                    }
                last_error = err_str
                continue

        return {
            "response": "⚠️ Google Gemini API key needs to be updated. Please generate a new API key from Google AI Studio (https://aistudio.google.com/app/apikey) and update GOOGLE_API_KEY in backend/.env.",
            "components": None
        }

    def _get_meta_campaigns(self) -> dict:
        if not self.meta_token or not self.ad_account_id:
            return {"error": "Meta Ads Integration credentials (META_SYSTEM_USER_TOKEN / META_AD_ACCOUNT_ID) are missing in .env"}
        url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{self.ad_account_id}/campaigns"
        params = {
            "access_token": self.meta_token,
            "fields": "id,name,status,objective,daily_budget",
            "limit": 50
        }
        try:
            r = requests.get(url, params=params, timeout=15)
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def _get_meta_insights(self, args: dict) -> dict:
        campaign_id = args.get("campaign_id")
        date_preset = args.get("date_preset", "last_30d")
        
        target_id = campaign_id if campaign_id else self.ad_account_id
        url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{target_id}/insights"
        
        params = {
            "access_token": self.meta_token,
            "fields": "spend,impressions,clicks,cpc,cpm,reach",
            "date_preset": date_preset
        }
        try:
            r = requests.get(url, params=params, timeout=15)
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def _create_meta_campaign(self, args: dict) -> dict:
        # Simplified creation logic for the agent mode
        name = args.get("campaign_name", "AI Generated Campaign")
        objective = args.get("objective", "OUTCOME_LEADS")
        
        url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{self.ad_account_id}/campaigns"
        payload = {
            "name": name,
            "objective": objective,
            "status": "PAUSED", # Default to PAUSED for safety
            "special_ad_categories": '["NONE"]',
            "access_token": self.meta_token
        }
        try:
            r = requests.post(url, data=payload, timeout=15)
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def _update_campaign_status(self, args: dict) -> dict:
        campaign_id = args.get("campaign_id")
        status = args.get("status")
        
        if not campaign_id or not status:
            return {"error": "Missing campaign_id or status"}
            
        url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{campaign_id}"
        payload = {
            "status": status,
            "access_token": self.meta_token
        }
        try:
            r = requests.post(url, data=payload, timeout=15)
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def _update_campaign_budget(self, args: dict) -> dict:
        campaign_id = args.get("campaign_id")
        budget = args.get("new_daily_budget_inr")
        
        if not campaign_id or not budget:
            return {"error": "Missing campaign_id or budget"}
            
        url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{campaign_id}"
        payload = {
            "daily_budget": int(float(budget) * 100), # Graph API expects budget in cents/paise
            "access_token": self.meta_token
        }
        try:
            r = requests.post(url, data=payload, timeout=15)
            return r.json()
        except Exception as e:
            return {"error": str(e)}

AIMarketingAgentService = AIMarketingProService
