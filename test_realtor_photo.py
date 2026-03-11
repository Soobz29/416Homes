import asyncio
from video_pipeline.video_producer import _scrape_photo_urls

url = "https://www.realtor.ca/real-estate/29457635/512-142-dundas-street-east-toronto-moss-park-toronto-moss-park-m?view=imagelist"

print(f"Testing real scraper on: {url}")
photos = _scrape_photo_urls(url)

print(f"Found {len(photos)} photos.")
if photos:
    print("First 3:")
    for p in photos[:3]:
        print(p)
