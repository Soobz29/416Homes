import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import os
from dotenv import load_dotenv

from memory.store import memory_store
# from elevenlabs import ElevenLabs  # Commented out for now
from google import genai

load_dotenv()
logger = logging.getLogger(__name__)

class VideoJobManager:
    """Manages video generation jobs with Supabase persistence"""
    
    def __init__(self):
        self.supabase = memory_store.supabase
        
        # Initialize ElevenLabs
        # self.elevenlabs = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))  # Commented out
        
        # Initialize Gemini
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model_id = "gemini-2.5-flash"
    
    async def create_video_job(self, listing_url: str, customer_email: str, 
                            customer_name: str = None) -> str:
        """Create a new video job and persist to database"""
        
        job_id = str(uuid.uuid4())
        
        job_data = {
            "id": job_id,
            "listing_url": listing_url,
            "customer_email": customer_email,
            "customer_name": customer_name or customer_email.split("@")[0],
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "progress": 0,
            "error_message": None,
            "video_url": None,
            "script_data": None,
            "audio_url": None,
            "final_video_path": None
        }
        
        try:
            result = self.supabase.table("video_jobs").insert(job_data).execute()
            
            if result.data:
                logger.info(f"Created video job {job_id} for {customer_email}")
                
                # Start processing asynchronously
                asyncio.create_task(self.process_video_job(job_id))
                
                return job_id
            else:
                logger.error(f"Failed to create video job")
                return None
                
        except Exception as e:
            logger.error(f"Error creating video job: {e}")
            return None
    
    async def get_video_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get video job status from database"""
        try:
            result = self.supabase.table("video_jobs")\
                .select("*")\
                .eq("id", job_id)\
                .single()\
                .execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error getting video job {job_id}: {e}")
            return None
    
    async def update_job_status(self, job_id: str, status: str, 
                             progress: int = None, error_message: str = None,
                             video_url: str = None, script_data: Dict = None,
                             audio_url: str = None, final_video_path: str = None):
        """Update video job status in database"""
        
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if progress is not None:
            update_data["progress"] = progress
        if error_message:
            update_data["error_message"] = error_message
        if video_url:
            update_data["video_url"] = video_url
        if script_data:
            update_data["script_data"] = script_data
        if audio_url:
            update_data["audio_url"] = audio_url
        if final_video_path:
            update_data["final_video_path"] = final_video_path
        
        try:
            result = self.supabase.table("video_jobs")\
                .update(update_data)\
                .eq("id", job_id)\
                .execute()
            
            if result.data:
                logger.info(f"Updated job {job_id} to {status} (progress: {progress}%)")
            else:
                logger.error(f"Failed to update job {job_id}")
                
        except Exception as e:
            logger.error(f"Error updating job {job_id}: {e}")
    
    async def process_video_job(self, job_id: str):
        """Process a video job through the pipeline"""
        
        try:
            # Get job details
            job = await self.get_video_job(job_id)
            if not job:
                logger.error(f"Job {job_id} not found")
                return
            
            listing_url = job["listing_url"]
            
            # Step 1: Generate script (25%)
            await self.update_job_status(job_id, "generating_script", 25)
            script_data = await self.generate_script(listing_url)
            
            if not script_data:
                await self.update_job_status(
                    job_id, "failed", 0, "Failed to generate script"
                )
                return
            
            await self.update_job_status(
                job_id, "script_generated", 50, 
                script_data=script_data
            )
            
            # Step 2: Generate audio (75%)
            await self.update_job_status(job_id, "generating_audio", 75)
            audio_url = await self.generate_audio(script_data["voiceover_script"])
            
            if not audio_url:
                await self.update_job_status(
                    job_id, "failed", 50, "Failed to generate audio"
                )
                return
            
            await self.update_job_status(
                job_id, "audio_generated", 75, 
                audio_url=audio_url
            )
            
            # Step 3: Generate final video (90%)
            await self.update_job_status(job_id, "generating_video", 90)
            video_url = await self.generate_final_video(script_data, audio_url)
            
            if not video_url:
                await self.update_job_status(
                    job_id, "failed", 75, "Failed to generate final video"
                )
                return
            
            # Step 4: Complete (100%)
            await self.update_job_status(
                job_id, "completed", 100, 
                video_url=video_url
            )
            
            logger.info(f"Video job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Error processing video job {job_id}: {e}")
            await self.update_job_status(
                job_id, "failed", 0, str(e)
            )
    
    async def generate_script(self, listing_url: str) -> Dict[str, Any]:
        """Generate video script from listing URL using Gemini"""
        
        try:
            # For now, return mock script data
            # In production, this would scrape the listing URL
            mock_listing_data = {
                "address": "123 Beautiful St, Toronto",
                "price": "$899,000",
                "beds": "3",
                "baths": "2", 
                "sqft": "1,500",
                "property_type": "Condo Apt",
                "description": "Stunning modern condo in prime location"
            }
            
            prompt = f"""
            Create a 30-second real estate video script for this property:
            
            Address: {mock_listing_data['address']}
            Price: {mock_listing_data['price']}
            {mock_listing_data['beds']} bed, {mock_listing_data['baths']} bath
            {mock_listing_data['sqft']} sqft {mock_listing_data['property_type']}
            Description: {mock_listing_data['description']}
            
            Return JSON with:
            - headline: Catchy opening line
            - voiceover_script: Full script (approx 75 words)
            - music_mood: Suggested music mood
            - key_features: List of 3-4 key selling points
            """
            
            response = self.client.models.generate_content(model=self.model_id, contents=prompt)
            
            # Parse response (simplified for demo)
            script_data = {
                "headline": "Your Dream Home Awaits!",
                "voiceover_script": "Welcome to this stunning modern condo in the heart of Toronto. With 3 bedrooms, 2 bathrooms, and 1,500 square feet of living space, this home offers everything you need for comfortable urban living. The prime location puts you steps away from shopping, dining, and transit. Don't miss this opportunity to own your piece of Toronto's vibrant real estate market.",
                "music_mood": "upbeat_inspiring",
                "key_features": ["Modern kitchen", "Prime location", "Spacious layout", "Great natural light"]
            }
            
            return script_data
            
        except Exception as e:
            logger.error(f"Script generation failed: {e}")
            return None
    
    async def generate_audio(self, script_text: str) -> str:
        """Generate audio from script using ElevenLabs"""
        
        try:
            # For demo, return mock URL
            # In production, this would call ElevenLabs API
            audio_url = f"https://storage.googleapis.com/416homes-audio/{uuid.uuid4()}.mp3"
            
            # Simulate processing time
            await asyncio.sleep(2)
            
            return audio_url
            
        except Exception as e:
            logger.error(f"Audio generation failed: {e}")
            return None
    
    async def generate_final_video(self, script_data: Dict, audio_url: str) -> str:
        """Generate final video with animation"""
        
        try:
            # For demo, return mock URL
            # In production, this would use Calico AI or ffmpeg
            video_url = f"https://storage.googleapis.com/416homes-videos/{uuid.uuid4()}.mp4"
            
            # Simulate processing time
            await asyncio.sleep(3)
            
            return video_url
            
        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            return None

# Global video job manager
video_job_manager = VideoJobManager()

# Convenience functions
async def create_video_job(listing_url: str, customer_email: str, 
                          customer_name: str = None) -> str:
    """Create a new video job"""
    return await video_job_manager.create_video_job(
        listing_url, customer_email, customer_name
    )

async def get_video_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get video job status"""
    return await video_job_manager.get_video_job(job_id)

# Legacy function for compatibility
def generate_script(listing_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate script from listing data (sync version for demo)"""
    return {
        "headline": "Your Dream Home Awaits!",
        "voiceover_script": f"Welcome to this beautiful property at {listing_data.get('address', 'Unknown Address')}. This {listing_data.get('beds', '3')} bedroom, {listing_data.get('baths', '2')} bathroom home offers {listing_data.get('sqft', '1,500')} square feet of living space. Priced at {listing_data.get('price', '$899,000')}, this is an incredible opportunity in today's market.",
        "music_mood": "upbeat_inspiring",
        "key_features": ["Great location", "Modern amenities", "Spacious rooms", "Excellent value"]
    }
