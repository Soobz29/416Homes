#!/usr/bin/env python3
"""
Simple test script for video job persistence (without database)
"""

import asyncio
import logging
from video_pipeline.pipeline import generate_script

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_video_job_simple():
    """Test video job functionality without database"""
    
    logger.info("Testing video job functionality...")
    
    # Test script generation
    listing_data = {
        "address": "123 Beautiful St, Toronto",
        "price": "$899,000",
        "beds": "3",
        "baths": "2", 
        "sqft": "1,500",
        "property_type": "Condo Apt",
        "description": "Stunning modern condo in prime location"
    }
    
    script_data = generate_script(listing_data)
    
    if script_data:
        logger.info("✅ Script generation successful!")
        logger.info(f"   Headline: {script_data['headline']}")
        logger.info(f"   Script length: {len(script_data['voiceover_script'])} chars")
        logger.info(f"   Music mood: {script_data['music_mood']}")
        logger.info(f"   Key features: {script_data['key_features']}")
    else:
        logger.error("❌ Script generation failed")
    
    logger.info("Video job functionality test complete!")

if __name__ == "__main__":
    asyncio.run(test_video_job_simple())
