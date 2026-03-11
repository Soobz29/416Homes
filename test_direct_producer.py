import asyncio
import logging
from pprint import pprint

# Set up logging to stdout
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def main():
    from demo_api import scrape_listing_from_url, generate_script_with_gemini
    from video_pipeline.video_producer import produce_video
    import time
    
    url = "https://www.realtor.ca/real-estate/29421416/1264-st-marys-avenue-mississauga-lakeview-lakeview?view=imagelist"
    print(f"Testing live Realtor.ca scrape on: {url}")
    
    listing_data = await scrape_listing_from_url(url)
    if not listing_data or "error" in listing_data:
        print(f"Scraper failed: {listing_data}")
        return
        
    print("Generating script...")
    script_data = await generate_script_with_gemini(listing_data)
    if not script_data:
        print("Failed to generate script")
        return
        
    print("Script success:")
    pprint(script_data)
    
    async def progress(step, msg):
        print(f"[{step.upper()}] {msg}")
        
    print("Running video producer directly...")
    start = time.time()
    result = await produce_video(
        listing_url=url,
        listing_data=listing_data,
        script_data=script_data,
        voice="male_cassius",
        on_progress=progress,
        job_id="test_lakeview_v1"
    )
    
    elapsed = time.time() - start
    if result:
        print(f"SUCCESS in {elapsed:.1f}s: {result}")
    else:
        print(f"FAILED in {elapsed:.1f}s. Check logs above.")

if __name__ == "__main__":
    asyncio.run(main())
