import os
import json
import logging
import asyncio
from typing import List, Dict, Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    genai = None
    types = None
    HAS_GENAI = False

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a highly capable AI Marketing Agent functioning as a fully autonomous Meta Ads Manager using the Model Context Protocol (MCP).
You have direct integration with the Meta Ads MCP Server.
Your goal is to help users manage, create, and analyze Meta Ads (Facebook & Instagram) entirely through conversation.
You are professional, concise, and proactive. Do not hallucinate data; always use your tools to fetch real data from the Meta Ads account.

# Key Capabilities & Rules
1. You can fetch active campaigns and their performance insights directly from Meta.
2. You can create new campaigns.
3. You can update campaign daily budgets and statuses (PAUSED/ACTIVE).
4. CRITICAL: For any action that spends money or modifies live campaigns, YOU MUST FIRST ASK THE USER FOR EXPLICIT PERMISSION before calling the tool. For example: "I am ready to increase the budget to ₹1000. Please confirm if I should proceed."
5. If the user gives permission, proceed to call the tool immediately.
6. When displaying data to the user, format it neatly in Markdown tables or bulleted lists. 
7. Do not mention "tools", "backend functions", or "MCP" to the user. Just provide the information seamlessly.
"""

def map_mcp_type(t: str):
    t = str(t).upper() if t else "STRING"
    if t == "STRING": return types.Type.STRING
    if t == "INTEGER": return types.Type.INTEGER
    if t == "NUMBER": return types.Type.NUMBER
    if t == "BOOLEAN": return types.Type.BOOLEAN
    if t == "ARRAY": return types.Type.ARRAY
    if t == "OBJECT": return types.Type.OBJECT
    return types.Type.STRING

class AIMarketingProService:
    def __init__(self, db, company_id: int, staff_id: int):
        self.db = db
        self.company_id = company_id
        self.staff_id = staff_id
        self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            
        if HAS_GENAI and self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None
            
        self.candidate_models = ["gemini-3.5-flash", "gemini-3.5-flash-lite"]

    async def process_chat(self, user_message: str, history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        return await self._process_chat_async(user_message, history)

    async def _process_chat_async(self, user_message: str, history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.client:
            return {
                "response": "AI Marketing Assistant is currently unavailable. Please configure GEMINI_API_KEY or GOOGLE_API_KEY in backend/.env file.",
                "components": None
            }

        server_script_path = os.path.join(os.path.dirname(__file__), "..", "mcp", "meta_ads_server.py")
        server_params = StdioServerParameters(
            command="python",
            args=[server_script_path],
            env=os.environ.copy()
        )

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    mcp_tools = await session.list_tools()
                    
                    gemini_function_declarations = []
                    for t in mcp_tools.tools:
                        properties = {}
                        input_schema = t.inputSchema or {}
                        props_dict = input_schema.get("properties", {})
                        
                        for k, v in props_dict.items():
                            prop_type = map_mcp_type(v.get("type", "string"))
                            description = v.get("description", "")
                            properties[k] = types.Schema(type=prop_type, description=description)
                            
                        schema_obj = types.Schema(
                            type=types.Type.OBJECT,
                            properties=properties,
                            required=input_schema.get("required", [])
                        )
                        gemini_function_declarations.append(
                            types.FunctionDeclaration(
                                name=t.name,
                                description=t.description,
                                parameters=schema_obj
                            )
                        )
                    
                    gemini_tools = [types.Tool(function_declarations=gemini_function_declarations)]
                    
                    return await self._run_gemini_loop(user_message, history, session, gemini_tools)
        except Exception as e:
            logger.error(f"Failed to connect to Meta Ads MCP Server: {e}")
            return {
                "response": f"⚠️ Connection to Meta Ads MCP Server failed. Error: {e}",
                "components": None
            }

    async def _run_gemini_loop(self, user_message: str, history: List[Dict[str, Any]], mcp_session: ClientSession, gemini_tools: list) -> Dict[str, Any]:
        if not history:
            history = []

        contents = []
        for msg in history:
            role = 'user' if msg.get('role') == 'user' else 'model'
            text_content = ""
            if "content" in msg:
                text_content = msg["content"]
            elif "parts" in msg and len(msg["parts"]) > 0:
                text_content = msg["parts"][0].get("text", "")
                
            if not text_content:
                continue

            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=text_content)]
                )
            )
            
        contents.append(
            types.Content(
                role='user',
                parts=[types.Part.from_text(text=user_message)]
            )
        )
        
        last_error = None
        for model_name in self.candidate_models:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.3,
                        tools=gemini_tools
                    )
                )

                max_turns = 10
                turns = 0
                
                while response.function_calls and turns < max_turns:
                    turns += 1
                    contents.append(response.candidates[0].content)
                    
                    tool_responses = []
                    for fn in response.function_calls:
                        tool_name = fn.name
                        tool_args = fn.args or {}
                        
                        logger.error(f"MCP Client executing tool: {tool_name} with args: {tool_args}")
                        
                        try:
                            mcp_result = await mcp_session.call_tool(tool_name, arguments=tool_args)
                            tool_result_text = mcp_result.content[0].text if mcp_result.content else "{}"
                            try:
                                tool_result_data = json.loads(tool_result_text)
                            except:
                                tool_result_data = {"raw": tool_result_text}
                        except Exception as e:
                            tool_result_data = {"error": str(e)}
                            
                        tool_responses.append(
                            types.Part(
                                function_response=types.FunctionResponse(
                                    name=tool_name, 
                                    response={"result": tool_result_data},
                                    id=fn.id
                                )
                            )
                        )
                    
                    contents.append(
                        types.Content(
                            role="user",
                            parts=tool_responses
                        )
                    )
                    
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.3,
                            tools=gemini_tools
                        )
                    )

                final_text = response.text
                if not final_text:
                    final_text = "I gathered the data via MCP but reached my internal processing limit before formulating an answer. Could you please ask a more specific question?"

                return {
                    "response": final_text,
                    "components": None
                }
            except Exception as e:
                err_str = str(e)
                logger.error(f"Error in AIMarketingProService with model {model_name}: {err_str}")
                if any(term in err_str for term in ["PERMISSION_DENIED", "leaked", "API_KEY_INVALID", "no longer available"]):
                    return {
                        "response": "⚠️ Google Gemini API key needs to be updated. The key configured in .env was flagged/deprecated by Google. Please generate a new API key from Google AI Studio and update GOOGLE_API_KEY in backend/.env.",
                        "components": None
                    }
                last_error = err_str
                continue

        return {
            "response": "⚠️ Google Gemini API key needs to be updated. Please check logs.",
            "components": None
        }

AIMarketingAgentService = AIMarketingProService
