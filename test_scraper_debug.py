import os
import sys
import asyncio
from pathlib import Path
import logging

# Add the project root to sys.path
sys.path.append(os.getcwd())

from video_pipeline.video_producer import download_listing_photos

logging.basicConfig(level=logging.INFO)

async def test_scraper():
    # Use a real condos.ca URL or similar
    url = "https://condos.ca/toronto/the-well-480-front-st-w-470-front-st-w-38-spadina-ave-455-wellington-st-w/unit-3510-C5921825" # Example URL
    # Or just use the one from test_pipeline if it worked before
    url = "https://www.realtor.ca/real-estate/26584065/120-clement-rd-toronto-etobicoke-west-humber-clairville"
    
    job_dir = Path("test_scrape_debug")
    job_dir.mkdir(exist_ok=True)
    
    print(f"Testing scraper for {url}...")
    try:
        photos = await download_listing_photos(url, job_dir, address="120 Clement Road")
        print(f"Scraper returned {len(photos)} photos.")
        for p in photos:
            print(f"  - {p} (exists: {p.exists()}, size: {p.stat().st_size if p.exists() else 0} bytes)")
    except Exception as e:
        print(f"Scraper error: {e}")

if __name__ == "__main__":
    asyncio.run(test_scraper())
