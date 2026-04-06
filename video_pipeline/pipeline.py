import asyncio
import functools
import logging
import subprocess
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
from .veo_renderer import VeoRenderer
from .listing_photos import extract_expcloud_photo_urls_from_html

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


def _tts_chunk_to_bytes(chunk: object) -> bytes:
    """ElevenLabs streams httpx byte chunks; tolerate buffer-like objects."""
    if isinstance(chunk, bytes):
        return chunk
    if isinstance(chunk, (bytearray, memoryview)):
        return bytes(chunk)
    try:
        return memoryview(chunk).tobytes()
    except TypeError:
        return bytes(chunk)


def _generate_google_tts_audio(text: str, voice_name: str, out_path: Path) -> None:
    """Google Cloud TTS — uses GOOGLE_APPLICATION_CREDENTIALS_JSON service account."""
    import json as _json
    from google.cloud import texttospeech  # type: ignore[import]
    from google.oauth2 import service_account  # type: ignore[import]

    creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON", "")
    client_kwargs: dict = {}
    if creds_json:
        creds = service_account.Credentials.from_service_account_info(
            _json.loads(creds_json),
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        client_kwargs["credentials"] = creds

    client = texttospeech.TextToSpeechClient(**client_kwargs)
    response = client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=text),
        voice=texttospeech.VoiceSelectionParams(language_code="en-US", name=voice_name),
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            sample_rate_hertz=24000,
        ),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(response.audio_content)
    if len(response.audio_content) < 800:
        raise RuntimeError(
            f"Google TTS returned too little audio ({len(response.audio_content)} bytes)"
        )


def _generate_gtts_audio(text: str, out_path: Path) -> None:
    """gTTS fallback — no API key required."""
    from gtts import gTTS  # type: ignore[import]

    tts = gTTS(text=text, lang="en", slow=False)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tts.save(str(out_path))
    if not out_path.exists() or out_path.stat().st_size < 800:
        raise RuntimeError("gTTS produced no output")


def _generate_elevenlabs_audio(text: str, voice_id: str, api_key: str, out_path: Path) -> None:
    """Synchronous ElevenLabs TTS call — run in executor."""
    from elevenlabs.client import ElevenLabs
    from elevenlabs import VoiceSettings

    client = ElevenLabs(api_key=api_key)
    stream = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id="eleven_turbo_v2_5",
        output_format="mp3_44100_128",
        voice_settings=VoiceSettings(
            stability=0.4,
            similarity_boost=0.8,
            style=0.0,
            use_speaker_boost=True,
        ),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with open(out_path, "wb") as f:
        for chunk in stream:
            if not chunk:
                continue
            b = _tts_chunk_to_bytes(chunk)
            if b:
                f.write(b)
                total += len(b)
    if total < 800:
        raise RuntimeError(
            f"ElevenLabs returned too little audio ({total} bytes); check API key, quota, and text length"
        )


def _normalize_script_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure voiceover_script is populated when the model uses alternate keys."""
    vo = data.get("voiceover_script")
    if isinstance(vo, str) and vo.strip():
        data["voiceover_script"] = vo.strip()
        return data
    for alt in ("voiceOverScript", "voice_over_script", "narration", "script"):
        v = data.get(alt)
        if isinstance(v, str) and v.strip():
            data["voiceover_script"] = v.strip()
            return data
    data["voiceover_script"] = ""
    return data


class VideoJobManager:
    """Manages video generation jobs with Supabase persistence."""

    def __init__(self):
        self.supabase = memory_store.supabase

        # Vertex AI Studio (API key) for JSON-aligned script generation — optional so the API
        # can boot without it (e.g. Railway only sets GOOGLE_APPLICATION_CREDENTIALS_JSON for Veo).
        import google.genai as genai

        self._vertex_client = None
        self.vertex_model = None
        vertex_key = (os.getenv("VERTEX_AI_API_KEY") or "").strip()
        if vertex_key:
            if hasattr(genai, "configure"):
                genai.configure(api_key=vertex_key)  # type: ignore[attr-defined]
                self.vertex_model = genai.GenerativeModel("gemini-2.5-flash-lite")  # type: ignore[attr-defined]
            else:
                self._vertex_client = genai.Client(api_key=vertex_key)  # type: ignore[attr-defined]
                self.vertex_model = "gemini-2.5-flash-lite"
            logger.info("Vertex AI Studio API key configured for script generation")
        else:
            logger.warning(
                "VERTEX_AI_API_KEY not set; video jobs will use fallback script text until it is set"
            )

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
    
    async def create_video_job(
        self,
        listing_url: str,
        customer_email: str,
        customer_name: Optional[str] = None,
        listing_data: Optional[Dict[str, Any]] = None,
        job_dir: Optional[Path] = None,
        job_id: Optional[str] = None,
    ) -> str:
        """Create a new video job and persist to database"""

        jid = job_id or str(uuid.uuid4())
        merged_listing: Dict[str, Any] = dict(listing_data or {})
        if job_dir is not None:
            merged_listing["_job_dir"] = str(Path(job_dir).resolve())

        job_data: Dict[str, Any] = {
            "id": jid,
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
            "final_video_path": None,
        }
        if merged_listing:
            job_data["listing_data"] = merged_listing

        if not self.supabase:
            logger.error("Cannot create video job: Supabase not configured")
            raise RuntimeError("Supabase not configured; set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY)")
        
        try:
            self.supabase.table("video_jobs").insert(job_data).execute()
            logger.info("Created video job: %s", jid)
            asyncio.create_task(self.process_video_job(jid))
            return jid
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

    async def _fetch_realtor_ca_photos(self, listing_url: str) -> List[str]:
        """Extract photos from a realtor.ca listing using curl_cffi (Chrome impersonation) to bypass Cloudflare."""
        import re as _re
        m = _re.search(r"/real-estate/(\d+)", listing_url)
        if not m:
            return []
        mls = m.group(1)

        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://www.realtor.ca",
            "Referer": listing_url,
        }
        data = {
            "CultureId": "1", "ApplicationId": "1",
            "MlsNumber": mls, "Version": "7.0", "TransactionTypeId": "2",
        }

        # Try curl_cffi with PropertyDetails_Get (returns full media gallery)
        try:
            from curl_cffi import requests as cffi_requests  # type: ignore
            import asyncio as _asyncio

            def _do_details():
                r = cffi_requests.post(
                    "https://api2.realtor.ca/Listing.svc/PropertyDetails_Get",
                    headers=headers,
                    data={"ApplicationId": "1", "CultureId": "1",
                          "PropertyId": mls, "ReferenceNumber": "0"},
                    impersonate="chrome120", timeout=15,
                )
                return r.status_code, r.json() if r.status_code == 200 else {}

            status, body = await _asyncio.to_thread(_do_details)
            if status == 200:
                # Full gallery under Media or Property.Photo
                media = body.get("Media") or body.get("Property", {}).get("Photo") or []
                urls = []
                for p in media:
                    u = (p.get("HighResPath") or p.get("MedResPath") or
                         p.get("LargePhotoUrl") or p.get("url") or "")
                    if u.startswith("http"):
                        urls.append(u)
                if urls:
                    logger.info("realtor.ca PropertyDetails_Get returned %d photos for MLS %s", len(urls), mls)
                    return urls[:15]
        except Exception as e:
            logger.warning("realtor.ca PropertyDetails_Get failed for MLS %s: %s", mls, e)

        # Fallback: PropertySearch_Post (summary — fewer photos)
        try:
            from curl_cffi import requests as cffi_requests  # type: ignore
            import asyncio as _asyncio

            def _do_post():
                r = cffi_requests.post(
                    "https://api2.realtor.ca/Listing.svc/PropertySearch_Post",
                    headers=headers, data=data, impersonate="chrome120", timeout=15,
                )
                return r.status_code, r.json() if r.status_code == 200 else {}

            status, body = await _asyncio.to_thread(_do_post)
            if status == 200:
                results = body.get("Results", []) or []
                if results:
                    photos = results[0].get("Property", {}).get("Photo", []) or []
                    urls = [p.get("HighResPath") or p.get("MedResPath") or "" for p in photos]
                    urls = [u for u in urls if u.startswith("http")]
                    if urls:
                        logger.info("realtor.ca PropertySearch_Post returned %d photos for MLS %s", len(urls), mls)
                        return urls[:15]
        except Exception as e:
            logger.warning("realtor.ca curl_cffi photo fetch failed for MLS %s: %s", mls, e)

        # Fallback: scrape cdn.realtor.ca URLs from the listing page HTML
        try:
            from curl_cffi import requests as cffi_requests  # type: ignore
            import asyncio as _asyncio

            def _get_html():
                r = cffi_requests.get(listing_url, impersonate="chrome120", timeout=20)
                return r.text

            html = await _asyncio.to_thread(_get_html)
            found = _re.findall(r"https://cdn\.realtor\.ca/[^\s\"\'<>)]+\.(?:jpg|jpeg|webp|png)", html, _re.IGNORECASE)
            seen, urls = set(), []
            for u in found:
                if u not in seen and "lowres" not in u.lower():
                    seen.add(u); urls.append(u)
            if urls:
                logger.info("realtor.ca HTML scrape found %d photos", len(urls))
                return urls[:15]
        except Exception as e:
            logger.warning("realtor.ca HTML photo scrape failed: %s", e)

        return []

    async def _fetch_listing_photos(self, listing_url: str) -> List[str]:
        """Fetch high-resolution photo URLs from a listing page (Zoocasa or realtor.ca)."""
        if not listing_url:
            return []

        if "realtor.ca" in listing_url:
            return await self._fetch_realtor_ca_photos(listing_url)

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
                resp = await client.get(listing_url)
                resp.raise_for_status()
                html = resp.text
        except Exception as e:
            logger.error("Failed to fetch listing HTML for %s: %s", listing_url, e)
            return []

        return extract_expcloud_photo_urls_from_html(html, max_urls=15)

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

    async def _upload_local_photos_to_storage(
        self, job_id: str, paths: List[Path]
    ) -> List[str]:
        """Upload on-disk listing photos to Supabase Storage and return public URLs."""

        uploaded_urls: List[str] = []
        for idx, p in enumerate(paths):
            try:
                data = p.read_bytes()
                if len(data) < 1000:
                    logger.warning("Skipping tiny local photo %s", p)
                    continue
                suffix = p.suffix.lower() if p.suffix else ".jpg"
                if suffix not in (".jpg", ".jpeg", ".png", ".webp"):
                    suffix = ".jpg"
                ext_for_name = ".jpg" if suffix == ".jpeg" else suffix
                path = f"{job_id}/frame_{idx:03d}{ext_for_name}"
                ctype = {
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".png": "image/png",
                    ".webp": "image/webp",
                }.get(suffix, "image/jpeg")

                logger.info(
                    "Uploading local photo %d/%d → listing-photos/%s",
                    idx + 1,
                    len(paths),
                    path,
                )
                self.supabase.storage.from_("listing-photos").upload(  # type: ignore[attr-defined]
                    path,
                    data,
                    file_options={"content-type": ctype},
                )
                pub = self.supabase.storage.from_("listing-photos").get_public_url(path)  # type: ignore[attr-defined]
                public_url = pub.get("publicUrl") if isinstance(pub, dict) else pub
                if public_url:
                    uploaded_urls.append(public_url)
            except Exception as e:
                logger.error("Failed to upload local photo %s: %s", p, e)

        if not uploaded_urls:
            raise RuntimeError("Failed to upload any custom-upload photos")
        logger.info("Successfully uploaded %d custom photos", len(uploaded_urls))
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
        ld_raw = job.get("listing_data")
        if isinstance(ld_raw, str):
            import json as _json

            try:
                ld: Dict[str, Any] = _json.loads(ld_raw)
            except Exception:
                ld = {}
        else:
            ld = ld_raw if isinstance(ld_raw, dict) else {}
        visible_ld = {k: v for k, v in ld.items() if not str(k).startswith("_")}
        facts_block = ""
        if visible_ld:
            facts_block = f"Property facts (use verbatim where helpful): {visible_ld}\n\n"

        prompt = (
            "Create a 30-second real estate video script that matches the following scene sequence.\n\n"
            f"Listing URL (for context only, do not open): {listing_url}\n\n"
            f"{facts_block}"
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

        return _normalize_script_json(_json.loads(raw))
    
    async def process_video_job(self, job_id: str):
        """Process a video job through the intelligent photo-aware pipeline."""

        try:
            job = await self.get_video_job(job_id)
            if not job:
                logger.error("Job %s not found", job_id)
                return

            listing_url = job.get("listing_url") or ""
            listing_data_raw = job.get("listing_data")
            if isinstance(listing_data_raw, str):
                import json as _json

                try:
                    listing_data_ctx: Dict[str, Any] = _json.loads(listing_data_raw)
                except Exception:
                    listing_data_ctx = {}
            else:
                listing_data_ctx = (
                    listing_data_raw if isinstance(listing_data_raw, dict) else {}
                )

            logger.info(
                "video_pipeline_entry=VideoJobManager.process_video_job job_id=%s url=%s",
                job_id,
                (listing_url or "")[:120],
            )
            # Use only statuses allowed by DB CHECK constraint
            await self.update_job_status(job_id, "generating_script", 10)

            # Step 1–2: Resolve photos (scrape or custom disk upload) → Supabase URLs
            if listing_url == "custom_upload":
                base = Path(listing_data_ctx.get("_job_dir", "") or "")
                photos_dir = base / "photos"
                if not photos_dir.is_dir():
                    raise RuntimeError("Custom upload photos directory missing")
                paths_set: List[Path] = []
                for pat in ("*.jpg", "*.jpeg", "*.png", "*.webp", "*.JPG", "*.PNG"):
                    paths_set.extend(photos_dir.glob(pat))
                paths = sorted({p.resolve() for p in paths_set}, key=lambda p: p.name.lower())
                if len(paths) < 4:
                    raise RuntimeError("Fewer than 4 photos found for custom upload")
                await self.update_job_status(job_id, "generating_script", 20)
                uploaded_urls = await self._upload_local_photos_to_storage(job_id, paths)
            else:
                photo_urls = await self._fetch_listing_photos(listing_url)
                if not photo_urls:
                    raise RuntimeError("No photos found for listing_url")
                await self.update_job_status(job_id, "generating_script", 20)
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

            # Step 6–7: ElevenLabs voiceover (inside job temp dir), render, mux audio
            video_renderer = (os.getenv("VIDEO_RENDERER") or "ffmpeg").strip().lower()
            vertex_creds = (os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON") or "").strip()

            audio_url: Optional[str] = None
            loop = asyncio.get_running_loop()

            with tempfile.TemporaryDirectory() as tmpdir:
                work_dir = Path(tmpdir)

                voice = listing_data_ctx.get("voice", "female_luxury")
                google_voice_map = {
                    "female_luxury": "en-US-Neural2-F",
                    "male_luxury": "en-US-Neural2-D",
                    "male_deep": "en-US-Neural2-J",
                }
                elevenlabs_voice_map = {
                    "female_luxury": "21m00Tcm4TlvDq8ikWAM",
                    "male_luxury": "29vD33N1CtxCmqQRPOHJ",
                    "male_deep": "ErXwobaYiN019PkySvjV",
                }
                google_voice_name = google_voice_map.get(str(voice), google_voice_map["female_luxury"])
                elevenlabs_voice_id = elevenlabs_voice_map.get(str(voice), elevenlabs_voice_map["female_luxury"])
                elevenlabs_key = (os.getenv("ELEVENLABS_API_KEY") or "").strip()
                if elevenlabs_key.lower().startswith("your_"):
                    elevenlabs_key = ""
                vo_text = (script_data.get("voiceover_script") or "").strip()

                audio_path: Optional[Path] = None
                logger.info(
                    "Voiceover precheck job=%s: script_chars=%d",
                    job_id,
                    len(vo_text),
                )

                if vo_text:
                    await self.update_job_status(job_id, "generating_audio", 72)
                    audio_path = work_dir / "voiceover.mp3"

                    # 1. Google Cloud TTS (primary — uses existing service account)
                    try:
                        await loop.run_in_executor(
                            None,
                            functools.partial(
                                _generate_google_tts_audio,
                                vo_text,
                                google_voice_name,
                                audio_path,
                            ),
                        )
                        logger.info("Voiceover generated via Google TTS: %d bytes", audio_path.stat().st_size)
                    except Exception as e:
                        logger.warning("Google TTS failed: %s — trying ElevenLabs", e)
                        audio_path = None

                    # 2. ElevenLabs fallback
                    if audio_path is None and elevenlabs_key:
                        try:
                            audio_path = work_dir / "voiceover.mp3"
                            await loop.run_in_executor(
                                None,
                                functools.partial(
                                    _generate_elevenlabs_audio,
                                    vo_text,
                                    elevenlabs_voice_id,
                                    elevenlabs_key,
                                    audio_path,
                                ),
                            )
                            logger.info("Voiceover generated via ElevenLabs: %d bytes", audio_path.stat().st_size)
                        except Exception as e:
                            logger.warning("ElevenLabs voiceover failed: %s — trying gTTS", e)
                            audio_path = None

                    # 3. gTTS last resort
                    if audio_path is None:
                        try:
                            audio_path = work_dir / "voiceover.mp3"
                            await loop.run_in_executor(
                                None,
                                functools.partial(_generate_gtts_audio, vo_text, audio_path),
                            )
                            logger.info("Voiceover generated via gTTS: %d bytes", audio_path.stat().st_size)
                        except Exception as e:
                            logger.warning("gTTS fallback failed: %s — continuing without audio", e)
                            audio_path = None

                    if audio_path and audio_path.exists():
                        try:
                            with audio_path.open("rb") as af:
                                self.supabase.storage.from_("videos").upload(  # type: ignore[attr-defined]
                                    f"{job_id}_voiceover.mp3",
                                    af,
                                    file_options={"content-type": "audio/mpeg"},
                                )
                            pub = self.supabase.storage.from_("videos").get_public_url(  # type: ignore[attr-defined]
                                f"{job_id}_voiceover.mp3"
                            )
                            audio_url = pub.get("publicUrl") if isinstance(pub, dict) else pub
                            logger.info("Voiceover uploaded: %s", audio_url)
                        except Exception as up_e:
                            logger.warning("Voiceover storage upload failed: %s", up_e)
                else:
                    logger.warning(
                        "Skipping voiceover job=%s: voiceover_script empty after script generation",
                        job_id,
                    )

                await self.update_job_status(
                    job_id,
                    "audio_generated",
                    78,
                    audio_url=audio_url,
                )
                await self.update_job_status(job_id, "generating_video", 80)

                if video_renderer == "veo" and vertex_creds:
                    logger.info("Using Veo renderer (service account credentials found)")
                    renderer: Any = VeoRenderer(work_dir=work_dir)
                else:
                    if video_renderer == "veo":
                        logger.warning(
                            "VIDEO_RENDERER=veo but GOOGLE_APPLICATION_CREDENTIALS_JSON not set; "
                            "falling back to ffmpeg"
                        )
                    renderer = VideoRenderer(work_dir)

                logger.info(
                    "Rendering video for job %s (backend=%s)",
                    job_id,
                    "veo" if video_renderer == "veo" and vertex_creds else "ffmpeg",
                )

                logger.info("scene_plan count before render_video: %d", len(scene_plan))
                logger.info(
                    "scene_plan sample photo_url: %s",
                    [str(s.get("photo_url", ""))[:100] for s in scene_plan[:3]],
                )
                video_path = await renderer.render_video(
                    scene_plan=scene_plan,
                    audio_url=None,
                    headline=script_data.get("headline", "Luxury Property"),
                    output_filename=f"{job_id}.mp4",
                )

                if (
                    audio_path
                    and audio_path.exists()
                    and audio_path.stat().st_size > 1000
                    and video_path
                    and video_path.exists()
                ):
                    muxed = work_dir / f"{job_id}_final.mp4"
                    mux_cmd = [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(video_path),
                        "-i",
                        str(audio_path),
                        "-map",
                        "0:v:0",
                        "-map",
                        "1:a:0",
                        "-c:v",
                        "copy",
                        "-c:a",
                        "aac",
                        "-b:a",
                        "192k",
                        "-shortest",
                        str(muxed),
                    ]
                    mux_res = await loop.run_in_executor(
                        None,
                        functools.partial(
                            subprocess.run,
                            mux_cmd,
                            capture_output=True,
                            text=True,
                            timeout=120,
                        ),
                    )
                    if mux_res.returncode == 0:
                        video_path = muxed
                        logger.info("Voiceover muxed into final video")
                    else:
                        err_tail = (mux_res.stderr or mux_res.stdout or "")[-2000:]
                        logger.warning("Voiceover mux failed (rc=%s): %s", mux_res.returncode, err_tail)
                        mux_cmd_alt = [
                            "ffmpeg",
                            "-y",
                            "-i",
                            str(video_path),
                            "-i",
                            str(audio_path),
                            "-map",
                            "0:v",
                            "-map",
                            "1:a:0",
                            "-c:v",
                            "copy",
                            "-c:a",
                            "aac",
                            "-b:a",
                            "192k",
                            "-shortest",
                            str(muxed),
                        ]
                        mux_res2 = await loop.run_in_executor(
                            None,
                            functools.partial(
                                subprocess.run,
                                mux_cmd_alt,
                                capture_output=True,
                                text=True,
                                timeout=120,
                            ),
                        )
                        if mux_res2.returncode == 0:
                            video_path = muxed
                            logger.info("Voiceover muxed (alternate stream mapping)")
                        else:
                            logger.warning(
                                "Voiceover alternate mux failed (rc=%s): %s",
                                mux_res2.returncode,
                                (mux_res2.stderr or mux_res2.stdout or "")[-2000:],
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
async def create_video_job(
    listing_url: str,
    customer_email: str,
    customer_name: Optional[str] = None,
    listing_data: Optional[dict] = None,
    job_dir: Optional[Path] = None,
    job_id: Optional[str] = None,
) -> str:
    """Create a new video job"""
    return await video_job_manager.create_video_job(
        listing_url=listing_url,
        customer_email=customer_email,
        customer_name=customer_name,
        listing_data=listing_data,
        job_dir=job_dir,
        job_id=job_id,
    )

async def get_video_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get video job status"""
    return await video_job_manager.get_video_job(job_id)

async def process_pending_job(job_id: str) -> None:
    """Process an already-inserted pending job. Called by the video-worker service."""
    await video_job_manager.process_video_job(job_id)

# Legacy function for compatibility
def generate_script(listing_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate script from listing data (sync version for demo)"""
    return {
        "headline": "Your Dream Home Awaits!",
        "voiceover_script": f"Welcome to this beautiful property at {listing_data.get('address', 'Unknown Address')}. This {listing_data.get('beds', '3')} bedroom, {listing_data.get('baths', '2')} bathroom home offers {listing_data.get('sqft', '1,500')} square feet of living space. Priced at {listing_data.get('price', '$899,000')}, this is an incredible opportunity in today's market.",
        "music_mood": "upbeat_inspiring",
        "key_features": ["Great location", "Modern amenities", "Spacious rooms", "Excellent value"]
    }
