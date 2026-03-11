import httpx
import time
import sys
import os

def run_demo():
    url = "http://127.0.0.1:8000/video/create-custom"
    
    img1 = r"C:\Users\soobo\.gemini\antigravity\brain\27c6d105-29f2-4f43-85af-1a75b0165d4b\test_kitchen_luxury_1772736530937.png"
    img2 = r"C:\Users\soobo\.gemini\antigravity\brain\27c6d105-29f2-4f43-85af-1a75b0165d4b\test_living_room_luxury_1772736546213.png"
    img3 = r"C:\Users\soobo\.gemini\antigravity\brain\27c6d105-29f2-4f43-85af-1a75b0165d4b\test_bedroom_luxury_1772736560887.png"
    
    if not os.path.exists(img1) or not os.path.exists(img2) or not os.path.exists(img3):
        print("❌ Missing test images! Please check paths.")
        return

    # Using httpx post syntax
    # files parameter should be a flat list of tuples or dict
    print("📦 Packing images for upload...")
    # For FastAPI List[UploadFile], we must pass multiple tuples with the SAME key ("photos")
    files = [
        ("photos", ("test_kitchen.png", open(img1, "rb"), "image/png")),
        ("photos", ("test_living.png", open(img2, "rb"), "image/png")),
        ("photos", ("test_bedroom.png", open(img3, "rb"), "image/png")),
    ]
    data = {
        "address": "123 Vision Drive, Toronto, ON",
        "price": "$2,500,000",
        "beds": "3",
        "baths": "3",
        "sqft": "2000",
        "description": "Stunning luxury suite with marble kitchen island, grand stone fireplace, and panoramic city views.",
        "voice": "female_luxury",
        "agent_name": "Vision Agent",
        "agent_email": "hello@vision.com"
    }
    
    print("\n🚀 Connecting to API endpoint /video/create-custom...")
    try:
        response = httpx.post(url, data=data, files=files, timeout=60.0)
        response.raise_for_status()
        res_json = response.json()
    except Exception as e:
        print(f"\n❌ Failed to connect to API or request failed: {e}")
        print("💡 Ensure 'uvicorn demo_api:app' is running.")
        sys.exit(1)
        
    job_id = res_json.get("job_id")
    print(f"\n✅ Job successfully initiated! Job ID: {job_id}\n")
    print(f"🔗 Polling /video/status/{job_id} for updates...\n")
    
    last_step = ""
    last_msg = ""
    last_prompts = []
    
    while True:
        try:
            status_res = httpx.get(f"http://127.0.0.1:8000/video/status/{job_id}").json()
            status = status_res.get("status")
            step = status_res.get("progress_step")
            msg = status_res.get("progress_message")
            prompts = status_res.get("cinematic_prompts", [])
            
            # Only print if something changed to keep console clean
            if step != last_step or msg != last_msg:
                print(f"[{status.upper()}] {step.upper()}: {msg}")
                last_step = step
                last_msg = msg
                
            # If new prompts are generated, print them
            if len(prompts) > len(last_prompts):
                new_prompt = prompts[-1]
                print(f"   🎥 NEW VISION PROMPT: {new_prompt[:120]}...")
                last_prompts = prompts
                
            if status == "complete":
                print(f"\n🎉 DONE! Video is ready! Check the video_pipeline/output folder.")
                break
            elif status == "failed":
                print(f"\n❌ FAILED! Check server error logs.")
                break
                
        except Exception as e:
            print(f"⚠️ Polling error: {e}")
            
        time.sleep(2)

if __name__ == "__main__":
    run_demo()
