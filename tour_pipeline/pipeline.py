"""
Tour pipeline — fetches listing photos, classifies by room via Gemini Vision,
builds a photo manifest, and delivers a hosted virtual tour link.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
APP_URL = os.getenv("APP_URL", "https://416-homes.vercel.app").split(",")[0].strip().rstrip("/")

STOCK_PHOTOS: list[str] = [
    "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=900&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=900&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1484154218962-a197022b5858?w=900&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1505691938895-1758d7feb511?w=900&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1552321554-5fefe8c9ef14?w=900&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1507089947368-19c1da9775ae?w=900&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=900&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?w=900&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1588854337221-4cf9fa96059c?w=900&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1560448204-603b3fc33ddc?w=900&auto=format&fit=crop",
]

ROOM_LABELS: dict[str, str] = {
    "exterior": "Exterior",
    "living_room": "Living Room",
    "kitchen": "Kitchen",
    "bedroom": "Bedroom",
    "bathroom": "Bathroom",
    "dining_room": "Dining Room",
    "basement": "Basement",
    "garage": "Garage",
    "backyard": "Backyard",
    "other": "Other",
}


def _supabase_client():
    try:
        from supabase import create_client
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logger.error("Supabase init failed: %s", e)
        return None


async def _fetch_realtor_ca_photos(listing_url: str) -> list[str]:
    """Extract photos from realtor.ca using curl_cffi (Chrome impersonation)."""
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
    try:
        from curl_cffi import requests as cffi_requests
        def _do():
            r = cffi_requests.post(
                "https://api2.realtor.ca/Listing.svc/PropertyDetails_Get",
                headers=headers,
                data={"ApplicationId": "1", "CultureId": "1", "PropertyId": mls, "ReferenceNumber": "0"},
                impersonate="chrome120", timeout=15,
            )
            return r.status_code, r.json() if r.status_code == 200 else {}
        status, body = await asyncio.to_thread(_do)
        if status == 200:
            media = body.get("Media") or body.get("Property", {}).get("Photo") or []
            urls = [(p.get("HighResPath") or p.get("MedResPath") or p.get("LargePhotoUrl") or "") for p in media]
            urls = [u for u in urls if u.startswith("http")]
            if urls:
                return urls[:15]
    except Exception as e:
        logger.warning("realtor.ca curl_cffi failed for MLS %s: %s", mls, e)

    # Fallback: scrape HTML
    try:
        from curl_cffi import requests as cffi_requests
        def _get_html():
            r = cffi_requests.get(listing_url, impersonate="chrome120", timeout=20)
            return r.text
        html = await asyncio.to_thread(_get_html)
        import re as _re2
        found = _re2.findall(r"https://cdn\.realtor\.ca/[^\s\"'<>)]+\.(?:jpg|jpeg|webp|png)", html, _re2.IGNORECASE)
        seen, urls = set(), []
        for u in found:
            if u not in seen and "lowres" not in u.lower():
                seen.add(u); urls.append(u)
        if urls:
            return urls[:15]
    except Exception as e:
        logger.warning("realtor.ca HTML scrape failed: %s", e)
    return []


async def _fetch_listing_photos(listing_url: str) -> list[str]:
    if not listing_url:
        return []
    if "realtor.ca" in listing_url:
        return await _fetch_realtor_ca_photos(listing_url)
    # Generic: look for expcloud image URLs
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            resp = await client.get(listing_url)
            resp.raise_for_status()
            html = resp.text
        import re as _re
        found = _re.findall(r"https://images\.expcloud\.com/[^\s\"'<>)]+\.(?:jpg|jpeg|webp|png)", html, _re.IGNORECASE)
        found += _re.findall(r"https://cdn\.zoocasa\.com/[^\s\"'<>)]+\.(?:jpg|jpeg|webp|png)", html, _re.IGNORECASE)
        seen, urls = set(), []
        for u in found:
            if u not in seen:
                seen.add(u); urls.append(u)
        return urls[:15]
    except Exception as e:
        logger.error("Generic photo fetch failed for %s: %s", listing_url, e)
        return []


async def _fetch_photos_from_db(listing_url: str) -> list[str]:
    """Look up already-scraped photos from the Supabase listings table."""
    if not listing_url:
        return []
    try:
        db = _supabase_client()
        if not db:
            return []
        # Try exact URL match first, then partial match on the core path
        rows = db.table("listings").select("raw_data, url").eq("url", listing_url).limit(1).execute()
        if not rows.data:
            # Try ILIKE partial match
            import re as _re
            slug = _re.sub(r"https?://[^/]+", "", listing_url).strip("/")[:80]
            rows = db.table("listings").select("raw_data, url").ilike("url", f"%{slug}%").limit(1).execute()
        if not rows.data:
            return []
        raw = rows.data[0].get("raw_data") or {}
        # Try common photo fields stored by our scrapers
        for key in ("photos", "photo_urls", "images", "media", "Photo"):
            val = raw.get(key)
            if isinstance(val, list):
                urls = []
                for item in val:
                    if isinstance(item, str) and item.startswith("http"):
                        urls.append(item)
                    elif isinstance(item, dict):
                        for fk in ("url", "HighResPath", "MedResPath", "LargePhotoUrl", "src"):
                            if isinstance(item.get(fk), str) and item[fk].startswith("http"):
                                urls.append(item[fk])
                                break
                if urls:
                    logger.info("Found %d photos from listings DB for %s", len(urls), listing_url)
                    return urls[:15]
        return []
    except Exception as e:
        logger.warning("DB photo lookup failed for %s: %s", listing_url, e)
        return []


async def _classify_photos_gemini(photo_urls: list[str]) -> list[dict[str, Any]]:
    """Ask Gemini to classify each photo into a room type. Returns list of {url, room_type}."""
    if not GEMINI_API_KEY or not photo_urls:
        # Fallback: assign generic labels
        labels = ["exterior", "living_room", "kitchen", "bedroom", "bathroom", "dining_room", "other"]
        return [{"url": u, "room_type": labels[i % len(labels)]} for i, u in enumerate(photo_urls)]

    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash")

        results = []
        for url in photo_urls:
            try:
                prompt = (
                    "Look at this real estate photo and classify it into exactly one of these room types: "
                    "exterior, living_room, kitchen, bedroom, bathroom, dining_room, basement, garage, backyard, other. "
                    "Reply with ONLY the room type slug, nothing else."
                )
                # Download image bytes
                async with httpx.AsyncClient(timeout=10) as client:
                    img_resp = await client.get(url)
                    img_bytes = img_resp.content
                    content_type = img_resp.headers.get("content-type", "image/jpeg")

                import google.generativeai.types as gtypes
                image_part = {"mime_type": content_type, "data": img_bytes}
                response = await asyncio.to_thread(model.generate_content, [prompt, image_part])
                room_type = response.text.strip().lower().replace(" ", "_")
                if room_type not in ROOM_LABELS:
                    room_type = "other"
                results.append({"url": url, "room_type": room_type})
            except Exception as e:
                logger.warning("Gemini classification failed for %s: %s", url, e)
                results.append({"url": url, "room_type": "other"})
        return results
    except Exception as e:
        logger.error("Gemini classify batch failed: %s", e)
        labels = ["exterior", "living_room", "kitchen", "bedroom", "bathroom", "dining_room", "other"]
        return [{"url": u, "room_type": labels[i % len(labels)]} for i, u in enumerate(photo_urls)]


def _build_manifest(classified: list[dict]) -> dict:
    """Group classified photos into rooms, sorted by display priority."""
    PRIORITY = ["exterior", "living_room", "kitchen", "dining_room", "bedroom", "bathroom", "backyard", "basement", "garage", "other"]
    groups: dict[str, list[str]] = {}
    for item in classified:
        rt = item["room_type"]
        groups.setdefault(rt, []).append(item["url"])

    rooms = []
    for slug in PRIORITY:
        if slug in groups:
            rooms.append({"slug": slug, "name": ROOM_LABELS[slug], "photos": groups[slug]})
    # Add any unexpected slugs at the end
    for slug, photos in groups.items():
        if slug not in PRIORITY:
            rooms.append({"slug": slug, "name": slug.replace("_", " ").title(), "photos": photos})
    return {"rooms": rooms}


async def _send_tour_email(customer_email: str, customer_name: str, tour_url: str) -> None:
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping tour delivery email")
        return
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            payload = {
                "from": "416Homes <tours@416homes.ca>",
                "to": [customer_email],
                "subject": "Your virtual tour is ready — 416Homes",
                "html": f"""
<div style="font-family:sans-serif;max-width:600px;margin:0 auto;background:#0a0a08;color:#f5f4ef;padding:32px;">
  <h1 style="color:#c8a96e;font-size:1.4rem;margin-bottom:8px;">Your virtual tour is ready</h1>
  <p style="color:#9a9a8a;margin-bottom:24px;">Hi {customer_name or 'there'},</p>
  <p style="margin-bottom:24px;">Your interactive virtual tour has been generated and is ready to share with buyers.</p>
  <a href="{tour_url}" style="display:inline-block;background:#c8a96e;color:#0a0a08;padding:12px 24px;text-decoration:none;font-weight:700;margin-bottom:24px;">View Your Tour →</a>
  <p style="color:#6b6b60;font-size:0.85rem;margin-bottom:8px;">Embed on your website:</p>
  <code style="display:block;background:#1a1a14;padding:12px;font-size:0.75rem;color:#c8a96e;word-break:break-all;">&lt;iframe src="{tour_url}" width="100%" height="600" frameborder="0" allowfullscreen&gt;&lt;/iframe&gt;</code>
  <p style="color:#6b6b60;font-size:0.8rem;margin-top:24px;">— 416Homes</p>
</div>""",
            }
            resp = await client.post(
                "https://api.resend.com/emails",
                json=payload,
                headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            )
            if resp.status_code >= 400:
                logger.error("Resend email failed (%d): %s", resp.status_code, resp.text)
            else:
                logger.info("Tour delivery email sent to %s", customer_email)
    except Exception as e:
        logger.error("Failed to send tour delivery email: %s", e)


async def process_tour_job(job_id: str) -> None:
    """Main entry point — called by the background worker loop."""
    db = _supabase_client()
    if not db:
        logger.error("Cannot process tour job %s — Supabase unavailable", job_id)
        return

    def _update(**fields):
        try:
            db.table("tour_jobs").update({**fields, "updated_at": datetime.now(timezone.utc).isoformat()}).eq("id", job_id).execute()
        except Exception as e:
            logger.error("Failed to update tour job %s: %s", job_id, e)

    try:
        row = db.table("tour_jobs").select("*").eq("id", job_id).single().execute()
        job = row.data
        listing_url = job.get("listing_url", "")
        customer_email = job.get("customer_email", "")
        customer_name = job.get("customer_name", "") or customer_email.split("@")[0]

        _update(status="processing")

        # Step 1: Fetch photos (3-tier fallback: scrape → DB lookup → stock)
        logger.info("Tour job %s: fetching photos from %s", job_id, listing_url)
        photo_urls = await _fetch_listing_photos(listing_url)
        used_stock = False
        if not photo_urls:
            logger.info("Tour job %s: direct scrape empty, trying DB lookup", job_id)
            photo_urls = await _fetch_photos_from_db(listing_url)
        if not photo_urls:
            logger.warning("Tour job %s: no photos found anywhere — using stock photos", job_id)
            photo_urls = STOCK_PHOTOS
            used_stock = True
        _update(status="classifying", progress=30)

        # Step 2: Classify with Gemini
        logger.info("Tour job %s: classifying %d photos", job_id, len(photo_urls))
        classified = await _classify_photos_gemini(photo_urls)
        _update(status="building", progress=70)

        # Step 3: Build manifest
        manifest = _build_manifest(classified)
        manifest["listing_url"] = listing_url
        if used_stock:
            manifest["stock_photos"] = True  # viewer can show a "sample photos" notice
        tour_url = f"{APP_URL}/tours/{job_id}"

        _update(
            status="completed",
            progress=100,
            photo_manifest=manifest,
            tour_url=tour_url,
        )
        logger.info("Tour job %s completed: %s", job_id, tour_url)

        # Step 4: Email delivery
        await _send_tour_email(customer_email, customer_name, tour_url)

    except Exception as e:
        logger.error("Tour job %s failed: %s", job_id, e)
        _update(status="failed", error_message=str(e))
