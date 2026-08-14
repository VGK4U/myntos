import os
from dotenv import load_dotenv

load_dotenv(".env")

api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

if not api_key:
    print("NO API KEY FOUND")
    exit(1)

from google import genai

client = genai.Client(api_key=api_key)

models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"]

for m in models:
    try:
        response = client.models.generate_content(
            model=m,
            contents="hello"
        )
        print(f"Model {m} SUCCESS! Response: {response.text[:20]}")
    except Exception as e:
        print(f"Model {m} FAILED: {str(e)}")
