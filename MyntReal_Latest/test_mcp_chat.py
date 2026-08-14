import requests
import json
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

URL = 'http://127.0.0.1:8000/api/v1/meta-ads-pro/chat'
HEADERS = {'Content-Type': 'application/json'}
history = []

def send_msg(msg):
    global history
    print(f"\n[USER] {msg}")
    try:
        r = requests.post(URL, json={'message': msg, 'history': history}, headers=HEADERS)
        data = r.json()
        response_text = data.get("response", "No response")
        print(f"[AI] {response_text}")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    send_msg("I am just testing the system. Create a test campaign called 'MCP Test Campaign 2026' with a daily budget of 150 INR and LEADS objective. Please confirm before executing.")
