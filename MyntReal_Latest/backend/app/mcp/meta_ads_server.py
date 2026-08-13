import os
import json
import requests
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

# Initialize FastMCP Server
mcp = FastMCP("Meta Ads MCP Server")

GRAPH_API_VERSION = "v22.0"
META_SYSTEM_USER_TOKEN = os.getenv("META_SYSTEM_USER_TOKEN")
META_AD_ACCOUNT_ID = os.getenv("META_AD_ACCOUNT_ID")

@mcp.tool()
def get_meta_campaigns() -> str:
    """Fetch all active or paused Meta Ads campaigns."""
    if not META_SYSTEM_USER_TOKEN or not META_AD_ACCOUNT_ID:
        return json.dumps({"error": "Meta Ads Integration credentials missing"})
    
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{META_AD_ACCOUNT_ID}/campaigns"
    params = {"access_token": META_SYSTEM_USER_TOKEN, "fields": "id,name,status,objective,daily_budget", "limit": 50}
    try:
        r = requests.get(url, params=params, timeout=15)
        return r.text
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def get_meta_insights(campaign_id: str = None, date_preset: str = "last_30d") -> str:
    """Fetch performance insights for a specific campaign or the entire account."""
    if not META_SYSTEM_USER_TOKEN or not META_AD_ACCOUNT_ID:
        return json.dumps({"error": "Meta Ads Integration credentials missing"})
        
    target_id = campaign_id if campaign_id else META_AD_ACCOUNT_ID
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{target_id}/insights"
    params = {"access_token": META_SYSTEM_USER_TOKEN, "fields": "spend,impressions,clicks,cpc,cpm,reach", "date_preset": date_preset}
    try:
        r = requests.get(url, params=params, timeout=15)
        return r.text
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def create_meta_campaign(name: str, objective: str, daily_budget: int) -> str:
    """Create a new Meta Ads campaign."""
    if not META_SYSTEM_USER_TOKEN or not META_AD_ACCOUNT_ID:
        return json.dumps({"error": "Meta Ads Integration credentials missing"})
        
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{META_AD_ACCOUNT_ID}/campaigns"
    payload = {
        "name": name,
        "objective": objective,
        "status": "PAUSED",
        "special_ad_categories": "NONE",
        "access_token": META_SYSTEM_USER_TOKEN
    }
    if daily_budget:
        payload["daily_budget"] = daily_budget * 100
    try:
        r = requests.post(url, data=payload, timeout=15)
        return r.text
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def update_campaign_status(campaign_id: str, status: str) -> str:
    """Pause or resume a specific Meta Ads campaign. Status must be 'ACTIVE' or 'PAUSED'."""
    if not META_SYSTEM_USER_TOKEN:
        return json.dumps({"error": "Meta Ads Integration credentials missing"})
        
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{campaign_id}"
    payload = {"status": status, "access_token": META_SYSTEM_USER_TOKEN}
    try:
        r = requests.post(url, data=payload, timeout=15)
        return r.text
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def update_campaign_budget(campaign_id: str, daily_budget: int) -> str:
    """Update the daily budget for a specific Meta Ads campaign."""
    if not META_SYSTEM_USER_TOKEN:
        return json.dumps({"error": "Meta Ads Integration credentials missing"})
        
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{campaign_id}"
    payload = {"daily_budget": daily_budget * 100, "access_token": META_SYSTEM_USER_TOKEN}
    try:
        r = requests.post(url, data=payload, timeout=15)
        return r.text
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    mcp.run(transport='stdio')
