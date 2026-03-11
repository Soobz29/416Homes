#!/usr/bin/env python3
"""
CLI runner for all scrapers
Usage: python -m scraper.run_all --source <source> --area <area>
"""

import asyncio
import argparse
import logging
import sys
from typing import List, Dict, Any

from .orchestrator import run_all_sources
from .realtor_ca import scrape_realtor_ca
from .kijiji import scrape_kijiji
from .redfin import scrape_redfin
from .zoocasa import scrape_zoocasa
from .housesigma import scrape_housesigma
from .condos_ca import scrape_condos_ca
from .zillow import scrape_zillow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main CLI entry point"""
    
    parser = argparse.ArgumentParser(description="Run real estate scrapers")
    parser.add_argument("--source", choices=["all", "realtor_ca", "kijiji", "redfin", "zoocasa", "housesigma", "condos_ca", "zillow"], 
                       default="all", help="Source to scrape")
    parser.add_argument("--area", choices=["toronto", "mississauga", "gta"], 
                       default="gta", help="Area to scrape")
    parser.add_argument("--days-back", type=int, default=30, 
                       help="Days back for sold comps (HouseSigma only)")
    
    args = parser.parse_args()
    
    logger.info(f"Starting scraper: source={args.source}, area={args.area}")
    
    try:
        if args.source == "all":
            listings = await run_all_sources(args.area)
        elif args.source == "realtor_ca":
            listings = await scrape_realtor_ca(args.area)
        elif args.source == "kijiji":
            listings = await scrape_kijiji(args.area)
        elif args.source == "redfin":
            listings = await scrape_redfin(args.area)
        elif args.source == "zoocasa":
            listings = await scrape_zoocasa(args.area)
        elif args.source == "housesigma":
            listings = await scrape_housesigma(args.area, args.days_back)
        elif args.source == "condos_ca":
            listings = await scrape_condos_ca(args.area)
        elif args.source == "zillow":
            listings = await scrape_zillow(args.area)
        else:
            logger.error(f"Unknown source: {args.source}")
            sys.exit(1)
        
        # Print results
        logger.info(f"Found {len(listings)} listings")
        
        for i, listing in enumerate(listings[:5], 1):  # Show first 5
            price = listing.get('price') or listing.get('sold_price', 0)
            logger.info(f"{i}. {listing['address']} - ${price:,} ({listing['source']})")
        
        if len(listings) > 5:
            logger.info(f"... and {len(listings) - 5} more")
        
        # Store to database if available
        try:
            from memory.store import embed_and_store_listings, store_sold_comps
            
            # Separate housesigma (sold comps) from regular listings
            regular_listings = []
            sold_comps = []
            
            for listing in listings:
                if listing.get('source') == 'housesigma' or 'sold_price' in listing:
                    sold_comps.append(listing)
                else:
                    regular_listings.append(listing)
            
            # Store regular listings
            if regular_listings:
                regular_count = await embed_and_store_listings(regular_listings)
                logger.info(f"Stored {regular_count}/{len(regular_listings)} listings to database")
            
            # Store sold comps
            if sold_comps:
                sold_count = await store_sold_comps(sold_comps)
                logger.info(f"Stored {sold_count}/{len(sold_comps)} sold comps to database")
                
        except ImportError:
            logger.warning("Database storage not available - skipping")
        except Exception as e:
            logger.error(f"Failed to store to database: {e}")
        
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
