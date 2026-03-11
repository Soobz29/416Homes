import asyncio
import logging
from scraper.aggregator import scrape_all_sources
from collections import Counter
import sys

# Setup basic logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def main():
    print("Starting multi-source scraper verification...")
    try:
        listings = await scrape_all_sources()
        
        if not listings:
            print("No listings found from any source.")
            sys.exit(1)
            
        by_source = Counter(l['source'] for l in listings)
        print("\nVerification Complete!")
        print(f"Total Unique Listings: {len(listings)}")
        print("Breakdown by Source:")
        for source, count in by_source.items():
            print(f"  - {source}: {count}")
            
        if len(listings) > 0:
            print("\nSample Listing:")
            sample = listings[0]
            for k, v in sample.items():
                print(f"  {k}: {v}")
                
        if len(by_source) < 2:
            print("\nWARNING: Less than 2 sources returned data. Check for blocks.")
            
    except Exception as e:
        print(f"Verification failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
