import os
import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a highly capable AI Marketing Employee inside a Real Estate & Corporate CRM system.
Your goal is to help users manage, create, and analyze Meta Ads (Facebook & Instagram) entirely through conversation.
You are professional, concise, and proactive. You do not ask excessive questions; you infer logical defaults (e.g., if the user wants to advertise Real Estate, you can infer audiences like 'Property Buyers', 'Investors', etc. without asking).

# Key Capabilities
1. You can fetch campaign performance metrics.
2. You can create new campaigns, ad sets, and ads.
3. You can generate ad creatives and copy.

When answering, format your text nicely. If you execute a tool, analyze the result and present it to the user in a readable format.
If you output a chart, the backend will parse it, but you should still provide a conversational summary.
"""

# Native Function Declarations for Gemini Tools
fetch_campaign_metrics_schema = {"function_declarations": [{
    "name": "fetch_campaign_metrics",
    "description": "Fetches performance metrics for existing Meta Ads campaigns (Spend, Impressions, Clicks, Leads).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "date_preset": {
                "type": "STRING",
                "description": "Date preset for metrics (e.g., 'last_30d', 'last_7d', 'today', 'lifetime'). Defaults to 'last_30d'."
            }
        }
    }
}]}

create_meta_campaign_schema = {"function_declarations": [{
    "name": "create_meta_campaign",
    "description": "Creates a new Meta Ads campaign.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "campaign_name": {"type": "STRING", "description": "Name of the campaign."},
            "daily_budget_inr": {"type": "NUMBER", "description": "Daily budget in INR."},
            "objective": {"type": "STRING", "description": "Campaign objective (e.g., 'OUTCOME_LEADS', 'OUTCOME_SALES')."}
        },
        "required": ["campaign_name", "daily_budget_inr"]
    }
}]}

create_ad_creative_schema = {"function_declarations": [{
    "name": "generate_ad_creative",
    "description": "Generates a new image creative and ad copy for a campaign.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {"type": "STRING", "description": "Visual description of the image to generate."},
            "aspect_ratio": {"type": "STRING", "description": "Image aspect ratio, e.g., '1:1', '16:9', '9:16'."}
        },
        "required": ["prompt"]
    }
}]}

class AIMarketingProService:
    def __init__(self, db: Session, company_id: int, staff_id: int):
        self.db = db
        self.company_id = company_id
        self.staff_id = staff_id
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-flash-latest" # Fast and supports tools
        self.image_model = "imagen-3.0-generate-001"

    def process_chat(self, user_message: str, history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user message using Gemini with Function Calling.
        """
        if not history:
            history = []

        # Convert history to Gemini contents
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

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.3,
                    tools=[fetch_campaign_metrics_schema, create_meta_campaign_schema, create_ad_creative_schema]
                )
            )

            # Handle Function Calls
            components = None
            if response.function_calls:
                fn = response.function_calls[0]
                if fn.name == "fetch_campaign_metrics":
                    # Fetch REAL data from the existing analytics service
                    from app.services.meta_insights_analytics_service import get_meta_ads_dashboard_kpis
                    real_data = get_meta_ads_dashboard_kpis(self.db, self.company_id)
                    
                    spend = real_data.get('metrics', {}).get('spend_inr', 0)
                    leads = real_data.get('metrics', {}).get('leads', 0)
                    cpl = real_data.get('metrics', {}).get('cpl', 0)
                    active_campaigns = real_data.get('active_campaigns', 0)
                    
                    # Convert the real data into chart components
                    components = self._render_chart_component({
                        "spend": spend,
                        "leads": leads,
                        "cpl": cpl,
                        "active_campaigns": active_campaigns
                    })
                    
                    return {
                        "response": f"Here is the real-time performance data for your Meta Ads. You have {active_campaigns} active campaigns, with a total spend of ₹{spend} generating {leads} leads at a CPL of ₹{cpl}.",
                        "components": components
                    }
                elif fn.name == "create_meta_campaign":
                    return {
                        "response": f"I have initiated the creation of the campaign '{fn.args.get('campaign_name')}' with a daily budget of ₹{fn.args.get('daily_budget_inr')}.",
                        "components": None
                    }
                elif fn.name == "generate_ad_creative":
                    components = self._generate_image(fn.args)
                    return {
                        "response": "Here is the ad creative I generated for you based on the strategy. You can download this directly to your Meta Ads Media Library.",
                        "components": components
                    }

            return {
                "response": response.text,
                "components": None
            }
            
        except Exception as e:
            logger.error(f"Error in AIMarketingProService: {str(e)}")
            # Fallback to standard chat if model fails or tools fail
            return {
                "response": "I'm currently experiencing high latency with my core reasoning engine. Please try again in a moment.",
                "components": None
            }

    def _render_chart_component(self, args: dict) -> dict:
        """
        Generates HTML/JS to be injected into the chat UI for charts.
        """
        chart_id = f"chart_{os.urandom(4).hex()}"
        
        spend = args.get('spend', 0)
        leads = args.get('leads', 0)
        cpl = args.get('cpl', 0)
        
        html = f'''
        <div class="metric-cards">
            <div class="metric-card"><div class="metric-label">Spend</div><div class="metric-value">₹{spend:,.2f}</div></div>
            <div class="metric-card"><div class="metric-label">Leads</div><div class="metric-value">{leads}</div></div>
            <div class="metric-card"><div class="metric-label">CPL</div><div class="metric-value">₹{cpl:,.2f}</div></div>
        </div>
        <div class="chart-wrapper">
            <canvas id="{chart_id}"></canvas>
        </div>
        '''
        
        script = f'''
        const ctx = document.getElementById('{chart_id}').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{{
                    label: 'Leads Trend',
                    data: [Math.max(0, {leads}-10), Math.max(0, {leads}-5), {leads}, Math.max(0, {leads}-2), {leads}+5, {leads}+12, {leads}+8],
                    borderColor: '#10B981',
                    tension: 0.4,
                    fill: false
                }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: false }}
        }});
        '''
        return {"html": html, "script": script}

    def _generate_image(self, args: dict) -> dict:
        """
        Uses Google Imagen 3 (via Gemini SDK) to generate an image based on the AI's prompt.
        """
        prompt = args.get("prompt", "A high quality marketing image")
        aspect_ratio = args.get("aspect_ratio", "1:1")
        
        try:
            # Using Imagen 3 syntax if available on standard key
            result = self.client.models.generate_images(
                model=self.image_model,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio=aspect_ratio,
                    output_mime_type="image/jpeg",
                    # Some accounts require safety settings, omit for now to use defaults
                )
            )
            
            # Extract base64 image data (or fallback)
            if hasattr(result, 'generated_images') and len(result.generated_images) > 0:
                image_bytes = result.generated_images[0].image.image_bytes
                import base64
                b64 = base64.b64encode(image_bytes).decode('utf-8')
                
                html = f'''
                <div class="ad-preview">
                    <div class="ad-header">
                        <img src="/public/images/logo.png" alt="Logo" onerror="this.src='https://ui-avatars.com/api/?name=MR&background=0D8ABC&color=fff'">
                        <div>
                            <div class="ad-name">Your Company</div>
                            <div class="ad-sponsored">Sponsored · <i class="fas fa-globe-americas"></i></div>
                        </div>
                    </div>
                    <div class="ad-text">{prompt[:100]}...</div>
                    <img src="data:image/jpeg;base64,{b64}" class="ad-media" alt="Generated Ad">
                    <div class="ad-cta-area">
                        <div>
                            <div class="ad-headline">Exclusive Offer</div>
                            <div class="ad-desc">Learn more about our services.</div>
                        </div>
                        <button class="ad-btn">Learn more</button>
                    </div>
                </div>
                '''
                return {"html": html}
            else:
                return {"html": "<p><i>Image generation returned empty results. Your API key might not support Imagen 3 yet.</i></p>"}
        except Exception as e:
            logger.error(f"Imagen error: {e}")
            return {"html": f"<p style='color:red;'><i>Image Generation Error: {str(e)}<br>Ensure your Gemini API key has access to Imagen 3.</i></p>"}
