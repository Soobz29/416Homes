"""
416Homes Demo API — Serves real scraped data AND video pipeline to the dashboard.

Usage:
    1. python demo_api.py
    2. Open http://localhost:3000/dashboard.html   (listings)
    3. Open http://localhost:3000/416homes-video.html (video orders)

Endpoints:
    GET  /listings           → cached scraped listings
    POST /valuate            → fallback valuation formula
    POST /video/create-checkout → create video job, start real Gemini script gen
    GET  /video/status/{id}  → poll job progress
    GET  /video/download/{id}→ download final video (placeholder)
    GET  /report             → branded client report (HTML)
    GET  /health             → health check
"""

from fastapi import FastAPI, Query, File, Form, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import asyncio
import logging
import os
import json
import uuid
import re
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# Autonomous Agent Components
from listing_agent import agent as listing_agent
from telegram_bot import bot as telegram_bot, send_notification
from listing_agent.scheduler import agent_scheduler
from listing_agent.memory import agent_memory

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# White-label Configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "agent_config.json")
def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

AGENT_CONFIG = load_config()
AGENT_NAME = AGENT_CONFIG.get("agent_name", "AI Agent")
BROKERAGE_NAME = AGENT_CONFIG.get("brokerage_name", "416Homes")
PRIMARY_COLOUR = AGENT_CONFIG.get("primary_colour", "#C9A84C")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start Agent Components
    logger.info(f"🚀 Starting {AGENT_NAME} components...")
    
    # 1. Start Listing Agent Scan Loop
    listing_agent.start()
    logger.info("✅ Listing agent scan loop started")
    
    # 2. Start Telegram Bot
    try:
        await telegram_bot.start()
        logger.info("✅ Telegram bot polling started")
    except Exception as e:
        logger.error(f"❌ Telegram bot failed to start: {e}")
        from listing_agent.activity_log import log_activity
        log_activity("ERROR", f"Telegram bot failed to start: {e}")
    
    # 3. Start APScheduler
    try:
        await agent_scheduler.start()
        logger.info("✅ APScheduler heartbeat scheduled")
    except Exception as e:
        logger.error(f"❌ APScheduler failed to start: {e}")
        from listing_agent.activity_log import log_activity
        log_activity("ERROR", f"APScheduler failed to start: {e}")
    
    yield
    
    # Shutdown: Stop Agent Components
    logger.info("🛑 Stopping 416 Agent components...")
    listing_agent.stop()
    await telegram_bot.stop()
    await agent_scheduler.stop()

app = FastAPI(title=f"{AGENT_NAME} Demo API", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory caches ────────────────────────────────────────────────────────
LISTINGS_CACHE: list = []
SCRAPE_STATUS = {"running": False, "done": False, "count": 0}
VIDEO_JOBS: Dict[str, Dict[str, Any]] = {}

# ── Report Endpoint ─────────────────────────────────────────────────────────

@app.get("/report", response_class=HTMLResponse)
async def get_client_report():
    try:
        # Force reload memory to get latest metrics
        agent_memory._load()
        metrics = agent_memory.get_metrics()
        
        def safe_int(val, default=0):
            try:
                if isinstance(val, str):
                    val = val.replace("$", "").replace(",", "").strip()
                return int(val)
            except:
                return default

        def format_currency(val):
            return f"${safe_int(val):,}"

        # Load Buyer Profiles
        profiles_path = os.path.join("listing_agent", "buyer_profiles.json")
        buyers = []
        if os.path.exists(profiles_path):
            try:
                with open(profiles_path, "r", encoding="utf-8") as f:
                    buyers = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load buyers: {e}")
                
        events = agent_memory.data.get("event_log", [])
        recent_alerts = [e for e in events if e.get('type') == 'alert_fired'][-15:]
        
        # Pre-process buyers and alerts for template
        buyer_rows = ""
        for b in buyers:
            budget = f"{format_currency(b.get('min'))} - {format_currency(b.get('max'))}"
            buyer_rows += f"<tr><td>{b.get('name')}</td><td>{budget}</td><td>{b.get('beds')}+</td><td>{b.get('neighbourhood')}</td><td><span class='badge badge-high'>ACTIVE</span></td></tr>"

        alert_rows = ""
        for e in reversed(recent_alerts):
            data = e.get('data', {})
            price = safe_int(data.get('price', 0))
            badge_class = "badge-urgent" if price > 1000000 else "badge-high"
            badge_text = "URGENT" if price > 1000000 else "HIGH MATCH"
            dt_str = "Unknown"
            if e.get('timestamp'):
                try:
                    dt_str = datetime.fromisoformat(e['timestamp']).strftime('%b %d • %H:%M')
                except: pass
                
            alert_rows += f"""
                <tr>
                    <td>{data.get('address', 'Private Address')}</td>
                    <td>{format_currency(price)}</td>
                    <td>{dt_str}</td>
                    <td><span class='badge {badge_class}'>{badge_text}</span></td>
                </tr>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{AGENT_NAME} - Performance Report</title>
            <style>
                body {{ font-family: 'Inter', -apple-system, sans-serif; background-color: #f4f7f6; color: #2d3436; margin: 0; padding: 40px; }}
                .container {{ max-width: 1000px; margin: auto; background: white; padding: 50px; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }}
                header {{ border-bottom: 2px solid {PRIMARY_COLOUR}; padding-bottom: 30px; margin-bottom: 40px; display: flex; justify-content: space-between; align-items: flex-start; }}
                h1 {{ margin: 0; font-size: 2.2rem; font-weight: 800; letter-spacing: -0.5px; }}
                h2 {{ font-size: 1.4rem; color: #1e272e; margin: 0 0 20px 0; border-left: 4px solid {PRIMARY_COLOUR}; padding-left: 15px; }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 50px; }}
                .stat-card {{ background: #fff; border: 1px solid #edf2f7; padding: 25px 15px; border-radius: 12px; text-align: center; }}
                .stat-value {{ font-size: 2.2rem; font-weight: 800; color: {PRIMARY_COLOUR}; margin-bottom: 8px; }}
                .stat-label {{ font-size: 0.75rem; color: #718096; text-transform: uppercase; font-weight: 600; letter-spacing: 1.2px; }}
                .section {{ margin-bottom: 50px; }}
                table {{ width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 15px; border: 1px solid #edf2f7; border-radius: 8px; overflow: hidden; }}
                th {{ background: #f8fafc; text-align: left; padding: 15px; font-size: 0.85rem; text-transform: uppercase; color: #4a5568; border-bottom: 2px solid #edf2f7; }}
                td {{ padding: 15px; border-bottom: 1px solid #edf2f7; font-size: 0.95rem; }}
                footer {{ margin-top: 60px; text-align: center; font-size: 0.85rem; color: #a0aec0; border-top: 1px solid #edf2f7; padding-top: 25px; }}
                .badge {{ padding: 6px 12px; border-radius: 20px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; }}
                .badge-high {{ background: #c6f6d5; color: #22543d; }}
                .badge-urgent {{ background: #feebc8; color: #744210; }}
            </style>
        </head>
        <body>
            <div class="container">
                <header>
                    <div>
                        <h1>{AGENT_NAME}</h1>
                        <p style="color: #4a5568; margin: 8px 0 0 0; font-size: 1.1rem;">Live Performance Report for <strong>{BROKERAGE_NAME}</strong></p>
                    </div>
                    {f'<img src="{AGENT_CONFIG.get("brokerage_logo_url", "")}" height="60">' if AGENT_CONFIG.get("brokerage_logo_url") else ""}
                </header>

                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">{safe_int(metrics.get('total_scans', 0)):,}</div>
                        <div class="stat-label">Total Scans</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{safe_int(metrics.get('total_alerts', 0)):,}</div>
                        <div class="stat-label">Matches Found</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{safe_int(metrics.get('total_videos', 0)):,}</div>
                        <div class="stat-label">Videos Created</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{len(buyers):,}</div>
                        <div class="stat-label">Active Buyers</div>
                    </div>
                </div>

                <div class="section">
                    <h2>Persistent Buyer Profiles</h2>
                    <table>
                        <thead>
                            <tr><th>Client Name</th><th>Budget Range</th><th>Beds</th><th>Neighbourhood</th><th>Status</th></tr>
                        </thead>
                        <tbody>{buyer_rows}</tbody>
                    </table>
                </div>

                <div class="section">
                    <h2>Real-Time Matches</h2>
                    <table>
                        <thead>
                            <tr><th>Address</th><th>Price</th><th>Date Detected</th><th>Score Rank</th></tr>
                        </thead>
                        <tbody>{alert_rows}</tbody>
                    </table>
                </div>

                <footer>
                    Powered by <strong>416Homes Technology</strong> • Last Updated: {datetime.now().strftime('%b %d, %Y %H:%M:%S')}
                </footer>
            </div>
        </body>
        </html>
        """
        return html_content
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return HTMLResponse(content=f"<h1>Report Error</h1><p>{str(e)}</p>", status_code=500)


# ── Pydantic models ─────────────────────────────────────────────────────────

class ValuationRequest(BaseModel):
    neighbourhood: str = ""
    property_type: str = "Condo Apt"
    city: str = "Toronto"
    bedrooms: int = 1
    bathrooms: int = 1
    sqft: int = 600
    list_price: int = 700000


class VideoOrderRequest(BaseModel):
    listing_url: str
    agent_email: str
    agent_name: str = ""
    voice: str = "female_luxury"


# ══════════════════════════════════════════════════════════════════════════════
#  LISTING ENDPOINTS (same as before)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "agent_running": listing_agent.running,
        "service": "416Homes Demo API",
        "version": "3.0.0",
        "listings_cached": len(LISTINGS_CACHE),
        "video_jobs": len(VIDEO_JOBS)
    }


@app.get("/listings")
async def get_listings(
    city: str = "Toronto", limit: int = 20,
    min_price: Optional[int] = None, max_price: Optional[int] = None,
    bedrooms: Optional[str] = None, bathrooms: Optional[str] = None,
):
    rows = LISTINGS_CACHE[:]
    city_lower = city.lower()
    if city_lower != "gta":
        rows = [r for r in rows if city_lower in r.get("city", "").lower()
                or city_lower in r.get("address", "").lower()]
    if min_price:
        rows = [r for r in rows if (r.get("price") or 0) >= min_price]
    if max_price:
        rows = [r for r in rows if (r.get("price") or 0) <= max_price]
    if bedrooms:
        try:
            min_beds = int(bedrooms.replace("+", ""))
            rows = [r for r in rows if _safe_int(r.get("bedrooms")) >= min_beds]
        except ValueError:
            pass
    if bathrooms:
        try:
            min_baths = int(bathrooms.replace("+", ""))
            rows = [r for r in rows if _safe_int(r.get("bathrooms")) >= min_baths]
        except ValueError:
            pass

    result = []
    for r in rows[:limit]:
        result.append({
            "id": r.get("id", ""), "address": r.get("address", "Unknown"),
            "price": r.get("price") or 0,
            "bedrooms": str(r.get("bedrooms") or ""),
            "bathrooms": str(r.get("bathrooms") or ""),
            "area": str(r.get("sqft") or ""),
            "lat": r.get("lat"), "lng": r.get("lng"),
            "source": r.get("source", "unknown"),
            "url": r.get("url", ""),
            "scraped_at": r.get("scraped_at", ""),
            "strategy": "live_scrape",
        })
    return result


@app.post("/valuate")
async def valuate(req: ValuationRequest):
    base = {"Toronto": 800, "Mississauga": 650}.get(req.city, 700)
    multiplier = {"Detached": 1.3, "Semi-Detached": 1.15, "Townhouse": 1.1}.get(req.property_type, 1.0)
    estimated = int(req.sqft * base * multiplier) + req.bedrooms * 20000 + req.bathrooms * 15000
    ratio = req.list_price / estimated if estimated else 1
    if ratio < 0.90:
        analysis = "Listed below estimated value — potential opportunity"
    elif ratio > 1.10:
        analysis = "Listed above estimated value — room to negotiate"
    else:
        analysis = "Priced in line with estimated market value"
    return {
        "estimated_value": estimated, "confidence": 0.72,
        "market_analysis": analysis + " (demo formula)",
        "price_per_sqft": round(estimated / req.sqft, 2) if req.sqft else None,
        "comparable_sales": [],
    }


@app.get("/")
async def root():
    return JSONResponse({"message": "416Homes Demo API", "docs": "/docs",
                         "listings_cached": len(LISTINGS_CACHE),
                         "video_jobs": len(VIDEO_JOBS)})


# ══════════════════════════════════════════════════════════════════════════════
#  VIDEO PIPELINE ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/video/create-checkout")
async def create_video_job(req: VideoOrderRequest):
    """
    Create a video job. In production this would redirect to Stripe first.
    In demo/dev mode we skip payment and start processing immediately.
    """
    job_id = str(uuid.uuid4())[:8]

    job = {
        "job_id": job_id,
        "listing_url": req.listing_url,
        "agent_email": req.agent_email,
        "agent_name": req.agent_name,
        "voice": req.voice,
        "status": "processing",
        "progress_step": "scrape",
        "progress_message": "Connecting to listing...",
        "listing_address": "",
        "listing_data": {},
        "script_data": {},
        "video_path": None,
        "error": None,
        "created_at": datetime.utcnow().isoformat(),
    }

    VIDEO_JOBS[job_id] = job
    logger.info(f"🎬 Video job {job_id} created for {req.listing_url}")

    # Start the pipeline in background
    asyncio.create_task(process_video_pipeline(job_id))

    return {"job_id": job_id}

@app.post("/video/create-custom")
async def create_video_job_custom(
    address: str = Form(...),
    price: str = Form(""),
    beds: str = Form(""),
    baths: str = Form(""),
    sqft: str = Form(""),
    property_type: str = Form(""),
    description: str = Form(""),
    agent_email: str = Form(...),
    agent_name: str = Form(...),
    voice: str = Form("female_luxury"),
    photos: List[UploadFile] = File(...),
    music: Optional[UploadFile] = File(None)
):
    """
    Create a custom video job with uploaded photos and optional music.
    """
    from video_pipeline.video_producer import TEMP_DIR
    job_id = str(uuid.uuid4())[:8]

    # Save uploaded files to the job directory
    job_dir = TEMP_DIR / job_id
    photos_dir = job_dir / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)

    for i, photo in enumerate(photos):
        photo_path = photos_dir / f"photo_{i}.jpg"
        photo_path.write_bytes(await photo.read())
        logger.info(f"📸 Saved custom uploaded photo {i+1} to {photo_path}")
        
    if music:
        music_path = job_dir / "custom_bgmusic.mp3"
        music_path.write_bytes(await music.read())

    listing_data = {
        "address": address,
        "price": price,
        "beds": beds,
        "baths": baths,
        "sqft": sqft,
        "property_type": property_type,
        "description": description,
    }

    job = {
        "job_id": job_id,
        "listing_url": "custom_upload",
        "agent_email": agent_email,
        "agent_name": agent_name,
        "voice": voice,
        "status": "processing",
        "progress_step": "scrape",
        "progress_message": "Initializing custom job...",
        "listing_address": address,
        "listing_data": listing_data,
        "script_data": {},
        "video_path": None,
        "error": None,
        "created_at": datetime.utcnow().isoformat(),
        "is_custom": True,
    }

    VIDEO_JOBS[job_id] = job
    logger.info(f"🎬 Custom Video job {job_id} created for {address}")

    asyncio.create_task(process_video_pipeline(job_id))

    return {"job_id": job_id}



@app.get("/video/status/{job_id}")
async def get_video_status(job_id: str, request: Request):
    """Return current status of a video job for the frontend to poll."""
    job = VIDEO_JOBS.get(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"error": "Job not found"})

    out = {
        "job_id": job["job_id"],
        "status": job["status"],
        "progress_step": job["progress_step"],
        "progress_message": job["progress_message"],
        "listing_address": job.get("listing_address", ""),
        "script_data": job.get("script_data", {}),
        "cinematic_prompts": job.get("cinematic_prompts", []),
        "error": job.get("error"),
    }
    # When complete and we have a file, include a playable video_url (same origin so <video src> works)
    video_path = job.get("video_path")
    if job["status"] == "complete" and video_path and Path(video_path).exists():
        base = str(request.base_url).rstrip("/")
        out["video_url"] = f"{base}/video/download/{job_id}"
    return out


@app.get("/video/download/{job_id}")
async def download_video(job_id: str):
    """Download the generated MP4 video."""
    job = VIDEO_JOBS.get(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"error": "Job not found"})
    video_path = job.get("video_path")
    if video_path and Path(video_path).exists():
        resp = FileResponse(
            path=video_path,
            media_type="video/mp4",
            filename=f"416homes_{job_id}.mp4",
        )
        resp.headers["Accept-Ranges"] = "bytes"
        return resp
    return JSONResponse(status_code=202, content={"message": "Video still processing or not available",
                         "script": job.get("script_data", {})})


# ══════════════════════════════════════════════════════════════════════════════
#  VIDEO PIPELINE — Real processing with Gemini
# ══════════════════════════════════════════════════════════════════════════════

async def process_video_pipeline(job_id: str):
    """
    Full pipeline — ALL REAL:
      1. Scrape listing data + photos   ← DrissionPage
      2. Generate voiceover script      ← Gemini 2.0 Flash
      3. Record voiceover + gen music   ← ElevenLabs + Suno (optional)
      4. Animate photos Ken Burns       ← ffmpeg zoompan
      5. Assemble final video           ← ffmpeg concat + audio mix
    """
    from video_pipeline.video_producer import produce_video
    from pathlib import Path

    job = VIDEO_JOBS[job_id]

    try:
        # ── Step 1: Scrape listing data ──────────────────────────────────
        if job.get("is_custom"):
            update_job(job_id, "processing", "scrape", "Using custom uploaded listing details...")
            await asyncio.sleep(1)
            listing_data = job.get("listing_data", {})
            # If custom photos were uploaded, they are already saved in job_dir/photos
        else:
            update_job(job_id, "processing", "scrape", "Fetching listing photos & details...")
            await asyncio.sleep(1)

            listing_data = await scrape_listing_from_url(job["listing_url"])

            if listing_data:
                job["listing_data"] = listing_data
                job["listing_address"] = listing_data.get("address", "Unknown")
                update_job(job_id, "processing", "scrape",
                           f"Found: {listing_data.get('address', 'listing')} — "
                           f"{listing_data.get('beds', '?')} bed, {listing_data.get('baths', '?')} bath, "
                           f"{listing_data.get('price', '?')}")
            else:
                listing_data = build_fallback_listing(job["listing_url"])
                job["listing_data"] = listing_data
                job["listing_address"] = listing_data.get("address", "Unknown Listing")
                update_job(job_id, "processing", "scrape",
                           f"Using listing URL details: {listing_data.get('address', 'listing')}")

        await asyncio.sleep(1)

        # ── Step 2: Generate script with Gemini ──────────────────────────
        update_job(job_id, "processing", "script", "Gemini is writing your voiceover script...")

        script_data = await generate_script_with_gemini(listing_data)

        if script_data:
            job["script_data"] = script_data
            update_job(job_id, "processing", "script",
                       f'Script complete — "{script_data.get("headline", "")}"')
            logger.info(f"🎬 Job {job_id} — Script: {script_data.get('headline', '')}")
        else:
            update_job(job_id, "failed", "script", "Script generation failed")
            await send_notification(
                f"❌ <b>Video Failed</b>\n"
                f"📍 {job['listing_url']}\n"
                f"Error: Script generation failed"
            )
            return

        # ── Steps 3-5: Real video production (ElevenLabs + ffmpeg) ────────
        async def on_progress(step, msg):
            update_job(job_id, "processing", step, msg)
            if step == "animate" and "Shot" in msg:
                # msg like "Shot 1/6: Extremely slow..."
                try:
                    prompt_part = msg.split(": ", 1)[1]
                    if "cinematic_prompts" not in job:
                        job["cinematic_prompts"] = []
                    job["cinematic_prompts"].append(prompt_part)
                except: pass

        video_path = await produce_video(
            listing_url=job.get("listing_url", ""),
            listing_data=listing_data,
            script_data=script_data,
            voice=job.get("voice", "female_luxury"),
            on_progress=on_progress,
            job_id=job_id,
        )

        if video_path and video_path.exists():
            job["video_path"] = str(video_path)
            size_mb = video_path.stat().st_size / (1024 * 1024)
            update_job(job_id, "complete", "complete",
                       f"Video ready! {size_mb:.1f} MB — {listing_data.get('address', '')}")
            logger.info(f"✅ Video job {job_id} completed: {video_path} ({size_mb:.1f} MB)")
            
            # Notify Telegram
            await send_notification(
                f"🎬 <b>Video Ready!</b>\n"
                f"📍 {listing_data.get('address', job['listing_url'])}\n"
                f"✅ Your cinematic video has been generated.\n"
                f"📁 <a href='http://localhost:8000/video/download/{job_id}'>Download Video</a>"
            )
        else:
            update_job(job_id, "failed", "assemble", "Video assembly failed — check logs")
            logger.error(f"❌ Video job {job_id} — produce_video returned None")
            await send_notification(
                f"❌ <b>Video Failed</b>\n"
                f"📍 {job['listing_url']}\n"
                f"Error: Video assembly failed"
            )

    except Exception as e:
        logger.error(f"❌ Video pipeline error for job {job_id}: {e}")
        update_job(job_id, "failed", job.get("progress_step", "scrape"), str(e))


def update_job(job_id: str, status: str, step: str, message: str):
    """Update job state in-memory."""
    job = VIDEO_JOBS.get(job_id)
    if job:
        job["status"] = status
        job["progress_step"] = step
        job["progress_message"] = message


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 1: Scrape listing data from URL
# ══════════════════════════════════════════════════════════════════════════════

async def scrape_listing_from_url(url: str) -> Optional[Dict[str, Any]]:
    """
    Try to scrape listing details from the provided URL.
    Supports Zoocasa, Condos.ca, Realtor.ca, Zillow URLs.
    Falls back to parsing data from the URL itself.
    """
    try:
        return await asyncio.to_thread(_scrape_listing_sync, url)
    except Exception as e:
        logger.warning(f"Listing scrape failed: {e}")
        return None


def _scrape_listing_sync(url: str) -> Optional[Dict[str, Any]]:
    """Sync scraper that uses DrissionPage to fetch listing details."""
    try:
        from scraper.browser_util import create_browser
        page = create_browser(headless=False)

        logger.info(f"📄 Scraping listing: {url}")
        page.get(url, retry=1, interval=1, timeout=15)
        # Get the page text
        page.wait.load_start()
        body_text = page.html or ''
        title = page.title or ''

        # Check if listing exists
        not_found_keywords = [
            "no longer exists", 
            "listing not found", 
            "page not found", 
            "start a new search",
            "listing has been removed"
        ]
        if any(kw in body_text.lower() for kw in not_found_keywords):
            logger.error(f"❌ Listing non-existent or removed: {url}")
            page.quit()
            raise ValueError(f"Listing at {url} no longer exists.")

        # Try to extract structured data
        listing = {}

        # Price
        price_match = re.search(r'\$[\d,]+', body_text)
        if price_match:
            listing["price"] = price_match.group(0)

        # Address — usually in the title or first heading
        listing["address"] = title.split('|')[0].strip() if title else "Unknown"
        listing["address"] = listing["address"].split(' - ')[0].strip()

        # Beds / Baths / Sqft from page text
        beds_match = re.search(r'(\d+)\s*(?:bed|bedroom|bd)', body_text, re.IGNORECASE)
        baths_match = re.search(r'(\d+)\s*(?:bath|bathroom|ba)', body_text, re.IGNORECASE)
        sqft_match = re.search(r'([\d,]+)\s*(?:sq\.?\s*ft|sqft)', body_text, re.IGNORECASE)

        listing["beds"] = beds_match.group(1) if beds_match else "2"
        listing["baths"] = baths_match.group(1) if baths_match else "1"
        listing["sqft"] = sqft_match.group(1).replace(',', '') if sqft_match else "800"

        # Property type
        for pt in ["Detached", "Semi-Detached", "Townhouse", "Condo", "Apartment"]:
            if pt.lower() in body_text.lower():
                listing["property_type"] = pt
                break
        else:
            listing["property_type"] = "Condo"

        # Description — first 300 chars of body
        desc_match = re.search(r'(?:description|about|overview)[:\s]*([^.!]{20,300})', body_text, re.IGNORECASE)
        listing["description"] = desc_match.group(1).strip() if desc_match else f"Beautiful property at {listing['address']}"

        page.quit()
        return listing

    except Exception as e:
        logger.warning(f"DrissionPage listing scrape failed: {e}")
        return None


def build_fallback_listing(url: str) -> Dict[str, Any]:
    """Extract whatever we can from the URL string itself."""
    listing = {
        "address": "Unknown Address",
        "price": "$799,000",
        "beds": "2",
        "baths": "1",
        "sqft": "800",
        "property_type": "Condo",
        "description": "A beautiful property in the Greater Toronto Area.",
    }

    # Try to parse address from URL path
    parts = url.split('/')
    for part in parts:
        if any(s in part.lower() for s in ['ave', 'st-', 'rd-', 'dr-', 'cres', 'blvd', 'trail']):
            listing["address"] = part.replace('-', ' ').title()
            break

    if 'mississauga' in url.lower():
        listing["address"] += ", Mississauga, ON"
    elif 'toronto' in url.lower():
        listing["address"] += ", Toronto, ON"

    return listing


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 2: Generate script with real Gemini API
# ══════════════════════════════════════════════════════════════════════════════

async def generate_script_with_gemini(listing: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Call Gemini 2.0 Flash to generate a real cinematic voiceover script.
    Returns headline, voiceover_script, music_mood, key_features.
    """
    try:
        from google import genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not set")
            return _fallback_script(listing)

        client = genai.Client(api_key=api_key)
        model_id = "gemini-2.5-flash"
        
        prompt = f"""You are a luxury real estate video scriptwriter. Create a cinematic 30-second voiceover script for this property listing.

Property Details:
- Address: {listing.get('address', 'Unknown')}
- Price: {listing.get('price', '$799,000')}
- Bedrooms: {listing.get('beds', '2')}
- Bathrooms: {listing.get('baths', '1')}
- Square Feet: {listing.get('sqft', '800')}
- Property Type: {listing.get('property_type', 'Condo')}
- Description: {listing.get('description', 'Beautiful property in Toronto')}

CRITICAL INSTRUCTION FOR VOICEOVER:
You MUST base the `voiceover_script` strictly on the provided `Description` above. Do not invent amenities or features that are not explicitly stated in the description or the metadata. Paint a warm, aspirational picture of the lifestyle and neighborhood using the factual details provided.

Return ONLY valid JSON (no markdown, no code fences) with these exact keys:
{{
  "headline": "A catchy 5-8 word headline for the video opening",
  "voiceover_script": "A cinematic 60-80 word voiceover script based purely on the provided Description. Warm, inviting, and factual to the listing specs.",
  "music_mood": "one of: cinematic_luxury, warm_inspiring, modern_elegant, cozy_intimate",
  "music_prompt": "A highly specific 20-30 word prompt for an AI music generator (like Suno) to create a custom background track for this specific listing. e.g., 'A soft classical piano track with no vocals, elegant strings, building to an inspiring crescendo, fitting for a $2.5M luxury home'.",
  "key_features": ["feature1", "feature2", "feature3", "feature4"],
  "scene_prompts": [
    "Cinematic camera prompt for photo 1 — describe the cinematic camera movement (dolly, pan, push-in) and the mood (golden hour, warm light). 20-30 words.",
    "Cinematic camera prompt for photo 2",
    "Cinematic camera prompt for photo 3",
    "Cinematic camera prompt for photo 4",
    "Cinematic camera prompt for photo 5",
    "Cinematic camera prompt for photo 6"
  ]
}}"""

        response = await asyncio.to_thread(client.models.generate_content, model=model_id, contents=prompt)
        text = response.text.strip()

        # Clean up markdown fences if present
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)

        script_data = json.loads(text)

        # Validate required keys
        required = ["headline", "voiceover_script", "music_mood", "key_features", "music_prompt"]
        if all(k in script_data for k in required):
            # Ensure scene_prompts exists
            if "scene_prompts" not in script_data:
                script_data["scene_prompts"] = []
            logger.info(f"✨ Gemini script generated: \"{script_data['headline']}\"")
            return script_data
        else:
            logger.warning("Gemini response missing required keys, using fallback")
            return _fallback_script(listing)

    except json.JSONDecodeError as e:
        logger.warning(f"Gemini returned invalid JSON: {e}")
        return _fallback_script(listing)
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return _fallback_script(listing)


def _fallback_script(listing: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback script when Gemini is unavailable."""
    addr = listing.get("address", "this beautiful property")
    return {
        "headline": "Your Dream Home Awaits",
        "voiceover_script": (
            f"Welcome to {addr}. "
            f"This stunning {listing.get('beds', '2')}-bedroom, {listing.get('baths', '1')}-bathroom "
            f"{listing.get('property_type', 'home').lower()} offers {listing.get('sqft', '800')} square feet "
            f"of thoughtfully designed living space. Priced at {listing.get('price', '$799,000')}, "
            f"this is a rare opportunity to own in one of the GTA's most sought-after neighbourhoods. "
            f"Schedule your private showing today."
        ),
        "music_mood": "warm_inspiring",
        "key_features": ["Prime location", "Modern finishes", "Spacious layout", "Natural light"],
        "scene_prompts": [
            "Cinematic slow dolly forward through elegant living room, warm golden hour sunlight. Luxury real estate.",
            "Smooth pan from left to right across modern kitchen, marble countertops gleaming. Magazine quality.",
            "Gentle push-in revealing bedroom with natural light, soft shadows. Premium property walkthrough.",
            "Slow aerial reveal of bathroom with spa-like finishes, warm ambient lighting. Upscale living.",
            "Wide cinematic shot of outdoor space or building exterior, golden hour. Real estate showcase.",
            "Slow orbiting shot of the main living area, highlighting architectural details. Luxury home tour.",
        ],
    }


# ══════════════════════════════════════════════════════════════════════════════
#  BACKGROUND SCRAPER (listings cache)
# ══════════════════════════════════════════════════════════════════════════════

async def run_scrapers():
    """Run scrapers in background on startup."""
    global LISTINGS_CACHE, SCRAPE_STATUS
    SCRAPE_STATUS["running"] = True
    logger.info("🚀 Starting background scrape of Zoocasa + Condos.ca...")

    all_listings = []

    try:
        from scraper.zoocasa import scrape_zoocasa
        logger.info("Scraping Zoocasa...")
        zoocasa = await scrape_zoocasa("toronto")
        all_listings.extend(zoocasa)
        logger.info(f"✅ Zoocasa: {len(zoocasa)} listings")
    except Exception as e:
        logger.error(f"❌ Zoocasa failed: {e}")

    try:
        from scraper.condos_ca import scrape_condos_ca
        logger.info("Scraping Condos.ca...")
        condos = await scrape_condos_ca("toronto")
        all_listings.extend(condos)
        logger.info(f"✅ Condos.ca: {len(condos)} listings")
    except Exception as e:
        logger.error(f"❌ Condos.ca failed: {e}")

    LISTINGS_CACHE = all_listings
    SCRAPE_STATUS = {"running": False, "done": True, "count": len(all_listings)}
    logger.info(f"🏠 Total listings cached: {len(all_listings)}")




# ══════════════════════════════════════════════════════════════════════════════
#  LISTING AGENT ENDPOINTS (Zentro-style 24/7 monitor)
# ══════════════════════════════════════════════════════════════════════════════

from listing_agent import agent as listing_agent


@app.post("/agent/start")
async def agent_start(req: dict = {}):
    """Start the 24/7 listing monitor."""
    criteria = req.get("criteria", None)
    interval = req.get("interval_minutes", 30)
    auto_video = req.get("auto_video", False)
    auto_video_min_price = req.get("auto_video_min_price", 1_000_000)
    result = listing_agent.start(
        criteria=criteria,
        interval_minutes=interval,
        auto_video=auto_video,
        auto_video_min_price=auto_video_min_price,
    )
    return result


@app.post("/agent/stop")
async def agent_stop():
    """Stop the listing monitor."""
    return listing_agent.stop()


@app.get("/agent/status")
async def agent_status():
    """Get agent status."""
    return listing_agent.get_status()


@app.get("/agent/alerts")
async def agent_alerts(unseen_only: bool = False, limit: int = 50):
    """Get listing alerts."""
    return {"alerts": listing_agent.get_alerts(unseen_only=unseen_only, limit=limit)}


@app.post("/agent/alerts/{alert_id}/seen")
async def agent_mark_seen(alert_id: str):
    """Mark an alert as seen."""
    if listing_agent.mark_seen(alert_id):
        return {"status": "ok"}
    return {"status": "not_found"}


@app.put("/agent/criteria")
async def agent_update_criteria(criteria: dict):
    """Update agent search criteria."""
    return listing_agent.update_criteria(criteria)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _safe_int(val, default=0):
    try:
        return int(str(val).replace("+", "").strip())
    except (ValueError, TypeError):
        return default


# ── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("""
=======================================================
         416Homes Demo API v3.0                      
                                                     
  API:       http://localhost:8000                    
  Docs:      http://localhost:8000/docs               
                                                     
  Serve HTML separately:                             
    python -m http.server 3000                       
    Dashboard: http://localhost:3000/dashboard.html   
    Video:     http://localhost:3000/416homes-video.html 
=======================================================
""")
    uvicorn.run(app, host="0.0.0.0", port=8000)
