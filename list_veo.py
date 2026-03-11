import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

print("Available Models:")
for model in client.models.list():
    if "veo" in model.name.lower():
        print(f"- {model.name}")
