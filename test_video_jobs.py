#!/usr/bin/env python3
"""
Test script for video job persistence
"""

import asyncio
import logging
from video_pipeline.pipeline import create_video_job, get_video_job_status

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_video_job_persistence():
    """Test creating and tracking video jobs"""
    
    logger.info("Testing video job persistence...")
    
    # Create a test video job
    job_id = await create_video_job(
        listing_url="https://www.realtor.ca/test-listing",
        customer_email="test@example.com",
        customer_name="Test User"
    )
    
    if job_id:
        logger.info(f"✅ Created video job: {job_id}")
        
        # Wait a moment for processing
        await asyncio.sleep(1)
        
        # Check job status
        job_status = await get_video_job_status(job_id)
        if job_status:
            logger.info(f"✅ Job status: {job_status['status']} (progress: {job_status['progress']}%)")
            logger.info(f"   Customer: {job_status['customer_name']} ({job_status['customer_email']})")
            logger.info(f"   Created: {job_status['created_at']}")
        else:
            logger.error("❌ Failed to get job status")
    else:
        logger.error("❌ Failed to create video job")
    
    logger.info("Video job persistence test complete!")

if __name__ == "__main__":
    asyncio.run(test_video_job_persistence())
