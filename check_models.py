import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("Available Models:")
try:
    for m in client.models.list():
        print(f"{m.name} | Methods: {getattr(m, 'supported_generation_methods', 'N/A')}")
        if '2.0-flash' in m.name:
            print(f"DEBUG: {m}")
except Exception as e:
    print("Error:", e)
