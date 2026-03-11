import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import sys

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from video_pipeline.video_producer import generate_cinematic_prompt_for_photo

load_dotenv()

IMAGES = [
    r"C:\Users\soobo\.gemini\antigravity\brain\27c6d105-29f2-4f43-85af-1a75b0165d4b\test_kitchen_luxury_1772736530937.png",
    r"C:\Users\soobo\.gemini\antigravity\brain\27c6d105-29f2-4f43-85af-1a75b0165d4b\test_living_room_luxury_1772736546213.png",
    r"C:\Users\soobo\.gemini\antigravity\brain\27c6d105-29f2-4f43-85af-1a75b0165d4b\test_bedroom_luxury_1772736560887.png"
]

LISTING_DATA = {
    "address": "Test Luxury Suite - 123 Vision Drive",
    "price": "$2,500,000",
    "beds": 3,
    "baths": 2
}

async def run_test():
    with open("vision_test_results.txt", "w", encoding="utf-8") as f:
        f.write(f"Testing Gemini Vision Prompts on {len(IMAGES)} images...\n\n")
        for img_path in IMAGES:
            path_obj = Path(img_path)
            if not path_obj.exists():
                f.write(f"❌ Image not found: {img_path}\n")
                continue
                
            f.write(f"🔍 Analyzing: {path_obj.name}\n")
            try:
                prompt = await generate_cinematic_prompt_for_photo(path_obj, LISTING_DATA)
                f.write(f"🎬 Generated Prompt:\n{prompt}\n\n")
            except Exception as e:
                f.write(f"❌ Error: {e}\n\n")
            f.write("-" * 60 + "\n\n")

if __name__ == "__main__":
    asyncio.run(run_test())
