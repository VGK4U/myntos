import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv(".env")
api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"]

for m in models:
    try:
        model = genai.GenerativeModel(model_name=m)
        response = model.generate_content("hello")
        print(f"STABLE SDK Model {m} SUCCESS! Response: {response.text[:20]}")
    except Exception as e:
        print(f"STABLE SDK Model {m} FAILED: {str(e)}")
