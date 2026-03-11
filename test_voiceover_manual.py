import os
import sys
from pathlib import Path
import logging

# Add the project root to sys.path
sys.path.append(os.getcwd())

from video_pipeline.video_producer import _sync_generate_voiceover

logging.basicConfig(level=logging.INFO)

def test_voiceover():
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("ELEVENLABS_API_KEY not found")
        return

    text = "Welcome to 120 Clement Road. This beautiful home offers modern architectural details and luxury finishes throughout."
    voice_id = "21m00Tcm4TlvDq8ikWAM" # Rachel
    out_path = Path("test_voiceover_manual.mp3")

    try:
        print(f"Generating voiceover to {out_path}...")
        _sync_generate_voiceover(text, voice_id, api_key, out_path)
        if out_path.exists():
            print(f"Success! File size: {out_path.stat().st_size} bytes")
        else:
            print("Failed: File not created")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_voiceover()
