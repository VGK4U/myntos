import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(".env")
api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

get_meta_campaigns_schema = {"function_declarations": [{
    "name": "get_meta_campaigns",
    "description": "Fetches a list of all Meta Ads campaigns with their ID, name, status, and objective.",
    "parameters": {"type": "OBJECT", "properties": {}}
}]}

response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="Can you fetch my active campaigns?",
    config=types.GenerateContentConfig(
        tools=[get_meta_campaigns_schema]
    )
)

print(f"Has function calls? {hasattr(response, 'function_calls')}")
print(f"response.function_calls: {getattr(response, 'function_calls', None)}")
if response.candidates and response.candidates[0].content.parts:
    for i, part in enumerate(response.candidates[0].content.parts):
        print(f"Part {i}: {part}")
print(f"response.text: {repr(response.text)}")
