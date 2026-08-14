import os
from dotenv import load_dotenv
from google import genai

load_dotenv(".env")
api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

models = ["gemini-flash-latest", "gemini-3.5-flash", "gemini-2.5-flash"]
for m in models:
    try:
        response = client.models.generate_content(
            model=m,
            contents="hello"
        )
        print(f"Model {m} SUCCESS! Response: {response.text[:20]}")
    except Exception as e:
        print(f"Model {m} FAILED: {str(e)}")
