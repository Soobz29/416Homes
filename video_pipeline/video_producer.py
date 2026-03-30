"""
Video Producer — Full pipeline for creating luxury listing videos.

Pipeline (Veo 3 / Flow mode):
  1. Download listing photos from the URL
  2. Generate voiceover with ElevenLabs
  3. Generate background music with Suno (via kie.ai) — optional
  4A. Enhance photos with Flow (gemini-2.5-flash-image) — luxury styling
  4B. Generate cinematic clips with Veo 3 (image-to-video, 6s each)
  4C. Fallback: Ken Burns effects with ffmpeg if Veo unavailable
  5. Assemble final video (clips + voiceover + music + captions)

  Env (produce_video / Veo): VEO_FALLBACK_MODE=per_shot (default) or uniform_kb —
  if any Veo clip fails, re-render every shot with Ken Burns for a consistent look.
  VEO_CLIP_RETRIES — extra per-shot Veo attempts after the batch run (default 1).

Dependencies: ffmpeg (system), httpx, Pillow, google-genai
"""

import asyncio
import base64
import logging
import os
import re
import json
import time
import uuid
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, date

import httpx
from dotenv import load_dotenv
from listing_agent.activity_log import log_activity
from video_pipeline.listing_photos import extract_expcloud_photo_urls_from_html

# Optional: Try to import PIL for image processing
try:
    from PIL import Image
except ImportError:
    Image = None

load_dotenv()
logger = logging.getLogger(__name__)

# ── Active video job tracker (shared state for Telegram /videostatus) ─────
_active_jobs: Dict[str, Dict[str, Any]] = {}

def get_active_jobs() -> Dict[str, Dict[str, Any]]:
    return dict(_active_jobs)

def _update_job_tracker(job_id: str, **kwargs):
    if job_id not in _active_jobs:
        _active_jobs[job_id] = {
            "started_at": datetime.utcnow().isoformat(),
            "step": "initializing",
            "detail": "",
            "photos_total": 0,
            "photos_downloaded": 0,
            "clips_total": 0,
            "clips_done": 0,
            "voiceover": False,
            "music": False,
            "enhanced": 0,
            "percent": 0,
            "address": "",
            "status": "running",
        }
    _active_jobs[job_id].update(kwargs)

def _remove_job_tracker(job_id: str):
    _active_jobs.pop(job_id, None)

# ── Config ──────────────────────────────────────────────────────────────────
OUTPUT_DIR = Path("video_pipeline/output")
TEMP_DIR = Path("video_pipeline/temp")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
SUNO_API_KEY = os.getenv("SUNO_API_KEY", "")

# Veo cost tracking
VEO_DAILY_LIMIT_CAD = float(os.getenv("VEO_DAILY_BUDGET_CAD", "5.0"))
VEO_COST_PER_VIDEO = 2.50  # Estimate: 5 clips × $0.50/clip
VEO_TRACKING_FILE = Path("video_pipeline/veo_spend_tracking.json")


def _load_veo_spend() -> dict:
    """Load Veo spend tracking from file."""
    if VEO_TRACKING_FILE.exists():
        try:
            return json.loads(VEO_TRACKING_FILE.read_text())
        except Exception:
            pass
    return {"date": str(date.today()), "spend": 0.0}


def _save_veo_spend(data: dict):
    """Save Veo spend tracking to file."""
    try:
        VEO_TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Parent may already exist or be current directory
        pass
    VEO_TRACKING_FILE.write_text(json.dumps(data, indent=2))


def check_veo_budget_available() -> bool:
    """Check if we're under daily Veo budget."""
    data = _load_veo_spend()
    today = str(date.today())

    # Reset spend if new day
    if data.get("date") != today:
        data = {"date": today, "spend": 0.0}
        _save_veo_spend(data)

    current_spend = data.get("spend", 0.0)

    if current_spend + VEO_COST_PER_VIDEO > VEO_DAILY_LIMIT_CAD:
        logger.warning(
            f"Veo daily budget exhausted: "
            f"CA${current_spend:.2f}/CA${VEO_DAILY_LIMIT_CAD:.2f}"
        )
        return False

    return True


def record_veo_usage():
    """Record Veo usage for budget tracking."""
    data = _load_veo_spend()
    data["spend"] = float(data.get("spend", 0.0)) + VEO_COST_PER_VIDEO
    _save_veo_spend(data)
    logger.info(f"Veo spend recorded: CA${data['spend']:.2f} today")


def ensure_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 0: Smart Photo Intelligence — classify, filter, and order photos
# ══════════════════════════════════════════════════════════════════════════════

WALKTHROUGH_ORDER = [
    "aerial",
    "exterior_front",
    "exterior_side",
    "entrance",
    "foyer",
    "living_room",
    "dining_room",
    "kitchen",
    "family_room",
    "bedroom_primary",
    "bedroom",
    "bathroom_ensuite",
    "bathroom",
    "laundry",
    "basement",
    "garage",
    "backyard",
    "pool",
    "amenity",
    "other",
]

MIN_PHOTO_BYTES = 8_000  # skip anything under 8 KB

# Walkthrough sorts these first; without a shared cap, MAX_VIDEO_PHOTOS=5 can be
# all aerial + exterior angles before any living/kitchen/bedroom.
EXTERIOR_WALKTHROUGH_ROOMS = frozenset({"aerial", "exterior_front", "exterior_side"})


async def smart_order_photos(photos: List[Path], listing_data: dict) -> List[Path]:
    """
    Send all photos to Gemini Vision in one call.  Gemini classifies each
    photo into a room type and returns a quality score.  Photos are then:
      1. Filtered  — remove duplicates, non-property images, tiny files
      2. Ordered   — natural walkthrough: exterior → entrance → rooms → yard
      3. Capped    — MAX_VIDEO_PHOTOS limit applied after ordering
    """
    if not photos:
        return photos

    # ── Pre-filter: skip tiny / corrupt files ──
    valid = [p for p in photos if p.exists() and p.stat().st_size >= MIN_PHOTO_BYTES]
    if not valid:
        return photos
    logger.info(f"[smart_order] {len(valid)} photos pass size filter (of {len(photos)})")

    try:
        from google import genai
        import PIL.Image, io, json as _json

        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            return valid

        client = genai.Client(api_key=api_key)

        room_types = ", ".join(WALKTHROUGH_ORDER)
        prompt = (
            f"You are a real estate photo classifier. I will show you {len(valid)} listing photos.\n\n"
            f"For EACH photo (in order), return its classification.\n\n"
            f"Room types (pick the BEST match): {room_types}\n\n"
            f"Return ONLY a valid JSON array of objects, one per photo:\n"
            f'[{{"index": 0, "room": "exterior_front", "quality": 8, "description": "front of house with driveway"}}, ...]\n\n'
            f"Rules:\n"
            f"- 'room' must be one of the types listed above\n"
            f"- 'quality' is 1-10 (10 = best composition, lighting, sharpness)\n"
            f"- 'description' is a short 5-10 word description of what's visible\n"
            f"- If a photo is NOT a property photo (logo, map, floorplan, agent headshot), set room to 'other' and quality to 1\n"
            f"- If two photos show the same room from very similar angles, give the worse one quality 1\n"
        )

        contents: list = [prompt]
        for photo_path in valid:
            try:
                img = PIL.Image.open(io.BytesIO(photo_path.read_bytes()))
                if img.width > 768:
                    ratio = 768 / img.width
                    img = img.resize((768, int(img.height * ratio)))
                contents.append(img)
            except Exception:
                pass

        if len(contents) < 2:
            return valid

        resp = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=contents,
        )
        text = resp.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        classifications = _json.loads(text)
        if not isinstance(classifications, list):
            logger.warning("[smart_order] Gemini returned non-list, skipping")
            return valid

        n = len(valid)
        dict_entries = [e for e in classifications if isinstance(e, dict)]
        if len(dict_entries) == n:
            indices = [e.get("index", -1) for e in dict_entries]
            perm_ok = (
                all(isinstance(i, int) and 0 <= i < n for i in indices)
                and len(set(indices)) == n
            )
            if perm_ok:
                dict_entries = sorted(
                    dict_entries, key=lambda e: int(e.get("index", 0))
                )
            else:
                for k, e in enumerate(dict_entries):
                    e["index"] = k
                logger.info(
                    "[smart_order] Positional index mapping (model indices missing or non-permutation)"
                )
            classifications = dict_entries

        # ── Build ordered list ──
        scored: List[dict] = []
        for entry in classifications:
            if not isinstance(entry, dict):
                continue
            idx = entry.get("index", -1)
            if idx < 0 or idx >= len(valid):
                continue
            room = entry.get("room", "other")
            quality = entry.get("quality", 5)
            desc = entry.get("description", "")

            if room not in WALKTHROUGH_ORDER:
                room = "other"

            # Skip junk
            if quality <= 2:
                logger.info(f"  [smart_order] Skipping photo {idx+1}: quality {quality} ({desc})")
                continue

            order_rank = WALKTHROUGH_ORDER.index(room)
            scored.append({
                "path": valid[idx],
                "room": room,
                "quality": quality,
                "order": order_rank,
                "desc": desc,
            })

        # Sort by walkthrough order, then by quality descending within same room
        scored.sort(key=lambda x: (x["order"], -x["quality"]))

        max_exterior = max(1, int(os.getenv("MAX_WALKTHROUGH_EXTERIOR", "2") or "2"))

        # Deduplicate: keep only the best photo per room type
        seen_rooms: Dict[str, int] = {}
        exterior_slots_used = 0
        final: List[Path] = []
        for s in scored:
            room = s["room"]
            if room in EXTERIOR_WALKTHROUGH_ROOMS and exterior_slots_used >= max_exterior:
                logger.info(
                    f"  [smart_order] Exterior cap ({max_exterior}): skip {room} — {s['desc']}"
                )
                continue
            count = seen_rooms.get(room, 0)
            # Allow max 2 photos of same room type (e.g. two bedrooms)
            if room in ("bedroom", "bathroom", "other") or count < 1:
                final.append(s["path"])
                seen_rooms[room] = count + 1
                if room in EXTERIOR_WALKTHROUGH_ROOMS:
                    exterior_slots_used += 1
                logger.info(f"  [smart_order] #{len(final)}: {s['room']} (q={s['quality']}) - {s['desc']}")
            else:
                logger.info(f"  [smart_order] Duplicate {room} skipped: {s['desc']}")

        if not final:
            return valid

        logger.info(f"[smart_order] Final order: {len(final)} photos ({' -> '.join(s['room'] for s in scored if s['path'] in final)})")
        return final

    except Exception as e:
        logger.warning(f"[smart_order] Classification failed, using original order: {e}")
        return valid


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 1: Download listing photos
# ══════════════════════════════════════════════════════════════════════════════

def _secure_download_drission(img_urls: List[str], photos_dir: Path) -> List[Path]:
    """Download images using DrissionPage to match browser fingerprint."""
    from scraper.browser_util import create_browser
    page = create_browser(headless=True)
    downloaded = []
    
    for i, url in enumerate(img_urls[:15]):
        try:
            # Use DrissionPage's download method
            res = page.download(url, str(photos_dir), f"photo_{i+1}.jpg")
            if res[0]: # Success
                p = Path(res[1])
                downloaded.append(p)
                size = p.stat().st_size if p.exists() else 0
                log_activity("DEBUG", f"Photo URL: {url[:60]}, size: {size} bytes")
                logger.info(f"  ✅ Securely downloaded photo {i+1}: {url[:60]}...")
            else:
                logger.warning(f"  Failed to download photo {i+1}: {res[1]}")
        except Exception as e:
            logger.warning(f"  Drission download failed for {url}: {e}")
            
    page.quit()
    return downloaded

async def download_listing_photos(url: str, job_dir: Path, address: Optional[str] = None, provided_urls: Optional[List[str]] = None) -> List[Path]:
    """
    Scrape listing page and download photos.
    Uses DrissionPage to load the page, find image URLs, and download them securely.
    """
    photos_dir = job_dir / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)

    try:
        if provided_urls:
            logger.info(f"Using {len(provided_urls)} pre-provided photo URLs...")
            photo_urls = provided_urls
        elif "condos.ca" in url:
            logger.info("Using dedicated condos.ca image downloader...")
            downloaded_files = await asyncio.to_thread(_scrape_and_download_images_condos, url, str(photos_dir))
            return [Path(p) for p in downloaded_files]
        elif "zoocasa.com" in url.lower():
            logger.info("Using Zoocasa HTML expcloud extraction (gallery order)...")
            photo_urls = []
            try:
                async with httpx.AsyncClient(
                    follow_redirects=True,
                    timeout=20,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    },
                ) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    photo_urls = extract_expcloud_photo_urls_from_html(resp.text, max_urls=15)
            except Exception as e:
                logger.warning("Zoocasa httpx fetch failed: %s", e)
            if len(photo_urls) < 4:
                logger.info(
                    "Zoocasa expcloud found fewer than 4 images; falling back to browser scrape"
                )
                photo_urls = await asyncio.to_thread(_scrape_photo_urls, url)
        else:
            photo_urls = await asyncio.to_thread(_scrape_photo_urls, url)
            
            if len(photo_urls) < 4 and address:
                logger.info(f"Found {len(photo_urls)} photos from URL. Trying Google Image Search for {address}...")
                google_urls = await asyncio.to_thread(_scrape_google_images, address)
                for g_url in google_urls:
                    if g_url not in photo_urls:
                        photo_urls.append(g_url)

        if not photo_urls:
            logger.warning("No photos found, using placeholder")
            return []

        # Download up to 6 photos securely
        downloaded = await asyncio.to_thread(_secure_download_drission, photo_urls, photos_dir)
        
        # Fallback to httpx if Drission failed completely
        if not downloaded:
            logger.info("Drission download failed or returned no photos, falling back to httpx...")
            async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}) as client:
                for i, img_url in enumerate(photo_urls[:15]):
                    try:
                        resp = await client.get(img_url)
                        if resp.status_code == 200 and len(resp.content) > 5000:
                            photo_path = photos_dir / f"photo_fallback_{i+1}.jpg"
                            photo_path.write_bytes(resp.content)
                            downloaded.append(photo_path)
                            log_activity("DEBUG", f"Photo URL (Fallback): {img_url[:60]}, size: {len(resp.content)} bytes")
                    except: continue

        logger.info(f"Successfully sourced {len(downloaded)} photos")
        return downloaded

    except Exception as e:
        logger.error(f"Photo sourcing failed: {e}")
        return []


def _scrape_and_download_images_condos(listing_url: str, output_dir: str) -> List[str]:
    """
    Extracts high-res image URLs from condos.ca JSON payload and downloads them securely.
    """
    import re
    import json
    import os
    from scraper.browser_util import create_browser
    
    print(f"🔍 Loading listing: {listing_url}")
    page = create_browser(headless=False)
    page.get(listing_url)
    page.wait.load_start()
    
    os.makedirs(output_dir, exist_ok=True)
    downloaded_files = []
    
    html_content = page.html
    match = re.search(r'window\.__REACT_QUERY_STATE__\s*=\s*({.*?});', html_content)
    
    if not match:
        print("⚠️ Could not find the JSON payload. Site layout may have changed.")
        page.quit()
        return downloaded_files
        
    try:
        # Replace JS 'undefined' with JSON 'null'
        json_str = re.sub(r':\s*undefined\b', ': null', match.group(1))
        data = json.loads(json_str)
        listing_data = data['queries'][0]['state']['data']['response']['data']['data']
        
        mls = listing_data.get('mls_number')
        base_url = listing_data.get('photo_base_url') 
        count = listing_data.get('photo_count', 0)
        version = listing_data.get('photo_version', 1)
        
        if not all([mls, base_url, count]):
            print("⚠️ Missing data required to build URLs.")
            page.quit()
            return downloaded_files

        print(f"✅ Found {count} images in JSON payload. Starting secure download...")
        
        # Limit to first 6 photos for video production
        for i in range(1, min(count + 1, 7)):
            img_url = f"{base_url}{mls}_{i}.jpg?width=1920&v={version}"
            file_name = f"{mls}_photo_{i}.jpg"
            
            try:
                result = page.download(
                    img_url, 
                    goal_path=output_dir, 
                    rename=file_name
                )
                
                # DrissionPage download usually returns (success, path_or_info)
                success = False
                if isinstance(result, tuple) and len(result) >= 1:
                    success = result[0]
                elif result:
                    success = True

                if success and os.path.exists(os.path.join(output_dir, file_name)):
                    downloaded_files.append(os.path.join(output_dir, file_name))
                    print(f"  ⬇️ Downloaded: {file_name}")
                else:
                    print(f"  ❌ Failed to download: {file_name}, Result: {result}")
            except Exception as e:
                print(f"  ⚠️ Error downloading {img_url}: {e}")
                
        print(f"🎉 Successfully saved {len(downloaded_files)} photos to {output_dir}")
    except Exception as e:
        print(f"❌ Error parsing JSON or downloading: {e}")
    finally:
        page.quit()

    return downloaded_files


def _scrape_photo_urls(url: str) -> List[str]:
    """Use DrissionPage to find listing photo URLs."""
    try:
        from scraper.browser_util import create_browser
        
        # Realtor.ca optimization: Use image list view for all photos
        if "realtor.ca" in url.lower() and "view=imagelist" not in url:
            if "?" in url:
                url += "&view=imagelist"
            else:
                url += "?view=imagelist"
            logger.info(f"Converting Realtor.ca URL to image list view: {url}")

        page = create_browser(headless=False)
        page.get(url, retry=2, interval=2, timeout=25)
        time.sleep(8)
        
        # Find all large images on the page
        img_urls = []
        all_imgs = page.eles('tag:img')

        for img in all_imgs:
            src = img.attr('src') or ''
            srcset = img.attr('srcset') or ''

            # Use srcset for highest quality if available
            if srcset:
                # Get the largest image from srcset
                parts = srcset.split(',')
                best = parts[-1].strip().split(' ')[0]
                if best.startswith('http') and '/photos/' in best or 'listing' in best.lower() or 'property' in best.lower():
                    img_urls.append(best)
                    continue

            if src.startswith('http') and any(kw in src.lower() for kw in ['photo', 'listing', 'property', 'image', 'cdn', 'media']):
                # Skip tiny icons/logos and SVGs
                if '.svg' in src.lower():
                    continue
                width = img.attr('width')
                if width and int(width) < 100:
                    continue
                img_urls.append(src)

        # Realtor.ca specific: Find high-res image list items
        if "realtor.ca" in url.lower():
            # In imagelist view, look for property photos in specific containers
            property_imgs = page.eles('.listViewListingImage')
            if not property_imgs:
                property_imgs = page.eles('.gridViewListingImage')
            
            logger.info(f"Realtor specific search found {len(property_imgs)} images with class selectors")
            for img in property_imgs:
                src = img.attr('src') or ''
                if src and src.startswith('http'):
                    if src not in img_urls:
                        img_urls.append(src)

        # Fallback: get all images that look like property photos
        if len(img_urls) < 3:
            for img in all_imgs:
                src = img.attr('src') or ''
                if src.startswith('http') and '.jpg' in src.lower() or '.jpeg' in src.lower() or '.webp' in src.lower():
                    if src not in img_urls:
                        img_urls.append(src)

        page.quit()

        # Deduplicate and ensure high quality
        seen = set()
        unique = []
        for u in img_urls:
            base = u.split('?')[0]
            if base not in seen:
                seen.add(base)
                # Ensure we use high res for Realtor.ca
                if "realtor.ca" in u.lower() and "width=" not in u:
                    if "?" in u: u += "&width=1920"
                    else: u += "?width=1920"
                unique.append(u)

        logger.info(f"Found {len(unique)} unique property photos")
        return unique[:15]

    except Exception as e:
        logger.warning(f"Photo scraping failed: {e}")
        return []

def _scrape_google_images(address: str) -> List[str]:
    """Fallback: search Google Images for the property address to find photos."""
    try:
        from scraper.browser_util import create_browser
        import urllib.parse
        
        query = urllib.parse.quote(f"{address} site:strata.ca OR site:zoocasa.com OR site:condos.ca")
        search_url = f"https://www.google.com/search?tbm=isch&q={query}"
        
        page = create_browser(headless=False)
        page.get(search_url, retry=1, interval=1, timeout=15)
        import time
        time.sleep(4)
        
        img_urls = []
        all_imgs = page.eles('tag:img')
        for img in all_imgs:
            src = img.attr('src') or ''
            # Google often embeds the original high-res URL in the data-src or src if we click it,
            # but for a quick fallback, we grab the largest thumbnails we can find.
            data_src = img.attr('data-src') or ''
            actual_src = data_src if data_src.startswith('http') else src
            
            if actual_src.startswith('http') and ('images?q=tbn:' in actual_src or 'gstatic.com' in actual_src):
                img_urls.append(actual_src)
                
        page.quit()
        
        unique = []
        for u in img_urls:
            if u not in unique:
                unique.append(u)
                
        # Google image thumbnails are often small. Let's try to remove any sizing caps
        final_urls = [u.replace('&s', '') for u in unique[:6]]
        return final_urls
        
    except Exception as e:
        logger.warning(f"Google Image search failed: {e}")
        return []

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 1B: Generate vision-based narration script from actual photos
# ══════════════════════════════════════════════════════════════════════════════

async def generate_vision_narration(
    photos: List[Path],
    listing_data: dict,
    target_duration: float = 30.0,
) -> dict:
    """
    Send every photo to Gemini Vision in a single call and get back a
    cohesive, scene-by-scene voiceover script that accurately describes
    what the viewer sees.  Target word count ≈ target_duration × 2.5
    (≈150 words for 60 s at a relaxed luxury narrator pace).
    """
    try:
        from google import genai
        import PIL.Image, io, json as _json

        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            return None

        client = genai.Client(api_key=api_key)

        address = listing_data.get("address", "this property")
        price = listing_data.get("price", "")
        beds = listing_data.get("bedrooms") or listing_data.get("beds", "")
        baths = listing_data.get("bathrooms") or listing_data.get("baths", "")
        sqft = listing_data.get("area") or listing_data.get("sqft", "")

        n = len(photos)
        secs_per_clip = target_duration / n
        words_per_scene = int(secs_per_clip * 2.5)
        word_target = words_per_scene * n

        contents: list = []

        prompt_text = (
            f"You are a luxury real-estate video narrator. You will see {n} photos "
            f"shown in the EXACT order they appear in the video. Each clip is ~{secs_per_clip:.0f} seconds.\n\n"
            f"Property: {address}\n"
            f"{'Price: ' + str(price) if price else ''}\n"
            f"{'Beds: ' + str(beds) + '  Baths: ' + str(baths) if beds else ''}\n"
            f"{'Area: ' + str(sqft) + ' sqft' if sqft else ''}\n\n"
            f"TASK — write {n} individual narration segments, one per photo.\n\n"
            f"CRITICAL TIMING RULES:\n"
            f"- Each segment MUST be EXACTLY {words_per_scene} words (+-2 words). "
            f"This ensures the voiceover matches what is on screen.\n"
            f"- Segment 1 should open with a hook mentioning the address.\n"
            f"- The last segment should close with a call-to-action.\n"
            f"- Each segment describes ONLY what is visible in THAT photo — "
            f"name the room/space, notable features, materials, lighting.\n"
            f"- Tone: warm, confident, cinematic — premium property film.\n"
            f"- Segments flow naturally as if one continuous narration.\n\n"
            f"Return ONLY valid JSON:\n"
            '{{\n'
            '  "headline": "short catchy tagline (8 words max)",\n'
            f'  "scene_scripts": ["segment 1 ({words_per_scene} words)", '
            f'"segment 2 ({words_per_scene} words)", ...],\n'
            '  "voiceover_script": "all segments joined with a period and space",\n'
            '  "music_mood": "cinematic_luxury | warm_inspiring | modern_elegant | cozy_intimate"\n'
            '}}'
        )

        contents.append(prompt_text)

        for i, photo_path in enumerate(photos):
            try:
                img = PIL.Image.open(io.BytesIO(photo_path.read_bytes()))
                if img.width > 1024:
                    ratio = 1024 / img.width
                    img = img.resize((1024, int(img.height * ratio)))
                contents.append(img)
            except Exception as e:
                logger.warning(f"  Could not load photo {i+1} for vision: {e}")

        if len(contents) < 2:
            return None

        resp = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=contents,
        )
        text = resp.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        data = _json.loads(text)
        if "voiceover_script" in data:
            wc = len(data["voiceover_script"].split())
            logger.info(
                f"✅ Vision narration: {wc} words, headline: {data.get('headline','')}"
            )
            return data

    except Exception as e:
        logger.warning(f"Vision narration generation failed: {e}")

    return None


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 2: Generate voiceover with ElevenLabs
# ══════════════════════════════════════════════════════════════════════════════

VOICE_IDS = {
    "female_luxury": "21m00Tcm4TlvDq8ikWAM",   # Rachel
    "male_luxury":   "29vD33N1CtxCmqQRPOHJ",    # Drew
    "male_deep":     "ErXwobaYiN019PkySvjV",     # Antoni
    "male_cassius":  "ErXwobaYiN019PkySvjV",    # Using Antoni as Cassius alternative for free-tier
}

def _sync_generate_voiceover(text: str, voice_id: str, api_key: str, out_path: Path):
    from elevenlabs.client import ElevenLabs
    from elevenlabs import VoiceSettings

    client = ElevenLabs(api_key=api_key)

    try:
        audio_stream = client.text_to_speech.convert(
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

        with open(out_path, "wb") as f:
            for chunk in audio_stream:
                if isinstance(chunk, bytes):
                    f.write(chunk)
    except Exception as e:
        logger.error(f"❌ ElevenLabs SDK error in _sync_generate_voiceover: {e}")
        raise e

async def generate_voiceover(script_text: str, voice: str, job_dir: Path) -> Optional[Path]:
    """Generate voiceover audio using ElevenLabs API."""
    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    if not api_key or api_key.startswith("your_"):
        logger.warning("ElevenLabs key not set, skipping voiceover")
        return None

    voice_id = VOICE_IDS.get(voice, VOICE_IDS["female_luxury"])
    output_path = job_dir / "voiceover.mp3"

    try:
        await asyncio.to_thread(
            _sync_generate_voiceover,
            script_text,
            voice_id,
            api_key,
            output_path
        )
        logger.info(f"✅ Voiceover generated: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"ElevenLabs voiceover failed (quota or network error): {e}. Falling back to gTTS.")
        try:
            from gtts import gTTS
            tts = gTTS(text=script_text, lang='en', slow=False)
            tts.save(str(output_path))
            logger.info("✅ Fallback voiceover generated with gTTS")
            return output_path
        except Exception as fallback_e:
            logger.error(f"gTTS fallback also failed: {fallback_e}")
            return None


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 3: Generate background music with Suno (via kie.ai)
# ══════════════════════════════════════════════════════════════════════════════

MUSIC_STYLES = {
    "cinematic_luxury": "Cinematic, Piano, Strings, Elegant",
    "warm_inspiring": "Inspirational, Warm Piano, Uplifting",
    "modern_elegant": "Modern Electronic, Minimal, Sophisticated",
    "cozy_intimate": "Acoustic Guitar, Soft, Cozy",
}

async def generate_background_music(script_data: Dict[str, Any], job_dir: Path) -> Optional[Path]:
    """Generate 30-sec background music using Suno API via kie.ai, or use custom file."""
    custom_music = job_dir / "custom_bgmusic.mp3"
    if custom_music.exists():
        logger.info(f"🎵 Using custom uploaded background music: {custom_music}")
        return custom_music
        
    if not SUNO_API_KEY or SUNO_API_KEY.startswith("your_"):
        logger.warning("Suno API key not set, skipping music generation")
        return None

    mood = script_data.get("music_mood", "cinematic_luxury")
    style = MUSIC_STYLES.get(mood, MUSIC_STYLES["cinematic_luxury"])
    output_path = job_dir / "bgmusic.mp3"
    
    # Use the tailored prompt if Gemini generated one, else fallback to generic style
    prompt = script_data.get("music_prompt")
    if not prompt:
        prompt = f"A 30-second {style.lower()} background track for a luxury real estate listing video. No vocals. Soft, elegant, professional."

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            # Start generation
            resp = await client.post(
                "https://api.kie.ai/api/v1/generate",
                headers={
                    "Authorization": f"Bearer {SUNO_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "prompt": prompt,
                    "customMode": True,
                    "instrumental": True,
                    "model": "V4",
                    "style": style,
                    "title": "Real Estate Background",
                    "negativeTags": "Heavy Metal, Loud Drums, Rock, Rap, Vocals, Singing",
                }
            )

            if resp.status_code != 200:
                logger.error(f"Suno API error: {resp.status_code} {resp.text[:200]}")
                return None

            data = resp.json()
            task_id = data.get("data", {}).get("taskId")
            if not task_id:
                logger.error(f"No taskId in Suno response: {data}")
                return None

            logger.info(f"🎵 Suno music generation started: task={task_id}")

            # Poll for completion (max 90 seconds)
            for _ in range(30):
                await asyncio.sleep(3)
                status_resp = await client.get(
                    f"https://api.kie.ai/api/v1/music/{task_id}",
                    headers={"Authorization": f"Bearer {SUNO_API_KEY}"},
                )
                if status_resp.status_code == 200:
                    sdata = status_resp.json()
                    status = sdata.get("data", {}).get("status", "")
                    if status == "SUCCESS":
                        # Get audio URL from the response
                        suno_data = sdata.get("data", {}).get("response", {}).get("sunoData", [])
                        if suno_data:
                            audio_url = suno_data[0].get("audioUrl", "")
                            if audio_url:
                                audio_resp = await client.get(audio_url)
                                if audio_resp.status_code == 200:
                                    output_path.write_bytes(audio_resp.content)
                                    logger.info(f"✅ Background music downloaded: {output_path}")
                                    return output_path
                        break
                    elif status in ("FAILED", "ERROR"):
                        logger.error(f"Suno generation failed: {sdata}")
                        break

            logger.warning("Suno music generation timed out or failed")
            return None

    except Exception as e:
        logger.error(f"Suno music generation error: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 4A: Enhance photos with Flow (Gemini image generation)
# ══════════════════════════════════════════════════════════════════════════════

async def enhance_photo_with_flow(photo_path: Path, scene_desc: str,
                                   job_dir: Path) -> Optional[Path]:
    """
    Enhance a listing photo using Flow (gemini-2.5-flash-image) for
    luxury magazine-quality styling.
    """
    try:
        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            return None

        client = genai.Client(api_key=api_key)

        # Read the original photo
        photo_bytes = photo_path.read_bytes()
        photo_b64 = base64.b64encode(photo_bytes).decode()

        prompt = (
            f"Enhance this real estate photo to luxury magazine quality. "
            f"Scene: {scene_desc}. "
            f"Make it brighter, add warm golden hour lighting, increase contrast, "
            f"make colors rich and inviting. Cinematic real estate photography style."
        )

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[
                    types.Content(parts=[
                        types.Part.from_text(text=prompt),
                        types.Part.from_bytes(data=photo_bytes, mime_type="image/jpeg"),
                    ])
                ],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                )
            )
        except Exception as gemini_err:
            log_activity("ERROR", f"gemini_call failed in enhance_photo_with_flow: {gemini_err}")
            return None

        # Check if we got an image back
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    enhanced_path = job_dir / f"enhanced_{photo_path.name}"
                    enhanced_path.write_bytes(part.inline_data.data)
                    logger.info(f"  ✅ Enhanced photo: {photo_path.name}")
                    return enhanced_path

        logger.warning(f"  Flow enhancement returned no image for {photo_path.name}")
        return None

    except Exception as e:
        logger.warning(f"  Flow enhancement for {photo_path.name} failed: {e}")
        return None


async def generate_cinematic_prompt_for_photo(
    photo_path: Path,
    listing_data: dict,
    scene_index: Optional[int] = None,
    total_scenes: Optional[int] = None,
) -> str:
    """
    Send a listing photo to Gemini Vision and get back a precision
    cinematic camera prompt for Veo 3 — styled like a luxury real
    estate videographer's shot card.
    """
    try:
        from google import genai
        import base64

        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            return VEO_SCENE_PROMPTS[0]

        client = genai.Client(api_key=api_key)
        model_id = "gemini-2.5-flash"

        photo_bytes = photo_path.read_bytes()
        suffix = photo_path.suffix.lower()
        mime_map = {'.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.webp':'image/webp'}
        mime_type = mime_map.get(suffix, 'image/jpeg')

        import PIL.Image
        import io
        img = PIL.Image.open(io.BytesIO(photo_bytes))

        tour_block = ""
        if (
            scene_index is not None
            and total_scenes is not None
            and total_scenes > 0
        ):
            tour_block = (
                f"\nTour context: This photo is frame {scene_index + 1} of {total_scenes} in ONE "
                "continuous luxury listing walk-through (not an isolated clip). The camera movement "
                "you prescribe must feel like the natural next moment after the previous space and "
                "should pull the viewer forward through the home.\n"
            )

        prompt = f"""You are a cinematic prompt engineer for luxury real estate video production.
{tour_block}
Analyze this room photo and write a single precision camera prompt for Veo 3 video generation.

Property: {listing_data.get('address', 'GTA property')}, {listing_data.get('price', '')}

Your prompt must follow this exact structure and style:

1. Camera movement type (e.g. "Extremely slow, measured, stabilized Micro Dolly-In" or "Smooth lateral slider pan" or "Imperceptibly slow Tilt-Down")
2. Direction and focal anchor — what specific object/feature the camera moves toward or tracks
3. Movement distance and easing — e.g. "controlled 6–10 inch forward glide, slow-in and slow-out, no acceleration"
4. Environmental micro-motion — subtle realistic light behavior only (shimmer, reflection, shadow shift)
5. Geometry lock constraints — explicitly state all architectural elements must stay perfectly static, vertical lines locked, no warping, bending, or perspective distortion
6. Quality tags — end with: 4K, HDR, photorealistic, stabilized slider shot, ultra-clean detail, premium real estate presentation

Write ONE dense paragraph. No bullet points. No headers. Be specific to what you actually see in this image — identify the exact focal anchor (island, fireplace, window, staircase etc). Keep it under 120 words."""

        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model_id,
                contents=[prompt, img]
            )
            result = response.text.strip()
            logger.info(f"  🎬 Cinematic prompt generated for {photo_path.name}: {result[:80]}...")
            return result
        except Exception as gemini_err:
            log_activity("ERROR", f"gemini_call failed in generate_cinematic_prompt_for_photo: {gemini_err}")
            return VEO_SCENE_PROMPTS[0]

    except Exception as e:
        logger.warning(f"  Cinematic prompt generation failed for {photo_path.name}: {e}")
        log_activity("ERROR", f"generate_cinematic_prompt_for_photo wrapper failed: {e}")
        return VEO_SCENE_PROMPTS[0]


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 4B: Generate cinematic clips with Veo 3 (image-to-video)
# ══════════════════════════════════════════════════════════════════════════════

# Cinematic camera prompts for each scene
VEO_SCENE_PROMPTS = [
    "Cinematic slow dolly forward through the room, warm golden hour sunlight streaming through windows. Luxury real estate commercial. Photorealistic, 4K.",
    "Smooth cinematic pan from left to right revealing the full space, magazine-quality interior design. Warm ambient lighting. Real estate showcase.",
    "Slow aerial-style reveal pulling back to show the entire space, professional real estate videography. Natural light, elegant atmosphere.",
    "Gentle cinematic track following the room's focal point, luxury property walkthrough. Soft shadows, rich textures. Premium real estate ad.",
    "Slow push-in shot highlighting architectural details, cinematic depth of field. Golden hour warmth. High-end property advertisement.",
    "Smooth orbiting camera revealing the space from a new angle, luxury real estate showcase. Professional lighting, magazine quality.",
]


def _walkthrough_tour_suffix(scene_index: int, total_scenes: int) -> str:
    """Prefix text so Veo treats each clip as part of one continuous listing walk-through."""
    if total_scenes <= 0:
        return ""
    if total_scenes <= 1:
        return (
            "CONTINUOUS TOUR: Single-shot property showcase — one cohesive hero moment, "
            "premium real estate production."
        )
    if scene_index == 0:
        return (
            "CONTINUOUS TOUR — OPENING: Start of a single walk-through visit; establish arrival "
            "and invite the viewer into the home. This shot flows into the following spaces."
        )
    if scene_index == total_scenes - 1:
        return (
            "CONTINUOUS TOUR — CLOSING: Final beat of the same walk-through; resolve the visit "
            "with a memorable last impression."
        )
    return (
        "CONTINUOUS TOUR — MID WALK: Same continuous property visit; motivate forward motion "
        "through the home as if escorting a buyer room-to-room."
    )


def _compose_veo_prompt_with_tour(base_prompt: str, scene_index: int, total_scenes: int) -> str:
    tour = _walkthrough_tour_suffix(scene_index, total_scenes)
    base = (base_prompt or "").strip()
    if not tour:
        return base
    return f"{tour} {base}".strip()


async def generate_veo_clip(
    photo_path: Path,
    scene_prompt: str,
    job_dir: Path,
    clip_index: int,
    duration: int = 6,
) -> Optional[Path]:
    try:
        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            logger.warning("No GEMINI_API_KEY for Veo")
            return None

        client = genai.Client(api_key=api_key)
        clips_dir = job_dir / "veo_clips"
        clips_dir.mkdir(parents=True, exist_ok=True)
        clip_path = clips_dir / f"veo_clip_{clip_index + 1}.mp4"

        photo_bytes = photo_path.read_bytes()
        suffix = photo_path.suffix.lower()
        mime_map = {'.jpg':'image/jpeg','.jpeg':'image/jpeg',
                    '.png':'image/png','.webp':'image/webp'}
        mime_type = mime_map.get(suffix, 'image/jpeg')

        logger.info(f"  🎬 Veo: generating clip {clip_index + 1} ({duration}s)...")
        image = types.Image(image_bytes=photo_bytes, mime_type=mime_type)
        operation = None
        # Only use Veo 2.0 for now as 3.0 preview is restricted/beta
        for model_name in ["veo-2.0-generate-001"]:
            try:
                operation = client.models.generate_videos(
                    model=model_name,
                    prompt=scene_prompt,
                    image=image,
                    config=types.GenerateVideosConfig(
                        aspect_ratio="16:9",
                        number_of_videos=1,
                    ),
                )
                logger.info(f"  ✓ Model accepted: {model_name}")
                break
            except Exception as model_err:
                logger.warning(f"  {model_name} rejected: {model_err}")
                operation = None

        if operation is None:
            logger.warning(f"  No Veo model available for clip {clip_index + 1}")
            return None

        # Poll every 15s, max 10 minutes
        for attempt in range(40):
            if operation.done:
                break
            logger.info(f"    ⏳ Clip {clip_index + 1} polling... {(attempt + 1) * 15}s elapsed")
            await asyncio.sleep(15)
            operation = client.operations.get(operation=operation)

        if not operation.done:
            logger.warning(f"  Veo timed out for clip {clip_index + 1}")
            return None

        if not (operation.response and operation.response.generated_videos):
            logger.warning(f"  Veo returned no generated_videos for clip {clip_index + 1}")
            return None

        video = operation.response.generated_videos[0]

        # Primary: read raw bytes
        try:
            downloaded = client.files.download(file=video.video)
            if hasattr(downloaded, 'read'):
                video_bytes = downloaded.read()
            elif hasattr(downloaded, 'content'):
                video_bytes = downloaded.content
            else:
                video_bytes = bytes(downloaded)
        except Exception:
            video_bytes = b""

        if video_bytes and len(video_bytes) > 1000:
            clip_path.write_bytes(video_bytes)
        else:
            # Fallback: SDK .save()
            try:
                video.video.save(str(clip_path))
            except Exception as save_err:
                logger.warning(f"  .save() also failed: {save_err}")
                return None

        if clip_path.exists() and clip_path.stat().st_size > 1000:
            logger.info(f"  ✅ Veo clip {clip_index + 1} saved: {clip_path.stat().st_size // 1024}KB")
            return clip_path

        logger.warning(f"  Veo clip {clip_index + 1} file is empty after save")
        return None

    except Exception as e:
        logger.warning(f"  Veo clip {clip_index + 1} exception: {e}")
        return None


async def create_veo_clips(
    photos: List[Path],
    scene_prompts: List[str],
    job_dir: Path,
    duration: int = 6,
) -> List[Optional[Path]]:
    """Generate Veo clips for ALL photos — no cap, 20s cooldown between requests."""
    clips = []
    for i, photo in enumerate(photos):
        if i > 0:
            logger.info(f"  ⏳ Cooldown 20s before clip {i + 1}...")
            await asyncio.sleep(20)
        prompt = (
            scene_prompts[i]
            if i < len(scene_prompts) and scene_prompts[i]
            else VEO_SCENE_PROMPTS[i % len(VEO_SCENE_PROMPTS)]
        )
        clip = await generate_veo_clip(photo, prompt, job_dir, i, duration)
        clips.append(clip)
        # Update tracker for any active job using this job_dir
        jid = job_dir.name
        if jid in _active_jobs:
            done = sum(1 for c in clips if c is not None)
            pct = 35 + int(55 * (i + 1) / len(photos))
            _update_job_tracker(jid, clips_done=done, percent=min(pct, 90))
    return clips


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 4C: Ken Burns effect on photos using ffmpeg (FALLBACK)
# ══════════════════════════════════════════════════════════════════════════════

KEN_BURNS_EFFECTS = [
    # Slow zoom in
    "scale=8000:-1,crop=3840:2160:'{iw_half}-1920+n*2':'{ih_half}-1080+n*1',scale=1920:1080",
    # Slow zoom out
    "scale=8000:-1,crop=3840:2160:'{iw_half}-1920-n*2':'{ih_half}-1080-n*1',scale=1920:1080",
    # Pan left to right
    "scale=8000:-1,crop=3840:2160:'n*3':'{ih_half}-1080',scale=1920:1080",
    # Pan right to left
    "scale=8000:-1,crop=3840:2160:'{iw}-3840-n*3':'{ih_half}-1080',scale=1920:1080",
    # Zoom in center
    "scale=8000:-1,crop='3840-n*2':'2160-n*1':'{iw_half}-(3840-n*2)/2':'{ih_half}-(2160-n*1)/2',scale=1920:1080",
    # Pan up
    "scale=8000:-1,crop=3840:2160:'{iw_half}-1920':'n*2',scale=1920:1080",
]

async def create_photo_clips(photos: List[Path], job_dir: Path,
                              duration_per_photo: float = 5.0) -> List[Path]:
    """Apply Ken Burns pan/zoom effects to each photo using ffmpeg."""
    clips_dir = job_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    clips = []

    for i, photo in enumerate(photos):
        if hasattr(photo, "exists") and not photo.exists():
            continue
            
        clip_path = clips_dir / f"clip_{i+1}.mp4"
        effect_idx = i % len(KEN_BURNS_EFFECTS)

        # Simpler, more reliable Ken Burns using zoompan filter
        # zoompan: zoom from 1 to 1.3 over duration, with slight pan
        fps = 30
        total_frames = int(duration_per_photo * fps)

        if effect_idx % 3 == 0:
            zp = (
                f"scale=1920:1080:force_original_aspect_ratio=increase,"
                f"crop=1920:1080,"
                f"zoompan=z='min(zoom+0.0015,1.2)':d={total_frames}"
                f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps={fps}"
            )
        elif effect_idx % 3 == 1:
            zp = (
                f"scale=1920:1080:force_original_aspect_ratio=increase,"
                f"crop=1920:1080,"
                f"zoompan=z='1.15':d={total_frames}"
                f":x='(iw-iw/zoom)*on/{total_frames}':y='ih/2-(ih/zoom/2)':s=1920x1080:fps={fps}"
            )
        else:
            zp = (
                f"scale=1920:1080:force_original_aspect_ratio=increase,"
                f"crop=1920:1080,"
                f"zoompan=z='if(eq(on,1),1.2,max(zoom-0.0015,1))':d={total_frames}"
                f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps={fps}"
            )

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(photo),
            "-vf", zp,
            "-t", str(duration_per_photo),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "ultrafast",
            str(clip_path),
        ]

        try:
            result = await asyncio.to_thread(
                subprocess.run, cmd,
                capture_output=True, text=True, timeout=180
            )
            if result.returncode == 0 and clip_path.exists():
                clips.append(clip_path)
                logger.info(f"  ✅ Clip {i+1}/{len(photos)} created")
            else:
                logger.error(f"  ❌ Clip {i+1} failed: {result.stderr[-200:]}")
        except Exception as e:
            logger.error(f"  ❌ Clip {i+1} error: {e}")

    return clips


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 5: Assemble final video
# ══════════════════════════════════════════════════════════════════════════════

async def assemble_video(
    clips: List[Path],
    voiceover: Optional[Path],
    music: Optional[Path],
    listing_data: Dict[str, Any],
    script_data: Dict[str, Any],
    job_dir: Path,
) -> Optional[Path]:
    """
    Assemble final video: concatenate clips, overlay voiceover + music,
    add text captions.
    """
    output_path = OUTPUT_DIR / f"416homes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    ensure_dirs()

    if not clips:
        logger.error("No clips to assemble")
        return None

    try:
        # Step A: Concatenate all clips into one video
        concat_file = job_dir / "concat.txt"
        with open(concat_file, "w") as f:
            for clip in clips:
                # Use as_posix() to ensure forward slashes, which ffmpeg concat requires
                f.write(f"file '{clip.resolve().as_posix()}'\n")

        concat_video = job_dir / "concat.mp4"
        cmd_concat = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_file),
            "-c:v", "libx264", "-preset", "fast",
            "-pix_fmt", "yuv420p",
            str(concat_video),
        ]

        result = await asyncio.to_thread(
            subprocess.run, cmd_concat, capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            logger.error(f"Concat failed: {result.stderr[-300:]}")
            return None

        # Step B: Add text overlay (headline + address + price)
        headline = (script_data or {}).get("headline", "")
        address = listing_data.get("address", "")
        price = listing_data.get("price", "")

        # Build drawtext filter for captions
        # Headline in first 3 seconds, address+price in last 3 seconds
        drawtext_parts = []
        if headline:
            drawtext_parts.append(
                f"drawtext=text='{_escape_ffmpeg(headline)}'"
                f":fontsize=48:fontcolor=white:borderw=2:bordercolor=black"
                f":x=(w-text_w)/2:y=h-120"
                f":enable='between(t,0.5,4)'"
                f":fontfile='C\\:/Windows/Fonts/arial.ttf'"
            )
        if address:
            drawtext_parts.append(
                f"drawtext=text='{_escape_ffmpeg(address)}'"
                f":fontsize=36:fontcolor=white:borderw=2:bordercolor=black"
                f":x=(w-text_w)/2:y=h-100"
                f":enable='gt(t,4)'"
                f":fontfile='C\\:/Windows/Fonts/arial.ttf'"
            )
        if price:
            drawtext_parts.append(
                f"drawtext=text='{_escape_ffmpeg(str(price))}'"
                f":fontsize=56:fontcolor=#c8a96e:borderw=2:bordercolor=black"
                f":x=(w-text_w)/2:y=h-160"
                f":enable='gt(t,4)'"
                f":fontfile='C\\:/Windows/Fonts/arial.ttf'"
            )

        # Step C: Mix audio tracks
        # Get concat video duration so we never truncate it
        probe = await asyncio.to_thread(
            subprocess.run,
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(concat_video)],
            capture_output=True, text=True, timeout=10,
        )
        video_dur = float(probe.stdout.strip() or "0")

        if voiceover and voiceover.exists():
            if music and music.exists():
                # Mix voiceover + music, pad audio to video length
                cmd_final = [
                    "ffmpeg", "-y",
                    "-i", str(concat_video),
                    "-i", str(voiceover),
                    "-i", str(music),
                    "-filter_complex",
                    f"[1:a]volume=1.0,apad=whole_dur={video_dur}[vo];"
                    f"[2:a]volume=0.15,apad=whole_dur={video_dur}[bg];"
                    f"[vo][bg]amix=inputs=2:duration=first[amixed]"
                    + (f";[0:v]{','.join(drawtext_parts)}[vout]" if drawtext_parts else ""),
                    "-map", "[vout]" if drawtext_parts else "0:v",
                    "-map", "[amixed]",
                    "-c:v", "libx264", "-preset", "fast",
                    "-c:a", "aac", "-b:a", "192k",
                    "-t", str(video_dur),
                    str(output_path),
                ]
            else:
                # Voiceover only — pad audio to match video length
                vf = ",".join(drawtext_parts) if drawtext_parts else None
                cmd_final = [
                    "ffmpeg", "-y",
                    "-i", str(concat_video),
                    "-i", str(voiceover),
                    "-filter_complex",
                    f"[1:a]apad=whole_dur={video_dur}[aout]"
                    + (f";[0:v]{','.join(drawtext_parts)}[vout]" if drawtext_parts else ""),
                ]
                if drawtext_parts:
                    cmd_final += ["-map", "[vout]"]
                else:
                    cmd_final += ["-map", "0:v"]
                cmd_final += [
                    "-map", "[aout]",
                    "-c:v", "libx264", "-preset", "fast",
                    "-c:a", "aac", "-b:a", "192k",
                    "-t", str(video_dur),
                    str(output_path),
                ]
        else:
            # No audio at all — just video with captions
            vf = ",".join(drawtext_parts) if drawtext_parts else None
            cmd_final = [
                "ffmpeg", "-y",
                "-i", str(concat_video),
            ]
            if vf:
                cmd_final += ["-vf", vf]
            cmd_final += [
                "-c:v", "libx264", "-preset", "fast",
                "-an",
                str(output_path),
            ]

        result = await asyncio.to_thread(
            subprocess.run, cmd_final, capture_output=True, text=True, timeout=120
        )

        if result.returncode == 0 and output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            logger.info(f"✅ Final video: {output_path} ({size_mb:.1f} MB)")
            return output_path
        else:
            logger.error(f"Final assembly failed: {result.stderr[-300:]}")
            return None

    except Exception as e:
        logger.error(f"Video assembly error: {e}")
        return None


def _escape_ffmpeg(text: str) -> str:
    """Escape special characters for ffmpeg drawtext."""
    return (text
            .replace("\\", "\\\\")
            .replace("'", "\\'")
            .replace(":", "\\:")
            .replace("%", "%%")
            .replace("\n", " "))


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN PIPELINE ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════

async def produce_video(
    listing_url: str,
    listing_data: dict,
    job_dir: Path,
    script_data: dict = None,
    progress_callback=None,
    force_veo: bool = False,
) -> Optional[Path]:
    """
    Full video production pipeline.

    Args:
        listing_url: URL to scrape photos from
        listing_data: Dict with address, price, beds, baths, etc.
        job_dir: Path to the directory for this job
        script_data: Optional dict with headline, voiceover_script, etc.
        progress_callback: async callback(step, message) for progress reporting

    Returns:
        Path to final MP4, or None on failure
    """
    url = listing_url  # normalize parameter name
    job_id = job_dir.name
    job_dir.mkdir(parents=True, exist_ok=True)
    ensure_dirs()
    logger.info(
        "video_pipeline_entry=produce_video job_id=%s url=%s",
        job_id,
        (listing_url or url or "")[:120],
    )
    log_activity("VIDEO", f"Job started: {job_id} for {listing_url}")
    _update_job_tracker(job_id, address=listing_data.get("address", url), status="running")

    async def progress(step, msg):
        if progress_callback:
            await progress_callback(step, msg)
        logger.info(f"[{step}] {msg}")
        _update_job_tracker(job_id, step=step, detail=msg)

    try:
        # 1. Download or use custom photos
        photos_dir = job_dir / "photos"
        photos = []
        if photos_dir.exists() and any(photos_dir.iterdir()):
            await progress("scrape", "Using custom uploaded photos...")
            # Grab all jpg/png files
            photos = sorted(list(photos_dir.glob("*.jpg")) + list(photos_dir.glob("*.png")))
            
        if not photos and listing_url and listing_url != "custom_upload":
            await progress("scrape", "Downloading listing photos...")
            photos = await download_listing_photos(
                listing_url, 
                job_dir, 
                address=listing_data.get("address"),
                provided_urls=listing_data.get("photos")
            )

        if not photos:
            await progress("scrape", "No photos found — creating placeholder clips")
            # Create a simple dark placeholder image
            placeholder = photos_dir / "placeholder.jpg"
            placeholder.parent.mkdir(parents=True, exist_ok=True)
            _create_placeholder_image(placeholder, listing_data)
            photos = [placeholder]

        # Smart ordering: classify rooms + arrange in walkthrough sequence
        await progress("scrape", f"Classifying {len(photos)} photos for optimal walkthrough order...")
        photos = await smart_order_photos(photos, listing_data)

        MAX_PHOTOS = int(os.getenv("MAX_VIDEO_PHOTOS", "5"))
        if len(photos) > MAX_PHOTOS:
            photos = photos[:MAX_PHOTOS]

        await progress("scrape", f"{len(photos)} photos ready (smart-ordered)")
        _update_job_tracker(job_id, photos_total=len(photos), photos_downloaded=len(photos), percent=10)

        if progress_callback:
            await progress_callback(1, "Photos classified and ordered")

        # 1B. Generate vision-based narration from actual photos if no script provided
        if not script_data or not script_data.get("voiceover_script", "").strip():
            clip_duration = 30.0
            total_video_secs = clip_duration  # rough target
            await progress("script", f"Analyzing {len(photos)} photos with AI vision to write narration...")
            vision_script = await generate_vision_narration(photos, listing_data, total_video_secs)
            if vision_script:
                script_data = vision_script
                await progress("script", f"Narration ready: \"{vision_script.get('headline', '')}\" ({len(vision_script.get('voiceover_script','').split())} words)")
            else:
                await progress("script", "Vision narration failed — video will have no voiceover")

        # 2. Generate voiceover (skip if no script text)
        vo_text = (script_data.get("voiceover_script", "") if script_data else "").strip()
        voiceover = None
        if vo_text:
            await progress("audio", "Recording AI voiceover with ElevenLabs...")
            voiceover = await generate_voiceover(
                vo_text, listing_data.get("voice", "female_luxury"), job_dir
            )
        else:
            await progress("audio", "No voiceover script — skipping")
        if voiceover:
            await progress("audio", "Voiceover recorded successfully")
            _update_job_tracker(job_id, voiceover=True, percent=20)
            if progress_callback:
                await progress_callback(2, "Voiceover recorded")
        else:
            await progress("audio", "Voiceover skipped (no API key or error)")
            _update_job_tracker(job_id, percent=20)

        # 3. Generate background music
        await progress("audio", "Generating background music...")
        music = await generate_background_music(
            script_data, job_dir
        )
        if music:
            await progress("audio", "Background music ready")
            _update_job_tracker(job_id, music=True, percent=25)
        else:
            await progress("audio", "Music skipped (Suno key not set)")
            _update_job_tracker(job_id, percent=25)

        # 4. Generate cinematic clips — try Veo 3 first (subject to budget), fallback to ffmpeg
        scene_prompts = script_data.get("scene_prompts", []) if script_data else []
        clips: List[Path] = []

        # Determine whether to use Veo based on budget and order type.
        paid_order = bool(listing_data.get("paid_order", False))
        env_use_veo = os.getenv("USE_VEO3", "true").lower() == "true"
        budget_ok = check_veo_budget_available() if paid_order or force_veo else False
        use_veo = env_use_veo and (force_veo or (paid_order and budget_ok))
        enhance_photos_flag = bool(listing_data.get("enhance_photos", False))

        n_photos = len(photos)
        await progress("animate", f"Analyzing {n_photos} photos for cinematic shots...")
        vision_prompts: List[str] = []
        for i, photo in enumerate(photos):
            prompt = await generate_cinematic_prompt_for_photo(
                photo, listing_data, scene_index=i, total_scenes=n_photos
            )
            vision_prompts.append(prompt)
            await progress("animate", f"Shot {i+1}/{n_photos}: {prompt[:60]}...")

        # 4A. Optional Flow enhancement (premium tier) — always followed by same Veo + gap-fill path
        enhanced_photos: List[Path]
        if use_veo and enhance_photos_flag:
            logger.info("Using Flow enhancement before Veo (premium tier).")
            await progress("enhance", f"Enhancing {n_photos} photos with Flow AI...")
            enhanced_photos = []
            for i, photo in enumerate(photos):
                desc = (
                    scene_prompts[i]
                    if script_data and i < len(scene_prompts)
                    else "luxury living space"
                )
                enhanced = await enhance_photo_with_flow(photo, desc, job_dir)
                enhanced_photos.append(enhanced or photo)

            enhanced_count = sum(1 for p in enhanced_photos if p.parent.name != "photos")
            _update_job_tracker(job_id, enhanced=enhanced_count, percent=30)
            if enhanced_count:
                await progress("enhance", f"Enhanced {enhanced_count}/{n_photos} photos")
            else:
                await progress("enhance", "Flow enhancement skipped, using originals")
                enhanced_photos = list(photos)
        else:
            enhanced_photos = list(photos)

        if use_veo:
            final_prompts = [
                _compose_veo_prompt_with_tour(
                    vp
                    if vp
                    else (
                        scene_prompts[i]
                        if i < len(scene_prompts)
                        else VEO_SCENE_PROMPTS[i % len(VEO_SCENE_PROMPTS)]
                    ),
                    i,
                    len(enhanced_photos),
                )
                for i, vp in enumerate(vision_prompts)
            ]

            target_duration = 30.0
            duration_per = (
                target_duration / len(enhanced_photos) if enhanced_photos else 2.0
            )
            await progress(
                "animate",
                f"🎬 Generating {len(enhanced_photos)} Veo 3 cinematic clips ({duration_per:.1f}s each)...",
            )
            _update_job_tracker(job_id, clips_total=len(enhanced_photos), percent=35)
            veo_results: List[Optional[Path]] = []
            try:
                veo_results = await create_veo_clips(
                    enhanced_photos,
                    final_prompts,
                    job_dir,
                    duration=int(duration_per),
                )
                if any(c is not None for c in veo_results):
                    record_veo_usage()
            except Exception as e:
                logger.error("Veo generation failed: %s, falling back to Ken Burns", e)
                veo_results = [None] * len(enhanced_photos)

            fallback_mode = (os.getenv("VEO_FALLBACK_MODE") or "per_shot").strip().lower()
            extra_retries = max(0, int(os.getenv("VEO_CLIP_RETRIES", "1") or "0"))
            source_photos = enhanced_photos if enhanced_photos else photos

            if fallback_mode == "uniform_kb" and any(r is None for r in veo_results):
                await progress(
                    "animate",
                    "VEO_FALLBACK_MODE=uniform_kb — regenerating all shots with Ken Burns for a consistent look.",
                )
                clips = await create_photo_clips(
                    source_photos,
                    job_dir,
                    duration_per_photo=duration_per,
                )
            else:
                clips = []
                for i, clip in enumerate(veo_results):
                    if clip:
                        clips.append(clip)
                        continue
                    retried: Optional[Path] = None
                    for attempt in range(extra_retries):
                        await progress(
                            "animate",
                            f"Veo extra attempt {attempt + 1}/{extra_retries} for shot {i + 1}...",
                        )
                        if attempt > 0:
                            await asyncio.sleep(15)
                        retried = await generate_veo_clip(
                            source_photos[i],
                            final_prompts[i],
                            job_dir,
                            i,
                            duration=int(duration_per),
                        )
                        if retried:
                            break
                    if retried:
                        clips.append(retried)
                        continue
                    await progress(
                        "animate",
                        f"Veo failed for shot {i + 1}, using ffmpeg fallback...",
                    )
                    kb_clips = await create_photo_clips(
                        [source_photos[i]],
                        job_dir,
                        duration_per_photo=duration_per,
                    )
                    if kb_clips:
                        clips.append(kb_clips[0])

            if clips:
                await progress("animate", f"✅ {len(clips)} total cinematic clips ready")
                if progress_callback:
                    await progress_callback(3, "Clips assembled")

        # 4C. Full fallback to ffmpeg Ken Burns if NO clips exist yet
        if not clips:
            if use_veo:
                await progress("animate", "Veo unavailable or budget limit hit — falling back to Ken Burns effects...")

            source_photos = enhanced_photos if enhanced_photos else photos
            target_duration = 30.0
            duration_per = target_duration / len(source_photos) if source_photos else 5.0
            await progress("animate", f"Animating {len(source_photos)} photos with Ken Burns effects...")
            clips = await create_photo_clips(source_photos, job_dir,
                                              duration_per_photo=duration_per)

        if not clips:
            await progress("animate", "Failed to create any clips")
            return None

        await progress("animate", f"All {len(clips)} clips ready")

        # 5. Assemble final video
        await progress("assemble", "Assembling final video with captions and audio...")
        if progress_callback:
            await progress_callback(4, "Rendering final video")
        final = await assemble_video(clips, voiceover, music, listing_data, script_data, job_dir)

        if final:
            await progress("assemble", f"Final video: {final.name} ({final.stat().st_size // 1024}KB)")
            log_activity("VIDEO", f"Job completed: {job_id} — file size {final.stat().st_size // 1024}KB")
            _update_job_tracker(job_id, status="done", percent=100,
                                detail=f"Final: {final.name} ({final.stat().st_size // 1024}KB)")
        else:
            await progress("assemble", "Assembly failed")
            log_activity("ERROR", f"Job failed: {job_id} (Assembly failed)")
            _update_job_tracker(job_id, status="failed", detail="Assembly failed")

        return final

    except Exception as e:
        import traceback
        logger.error(f"Pipeline error: {e}")
        log_activity("ERROR", f"produce_video failed for {url}: {e}")
        log_activity("ERROR", traceback.format_exc())
        _update_job_tracker(job_id, status="failed", detail=str(e)[:200])
        return None
    finally:
        # Keep temp files — Veo clips cost credits to regenerate
        logger.info(f"Job {job_id} temp files preserved at: {job_dir}")
        # Keep finished jobs in tracker for 10 min so users can check status
        asyncio.get_event_loop().call_later(600, _remove_job_tracker, job_id)


def _create_placeholder_image(path: Path, listing_data: Dict):
    """Create a simple dark gradient image as placeholder."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGB', (1920, 1080), color=(10, 10, 8))
        draw = ImageDraw.Draw(img)
        # Simple centered text
        addr = listing_data.get("address", "Property Listing")
        price = listing_data.get("price", "")
        draw.text((960, 480), addr, fill=(200, 169, 110), anchor="mm")
        draw.text((960, 560), str(price), fill=(245, 244, 239), anchor="mm")
        img.save(path, "JPEG", quality=95)
    except ImportError:
        # No Pillow — create a tiny JPEG manually not possible, use ffmpeg
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "color=c=0x0a0a08:s=1920x1080:d=1",
            "-frames:v", "1",
            str(path),
        ], capture_output=True, timeout=10)
