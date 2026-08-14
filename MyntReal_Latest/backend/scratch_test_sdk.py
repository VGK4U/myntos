import os
from dotenv import load_dotenv

load_dotenv(".env")
api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

from google import genai
client = genai.Client(api_key=api_key)

print(dir(client))
try:
    print(dir(client.interactions))
except Exception as e:
    print("No interactions:", e)

try:
    print(dir(client.models))
except Exception as e:
    print("No models:", e)
