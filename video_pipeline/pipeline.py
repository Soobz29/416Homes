import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import tempfile
import uuid
import os

import httpx
from dotenv import load_dotenv

from memory.store import memory_store
from .photo_classifier import PhotoClassifier
from .scene_planner import ScenePlanner
from .renderer import VideoRenderer

try:
    # New Gemini SDK (package: google-genai)
    from google import genai as _genai  # type: ignore
    _GENAI_SDK = "google-genai"
except Exception:  # pragma: no cover
    try:
        # Legacy Gemini SDK (package: google-generativeai)
        import google.generativeai as _genai  # type: ignore
        _GENAI_SDK = "google-generativeai"
    except Exception:  # pragma: no cover
        _genai = None  # type: ignore[assignment]
        _GENAI_SDK = "none"

load_dotenv()
logger = logging.getLogger(__name__)


class VideoJobManager:
    """Manages video generation jobs with Supabase persistence."""

    def __init__(self):
        self.supabase = memory_store.supabase

        # Initialize Vertex AI Studio (API key) for script generation
        import google.genai as genai

        # Vertex AI Studio uses API key (uses free credits!)
        api_key = os.getenv("VERTEX_AI_API_KEY")
        if not api_key:
            raise ValueError("VERTEX_AI_API_KEY required")

        if hasattr(genai, "configure"):
            genai.configure(api_key=api_key)  # type: ignore[attr-defined]
            self._vertex_client = None
            self.vertex_model = genai.GenerativeModel("gemini-2.5-flash-lite")  # type: ignore[attr-defined]
        else:
            self._vertex_client = genai.Client(api_key=api_key)  # type: ignore[attr-defined]
            self.vertex_model = "gemini-2.5-flash-lite"

        logger.info("✅ Vertex AI Studio API key configured for script generation")

        # Initialize Gemini (for script generation)
        self.client = None
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and _genai is not None and _GENAI_SDK != "none":
            if _GENAI_SDK == "google-genai":
                self.client = _genai.Client(api_key=api_key)  # type: ignore[call-arg]
            else:
                _genai.configure(api_key=api_key)  # type: ignore[call-arg]
                self.client = _genai.GenerativeModel("gemini-2.0-flash-exp")  # type: ignore[call-arg]
        self.model_id = os.getenv("GEMINI_VIDEO_MODEL", "gemini-2.5-flash")

        # Vision + scene planning components
        self.photo_classifier = PhotoClassifier()
        self.scene_planner = ScenePlanner()
    
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
            self.supabase.table("video_jobs").insert(job_data).execute()
            logger.info("Created video job: %s", job_id)
            asyncio.create_task(self.process_video_job(job_id))
            return job_id
        except Exception as e:
            logger.error("Failed to create video job: %s", e)
            raise
    
    async def get_video_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get video job status from database"""
        try:
            result = self.supabase.table("video_jobs")\
                .select("*")\
                .eq("id", job_id)\
                .single()\
                .execute()
            
            return getattr(result, "data", None)
            
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
            result = (
                self.supabase.table("video_jobs")
                .update(update_data)
                .eq("id", job_id)
                .execute()
            )
            if getattr(result, "data", None):
                logger.info("Updated job %s to %s (progress: %s%%)", job_id, status, progress)
            else:
                logger.error("Failed to update job %s", job_id)
        except Exception as e:  # pragma: no cover - network/db
            logger.error("Error updating job %s: %s", job_id, e)

    def _update_job(self, job_id: str, **updates: Any) -> None:
        """Update job fields in Supabase."""
        try:
            clean_updates = {k: v for k, v in updates.items() if v is not None}

            if not clean_updates:
                return

            clean_updates["updated_at"] = datetime.utcnow().isoformat()
            logger.info("Updating job %s: %s", job_id, list(clean_updates.keys()))

            self.supabase.table("video_jobs").update(clean_updates).eq("id", job_id).execute()

        except Exception as e:
            logger.error("Failed to update job %s: %s", job_id, e)

    def _update_job_record(self, job_id: str, **fields: Any) -> None:
        """Low-level helper to patch arbitrary fields on a video job."""
        self._update_job(job_id, **fields)

    async def _fetch_listing_photos(self, listing_url: str) -> List[str]:
        """Fetch high-resolution photo URLs from Zoocasa listing page using multiple extraction methods."""
        if not listing_url:
            return []

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
                resp = await client.get(listing_url)
                resp.raise_for_status()
                html = resp.text
        except Exception as e:
            logger.error("Failed to fetch listing HTML for %s: %s", listing_url, e)
            return []

        urls: List[str] = []

        # Method 1: Extract from ALL image URLs in HTML using regex (most reliable)
        import re

        # Find all images.expcloud.com URLs (Zoocasa's CDN)
        pattern = r'https://images\.expcloud\.com/[^\s"\'<>)]+\.(?:jpg|jpeg|png|webp)(?:\?[^\s"\'<>)]*)?'
        all_urls = re.findall(pattern, html, re.IGNORECASE)

        # Deduplicate and prefer larger sizes
        url_bases: Dict[str, Dict[str, Any]] = {}  # base_path -> largest_url
        for url in all_urls:
            # Remove size params to find base
            base = re.sub(r"[?&]w=\d+", "", url)
            base = re.sub(r"[?&]h=\d+", "", base)

            # Extract width if present
            width_match = re.search(r"[?&]w=(\d+)", url)
            width = int(width_match.group(1)) if width_match else 0

            # Keep largest version of each unique photo
            if base not in url_bases or width > url_bases.get(base, {}).get("width", 0):
                url_bases[base] = {"url": url, "width": width}

        urls = [info["url"] for info in url_bases.values()]
        logger.info("Extracted %d unique photos from regex scan", len(urls))

        # Method 2: Try to find photo data in script tags (JSON arrays)
        if len(urls) < 3:
            photo_patterns = [
                r'"photos"\s*:\s*\[(.*?)\]',
                r'"images"\s*:\s*\[(.*?)\]',
                r"photoUrls\s*[:=]\s*\[(.*?)\]",
                r'"media"\s*:\s*{[^}]*"photos"\s*:\s*\[(.*?)\]',
            ]

            for p in photo_patterns:
                matches = re.findall(p, html, re.DOTALL)
                for match in matches:
                    # Extract URLs from JSON-like content
                    photo_urls = re.findall(r'https://images\.expcloud\.com/[^"\']+', match)
                    urls.extend(photo_urls)

            logger.info("After script extraction: %d total photos", len(urls))

        # Method 3: BeautifulSoup fallback for static img tags
        if len(urls) < 3:
            try:
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(html, "html.parser")

                for img in soup.find_all("img"):
                    # Check srcset first
                    srcset = img.get("srcset", "")
                    if "images.expcloud.com" in srcset:
                        parts = [part.strip() for part in srcset.split(",")]
                        for part in parts:
                            srcset_url = part.split()[0]
                            if srcset_url.startswith("http"):
                                urls.append(srcset_url)

                    # Check src
                    src = img.get("src", "")
                    if "images.expcloud.com" in src and src.startswith("http"):
                        urls.append(src)

                logger.info("After BeautifulSoup: %d total photos", len(urls))
            except Exception as e:
                logger.warning("BeautifulSoup parsing failed: %s", e)

        # Clean and deduplicate
        seen = set()
        clean_urls: List[str] = []
        for u in urls:
            if not u or u in seen:
                continue
            # Skip SVG
            if u.lower().endswith(".svg"):
                continue
            # Skip very small images (width < 200)
            if re.search(r"[?&]w=([0-9]{1,2})(?:&|$)", u):
                continue
            seen.add(u)
            clean_urls.append(u)

        # Prefer larger images - sort by width parameter
        def get_width(url: str) -> int:
            match = re.search(r"[?&]w=(\d+)", url)
            return int(match.group(1)) if match else 500  # default to medium

        clean_urls.sort(key=get_width, reverse=True)

        logger.info("Final count: %d high-res photos from listing", len(clean_urls))
        return clean_urls[:15]

    async def _upload_photos_to_storage(self, job_id: str, photo_urls: List[str]) -> List[str]:
        """Upload photos to Supabase Storage."""

        # Convert relative URLs to absolute Zoocasa URLs
        valid_urls: List[str] = []
        for url in photo_urls:
            if not isinstance(url, str):
                continue
            if url.startswith(("http://", "https://")):
                valid_urls.append(url)
            elif url.startswith("/"):
                # Relative path - convert to absolute Zoocasa URL
                valid_urls.append(f"https://www.zoocasa.com{url}")
                logger.info(
                    "Converted relative URL: %s -> https://www.zoocasa.com%s",
                    url,
                    url,
                )

        logger.info("Filtered %d URLs -> %d valid URLs", len(photo_urls), len(valid_urls))

        if not valid_urls:
            logger.warning("No valid photo URLs found (all were relative paths)")
            raise RuntimeError("No valid photo URLs to upload")

        uploaded_urls: List[str] = []

        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            for idx, url in enumerate(valid_urls):
                try:
                    logger.info("Downloading photo %d/%d: %s", idx + 1, len(valid_urls), url)
                    response = await client.get(url)
                    response.raise_for_status()

                    path = f"{job_id}/frame_{idx:03d}.jpg"
                    logger.info("Uploading to listing-photos/%s", path)

                    self.supabase.storage.from_("listing-photos").upload(  # type: ignore[attr-defined]
                        path,
                        response.content,
                        file_options={"content-type": "image/jpeg"},
                    )

                    pub = self.supabase.storage.from_("listing-photos").get_public_url(path)  # type: ignore[attr-defined]
                    public_url = pub.get("publicUrl") if isinstance(pub, dict) else pub
                    if public_url:
                        uploaded_urls.append(public_url)
                    logger.info("Successfully uploaded photo %d", idx + 1)
                except Exception as e:
                    logger.error("Failed to upload photo %d from %s: %s", idx, url, e)

        if not uploaded_urls:
            raise RuntimeError("Failed to upload any listing photos")

        logger.info("Successfully uploaded %d photos", len(uploaded_urls))
        return uploaded_urls

    async def _upload_video_to_storage(self, job_id: str, video_path: Path) -> str:
        """Upload rendered video file to Supabase Storage and return public URL."""

        path = f"{job_id}.mp4"
        with video_path.open("rb") as f:
            self.supabase.storage.from_("videos").upload(  # type: ignore[attr-defined]
                path,
                f,
                file_options={"content-type": "video/mp4"},
            )
        pub = (
            self.supabase.storage.from_("videos")  # type: ignore[attr-defined]
            .get_public_url(path)
        )

        # `get_public_url()` may return either:
        # 1) {"publicUrl": "..."} (dict)
        # 2) "..." (string URL)
        if isinstance(pub, dict):
            public_url = pub.get("publicUrl")
        else:
            public_url = pub

        if not public_url:
            raise RuntimeError("Supabase get_public_url returned empty value")

        return public_url

    async def _generate_aligned_script(
        self,
        scene_plan: List[Dict[str, Any]],
        job: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate a 30-second script roughly aligned with the scene sequence."""

        if not self.client:
            # Fallback to simple static script if Gemini is not configured
            return {
                "headline": "Your Dream Home Awaits",
                "voiceover_script": (
                    "Welcome to this beautiful property, featuring bright living spaces and modern finishes. "
                    "Enjoy generous bedrooms, stylish bathrooms, and inviting common areas perfect for everyday life "
                    "and entertaining. Reach out today to schedule a private viewing."
                ),
                "music_mood": "cinematic_luxury",
                "key_features": ["Bright living spaces", "Modern finishes", "Great location"],
            }

        scene_desc = "\n".join(
            f"{idx+1}. {scene.get('room_type','other').replace('_',' ').title()} "
            f"({scene['start_time']}-{scene['end_time']}s)"
            for idx, scene in enumerate(scene_plan)
        )

        listing_url = job.get("listing_url") or ""
        prompt = (
            "Create a 30-second real estate video script that matches the following scene sequence.\n\n"
            f"Listing URL (for context only, do not open): {listing_url}\n\n"
            "Scenes:\n"
            f"{scene_desc}\n\n"
            "Requirements:\n"
            "- 70-80 words total\n"
            "- Opening hook (0-5s): highlight exterior/entry\n"
            "- Middle (5-25s): walk through key rooms and features\n"
            "- Closing CTA (25-30s): invite viewer to book a showing\n\n"
            "Return ONLY JSON in this shape:\n"
            "{\n"
            '  \"headline\": \"Short catchy title\",\n'
            '  \"voiceover_script\": \"Full 70-80 word script matching scene timing\",\n'
            '  \"music_mood\": \"cinematic_luxury\",\n'
            '  \"key_features\": [\"feature1\", \"feature2\", \"feature3\"]\n'
            "}"
        )

        if not self.vertex_model:
            raise RuntimeError("Vertex AI not initialized")

        if self._vertex_client is None:
            response = self.vertex_model.generate_content(prompt)  # type: ignore[union-attr]
            text = getattr(response, "text", None)
        else:
            response = self._vertex_client.models.generate_content(  # type: ignore[union-attr]
                model=self.vertex_model,
                contents=prompt,
            )
            text = getattr(response, "text", None)

        if not text:
            raise RuntimeError("Gemini script generation response was empty")

        raw = text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("\n```", 1)[0]

        import json as _json

        return _json.loads(raw)
    
    async def process_video_job(self, job_id: str):
        """Process a video job through the intelligent photo-aware pipeline."""

        try:
            job = await self.get_video_job(job_id)
            if not job:
                logger.error("Job %s not found", job_id)
                return

            listing_url = job.get("listing_url") or ""
            # Use only statuses allowed by DB CHECK constraint
            await self.update_job_status(job_id, "generating_script", 10)

            # Step 1: Fetch photos from listing URL (or use existing manifest)
            photo_urls = await self._fetch_listing_photos(listing_url)
            if not photo_urls:
                raise RuntimeError("No photos found for listing_url")
            await self.update_job_status(job_id, "generating_script", 20)

            # Step 2: Upload photos to Supabase Storage and get public URLs
            uploaded_urls = await self._upload_photos_to_storage(job_id, photo_urls)
            if not uploaded_urls:
                raise RuntimeError("Failed to upload any listing photos")
            await self.update_job_status(job_id, "generating_script", 30)

            # Step 3: Classify photos with Gemini Vision
            logger.info("Classifying %d uploaded photos for job %s", len(uploaded_urls), job_id)
            photo_manifest = await self.photo_classifier.classify_photos(uploaded_urls)
            self._update_job_record(job_id, photo_manifest=photo_manifest)
            await self.update_job_status(job_id, "generating_script", 50)

            # Step 4: Plan scenes
            logger.info("Planning scenes for job %s", job_id)
            scene_plan = self.scene_planner.plan_scenes(photo_manifest, target_duration_sec=30)
            self._update_job_record(job_id, scene_plan=scene_plan)
            await self.update_job_status(job_id, "generating_script", 60)

            # Step 5: Generate script aligned with scenes
            script_data = await self._generate_aligned_script(scene_plan, job)
            if not script_data:
                raise RuntimeError("Failed to generate aligned script")
            await self.update_job_status(
                job_id,
                "script_generated",
                70,
                script_data=script_data,
            )

            # Step 6: Generate audio (placeholder for ElevenLabs)
            audio_url: Optional[str] = None
            await self.update_job_status(job_id, "generating_audio", 75, audio_url=audio_url)
            await self.update_job_status(job_id, "audio_generated", 80, audio_url=audio_url)

            # Step 7: Render video with ffmpeg
            logger.info("Rendering video for job %s", job_id)
            await self.update_job_status(job_id, "generating_video", 90)
            with tempfile.TemporaryDirectory() as tmpdir:
                renderer = VideoRenderer(Path(tmpdir))
                video_path = await renderer.render_video(
                    scene_plan=scene_plan,
                    audio_url=audio_url,
                    headline=script_data.get("headline", "Luxury Property"),
                    output_filename=f"{job_id}.mp4",
                )

                video_url = await self._upload_video_to_storage(job_id, video_path)

            await self.update_job_status(
                job_id,
                "completed",
                100,
                video_url=video_url,
                final_video_path=f"videos/{job_id}.mp4",
            )
            logger.info("Video job %s completed successfully: %s", job_id, video_url)

        except Exception as e:  # pragma: no cover - orchestration
            logger.exception("Error processing video job %s: %s", job_id, e)
            await self.update_job_status(job_id, "failed", 0, str(e))
    
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
            
            if _GENAI_SDK == "google-genai":
                if not self.client:
                    raise RuntimeError("Gemini client not initialized")
                _ = self.client.models.generate_content(model=self.model_id, contents=prompt)
            else:
                model = _genai.GenerativeModel(self.model_id)
                _ = model.generate_content(prompt)
            
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
