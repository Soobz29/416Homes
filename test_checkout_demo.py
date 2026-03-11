import httpx
import time
import sys

def run_checkout_demo():
    url = "http://127.0.0.1:8000/video/create-checkout"
    listing_url = "https://condos.ca/toronto/33-bay-at-pinnacle-centre-33-bay-st/unit-414-C12852472"
    
    data = {
        "listing_url": listing_url,
        "voice": "female_luxury",
        "agent_name": "Demo Agent",
        "agent_email": "demo@416homes.com"
    }
    
    print(f"\n🚀 Initiating checkout demo for URL: {listing_url}")
    try:
        response = httpx.post(url, json=data, timeout=30.0)
        response.raise_for_status()
        res_json = response.json()
    except Exception as e:
        print(f"\n❌ Failed to connect to API or request failed: {e}")
        sys.exit(1)
        
    job_id = res_json.get("job_id")
    print(f"\n✅ Job successfully initiated! Job ID: {job_id}\n")
    print(f"🔗 Polling /video/status/{job_id} for updates...\n")
    
    last_step = ""
    last_msg = ""
    last_prompts = []
    
    start_time = time.time()
    
    while True:
        try:
            status_res = httpx.get(f"http://127.0.0.1:8000/video/status/{job_id}").json()
            status = status_res.get("status")
            step = status_res.get("progress_step")
            msg = status_res.get("progress_message")
            prompts = status_res.get("cinematic_prompts", [])
            
            if step != last_step or msg != last_msg:
                elapsed = int(time.time() - start_time)
                print(f"[{elapsed}s][{status.upper()}] {step.upper()}: {msg}")
                last_step = step
                last_msg = msg
                
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
            pass
            
        time.sleep(2)

if __name__ == "__main__":
    run_checkout_demo()
