import os
import asyncio
from google import genai
from google.genai import types
from pathlib import Path

async def test_veo():
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    # Check if any videos folder exists to grab a test image
    test_img = Path("video_pipeline/output") / "placeholder.jpg" # Or any image
    if not test_img.exists():
        test_img = Path("video_pipeline/job_test/photos/photo_1.jpg")
        
    print(f"Using image: {test_img}")
    if not test_img.exists():
        videos = list(Path(".").rglob("*.jpg"))
        if videos:
            test_img = videos[0]
            print(f"Found image: {test_img}")
        else:
            print("No test images found")
            return
            
    print("Uploading to GenAI...")
    file_upload = client.files.upload(
        file=test_img,
        config={'display_name': 'test_veo_img'}
    )
    
    print(f"Uploaded file: {file_upload.name}")
    
    print("Requesting Veo 2.0 Video Generation...")
    try:
        suffix = test_img.suffix.lower()
        mime_map = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp'}
        mime_type = mime_map.get(suffix, 'image/jpeg')
        
        image = types.Image(image_bytes=test_img.read_bytes(), mime_type=mime_type)
        
        operation = client.models.generate_videos(
            model='veo-2.0-generate-001',
            prompt='Cinematic slow dolly forward',
            image=image,
        )
        print("Operation started!")
        print(f"Operation Name: {operation.name}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_veo())
