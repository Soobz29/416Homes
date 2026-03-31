"""
416Homes API — api/main.py

WHAT THIS FILE DOES
────────────────────
FastAPI backend that serves three things:
  1. /listings       → reads real rows from Supabase `listings` table
  2. /valuate        → runs the real LightGBM model from valuation/model.py
  3. /video-jobs     → creates / reads video jobs via the pipeline

WHY WE REMOVED THE MOCK DATA
──────────────────────────────
Windsurf left five hardcoded fake listings and a hardcoded price formula.
Those worked for an early demo but mean the dashboard never shows real scraped
data even after the scraper has run and populated Supabase.

HOW THE REAL FLOW WORKS NOW
────────────────────────────
  scraper runs  →  listings land in Supabase
  dashboard calls GET /listings
  ↳  this file queries Supabase, applies filters, returns real rows
  dashboard calls POST /valuate
  ↳  this file loads valuation_model.pkl, calls predict(), returns result
"""

import uuid

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

from valuation.model import ValuationModel
from video_pipeline.pipeline import create_video_job, get_video_job_status

load_dotenv()
logger = logging.getLogger(__name__)

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="416Homes API",
    description="Toronto Real Estate Intelligence Platform",
    version="2.0.0",
)

# CORS: allow requests from the dashboard HTML file served on any port
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Shared clients ─────────────────────────────────────────────────────────────
#
# WHY create these at module load time?
# Creating a Supabase client or loading a .pkl file takes ~200ms each.
# If we did it inside every request handler, every API call would be 200ms
# slower. By creating them once when the server starts, all requests share the
# same already-initialized objects. This is called a "singleton" pattern.

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY"),
)

# ValuationModel wraps our LightGBM model.
# load_model() reads valuation_model.pkl from disk.
# If the file doesn't exist yet (model hasn't been trained), predict() will
# gracefully return an error dict rather than crashing the whole API.
valuation_model = ValuationModel()
valuation_model.load_model()


# ── Pydantic models ────────────────────────────────────────────────────────────
#
# Pydantic models do two things:
#   1. They validate incoming JSON (FastAPI rejects bad data before our code
#      even runs, returning a clear 422 error to the caller)
#   2. They document the API shape (shows up in /docs automatically)
#
# Optional[X] = None means the field is allowed to be missing — FastAPI won't
# reject the request if it's absent, and we get None in our code.

class ListingResponse(BaseModel):
    id: str
    address: str
    price: int
    bedrooms: Optional[str] = None
    bathrooms: Optional[str] = None
    area: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    source: str
    url: str
    scraped_at: str
    strategy: str


class ValuationRequest(BaseModel):
    neighbourhood: str
    property_type: str
    city: str
    bedrooms: int
    bathrooms: int
    sqft: int
    list_price: int


class ValuationResponse(BaseModel):
    estimated_value: int
    confidence: float
    market_analysis: str
    price_per_sqft: Optional[float] = None
    comparable_sales: Optional[List[dict]] = None


class VideoJobRequest(BaseModel):
    listing_url: str
    customer_email: Optional[str] = None
    agent_email: Optional[str] = None
    customer_name: Optional[str] = None
    agent_name: Optional[str] = None
    voice: Optional[str] = "female_luxury"
    tier: Optional[str] = "cinematic"
    price_cad: Optional[float] = None
    use_veo: Optional[bool] = True


class VideoJobResponse(BaseModel):
    id: str
    status: str
    message: str


def _normalize_video_job_payload(row: Dict[str, Any]) -> Dict[str, Any]:
    if not row:
        return row
    out = dict(row)
    status = out.get("status") or "pending"
    step_map = {
        "pending": "scrape",
        "generating_script": "script",
        "script_generated": "audio",
        "generating_audio": "audio",
        "audio_generated": "animate",
        "generating_video": "animate",
        "completed": "assemble",
        "failed": "assemble",
    }
    msg_map = {
        "pending": "Queued — preparing photos…",
        "generating_script": "Generating script…",
        "script_generated": "Script ready — preparing audio…",
        "generating_audio": "Generating audio…",
        "audio_generated": "Rendering video…",
        "generating_video": "Rendering video…",
        "completed": "Done",
        "failed": "Failed",
    }
    out["progress_step"] = step_map.get(status, "scrape")
    out["progress_message"] = msg_map.get(status, "Processing…")
    if status == "completed":
        out["status"] = "complete"
    ld = out.get("listing_data")
    if isinstance(ld, str):
        try:
            import json as _json

            ld = _json.loads(ld)
        except Exception:
            ld = {}
    if isinstance(ld, dict) and ld.get("address"):
        out["listing_address"] = ld.get("address")
    if out.get("error_message"):
        out["error"] = out["error_message"]
    return out


# ── Health check ───────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Quick ping to confirm the API is alive. Used by GitHub Actions health-check.yml."""
    return {"status": "healthy", "service": "416Homes API", "version": "2.0.0"}


# ── Listings ───────────────────────────────────────────────────────────────────

@app.get("/listings", response_model=List[ListingResponse])
async def get_listings(
    city: str = "Toronto",
    limit: int = 20,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    bedrooms: Optional[str] = None,
    bathrooms: Optional[str] = None,
):
    """
    Return real listings from Supabase, with optional filter parameters.

    HOW THE SUPABASE QUERY WORKS
    ──────────────────────────────
    supabase.table("listings")   → target the `listings` table
      .select("*")               → return all columns (we could list specific ones)
      .ilike("address", f"%{city}%")  → case-insensitive substring match on address
      .order("scraped_at", desc=True) → newest first
      .limit(limit * 3)          → fetch more than needed so we can apply Python filters
      .execute()                 → actually runs the query, returns a response object

    We fetch `limit * 3` rows because Supabase can't easily apply the Python-side
    filters (min_price etc.) at the DB level with our current schema. Fetching
    extras means we have enough rows left after filtering to fill the limit.
    """
    try:
        query = (
            supabase.table("listings")
            .select("*")
            .ilike("address", f"%{city}%")
            .order("scraped_at", desc=True)
            .limit(limit * 3)
        )
        result = query.execute()
        rows = result.data or []

        # Apply remaining filters in Python.
        # WHY in Python? Supabase PostgREST supports .gte/.lte for numbers but
        # our bedrooms/bathrooms are stored as TEXT (e.g. "2+") so we can't
        # use a numeric comparison at the DB level reliably.
        if min_price:
            rows = [r for r in rows if (r.get("price") or 0) >= min_price]
        if max_price:
            rows = [r for r in rows if (r.get("price") or 0) <= max_price]
        if bedrooms:
            rows = [
                r for r in rows
                if _parse_int(r.get("bedrooms", "0")) >= _parse_int(bedrooms)
            ]
        if bathrooms:
            rows = [
                r for r in rows
                if _parse_int(r.get("bathrooms", "0")) >= _parse_int(bathrooms)
            ]

        # Trim to requested limit and ensure required fields have defaults
        return [_normalise_listing(r) for r in rows[:limit]]

    except Exception as e:
        logger.error(f"/listings error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch listings")


@app.get("/listings/search")
async def search_listings_endpoint(q: str, limit: int = 10):
    """Vector-similarity search. Requires the pgvector extension and embeddings in Supabase."""
    from memory.store import search_listings
    try:
        return await search_listings(q, limit)
    except Exception as e:
        logger.error(f"/listings/search error: {e}")
        return []


# ── Valuation ──────────────────────────────────────────────────────────────────

@app.post("/valuate", response_model=ValuationResponse)
async def valuate_property(request: ValuationRequest):
    """
    Run the real LightGBM model against the request data.

    HOW THE MODEL INTEGRATION WORKS
    ──────────────────────────────────
    valuation_model.predict() expects a dict whose keys match the feature columns
    the model was trained on:
      bedrooms, bathrooms, sqft, property_type, neighbourhood, city

    It returns a dict with estimated_value, confidence, price_per_sqft.
    If the model file doesn't exist yet (train it first with `python valuation/model.py`)
    it returns {'error': 'Model not loaded'}, which we catch and fall back on.

    FALLBACK
    ─────────
    If the model hasn't been trained yet, we fall back to a simple formula.
    This means the API keeps working during development even without the .pkl file.
    The fallback is clearly labelled in the market_analysis string so you know
    which path fired.
    """
    property_data = {
        "bedrooms": request.bedrooms,
        "bathrooms": request.bathrooms,
        "sqft": request.sqft,
        "property_type": request.property_type,
        "neighbourhood": request.neighbourhood,
        "city": request.city,
    }

    result = valuation_model.predict(property_data)

    # If model isn't loaded or predict() hit an exception, fall back gracefully
    if "error" in result:
        logger.warning(f"Model predict() returned error: {result['error']} — using fallback formula")
        estimated = _fallback_estimate(request)
        market_analysis = _market_signal(estimated, request.list_price) + " (fallback formula — train model first)"
        return ValuationResponse(
            estimated_value=estimated,
            confidence=0.60,
            market_analysis=market_analysis,
        )

    # Fetch nearby sold comps from Supabase to show in the dashboard
    comps = _get_comps(request.neighbourhood)

    return ValuationResponse(
        estimated_value=result["estimated_value"],
        confidence=result["confidence"],
        market_analysis=_market_signal(result["estimated_value"], request.list_price),
        price_per_sqft=result.get("price_per_sqft"),
        comparable_sales=comps,
    )


# ── Video jobs ─────────────────────────────────────────────────────────────────

@app.post("/video-jobs", response_model=VideoJobResponse)
@app.post("/api/video-jobs", response_model=VideoJobResponse)
async def create_video_job_endpoint(request: VideoJobRequest):
    """Create a new video job. Persisted to Supabase by the pipeline."""
    try:
        email = request.agent_email or request.customer_email or ""
        name = request.agent_name or request.customer_name or ""
        if not email:
            raise HTTPException(status_code=422, detail="agent_email or customer_email is required")

        listing_meta: Dict[str, Any] = {}
        if request.voice is not None:
            listing_meta["voice"] = request.voice
        if request.tier is not None:
            listing_meta["tier"] = request.tier
        if request.price_cad is not None:
            listing_meta["price_cad"] = request.price_cad
        if request.use_veo is not None:
            listing_meta["use_veo"] = request.use_veo

        job_id = await create_video_job(
            listing_url=request.listing_url,
            customer_email=email,
            customer_name=name or None,
            listing_data=listing_meta or None,
        )
        if not job_id:
            raise HTTPException(status_code=500, detail="Pipeline failed to create job")
        return VideoJobResponse(
            id=job_id,
            status="pending",
            message="Video job created successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("/video-jobs POST error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create video job")


@app.post("/api/video-jobs/custom", response_model=VideoJobResponse)
async def create_custom_video_job(
    address: str = Form(...),
    price: str = Form(""),
    beds: str = Form(""),
    baths: str = Form(""),
    agent_email: str = Form(...),
    agent_name: str = Form(""),
    voice: str = Form("female_luxury"),
    photos: List[UploadFile] = File(...),
    music: Optional[UploadFile] = File(None),
):
    """Create video job from uploaded photos."""
    if len(photos) < 4 or len(photos) > 10:
        raise HTTPException(status_code=400, detail="Upload between 4 and 10 photos")
    try:
        job_id = str(uuid.uuid4())
        tmp_root = Path(os.getenv("VIDEO_JOB_TMP", "/tmp")) / "video_jobs"
        job_dir = tmp_root / job_id
        photos_dir = job_dir / "photos"
        photos_dir.mkdir(parents=True, exist_ok=True)

        for i, photo in enumerate(photos):
            ext = Path(photo.filename or "photo.jpg").suffix or ".jpg"
            dest = photos_dir / f"photo_{i + 1:03d}{ext}"
            contents = await photo.read()
            dest.write_bytes(contents)

        if music and music.filename:
            music_bytes = await music.read()
            (job_dir / "custom_bgmusic.mp3").write_bytes(music_bytes)

        listing_data: Dict[str, Any] = {
            "address": address,
            "price": price,
            "bedrooms": beds,
            "bathrooms": baths,
            "voice": voice,
        }
        if (job_dir / "custom_bgmusic.mp3").exists():
            listing_data["custom_music_path"] = str((job_dir / "custom_bgmusic.mp3").resolve())

        job_id = await create_video_job(
            listing_url="custom_upload",
            customer_email=agent_email,
            customer_name=agent_name or None,
            listing_data=listing_data,
            job_dir=job_dir,
            job_id=job_id,
        )
        return VideoJobResponse(
            id=job_id,
            status="pending",
            message="Video job created successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating custom video job: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/video-jobs/{job_id}")
@app.get("/api/video-jobs/{job_id}")
async def get_video_job(job_id: str):
    """Poll job status. Used by the dashboard's auto-refresh."""
    try:
        job = await get_video_job_status(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return _normalize_video_job_payload(job)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("/video-jobs GET error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to get job status")


@app.get("/video/history/{email}")
async def get_video_history(email: str):
    """Return all video jobs for a given email address."""
    try:
        result = (
            supabase.table("video_jobs")
            .select("*")
            .eq("customer_email", email)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"/video/history error: {e}")
        return []


@app.get("/")
async def read_root():
    return JSONResponse({"message": "416Homes API", "docs": "/docs"})


# ── Private helpers ────────────────────────────────────────────────────────────
#
# These are small utility functions used above.
# Prefixing with _ is a Python convention meaning "internal — don't call from outside".

def _parse_int(value: str | int | None, default: int = 0) -> int:
    """Safely convert '2+' or '2' or 2 or None to an int."""
    if value is None:
        return default
    try:
        return int(str(value).replace("+", "").strip())
    except (ValueError, TypeError):
        return default


def _normalise_listing(row: dict) -> dict:
    """
    Ensure every listing row has the fields ListingResponse expects.
    Supabase rows may have None for optional fields — Pydantic will reject
    those unless we supply defaults here.
    """
    return {
        "id": row.get("id", ""),
        "address": row.get("address", ""),
        "price": row.get("price") or 0,
        "bedrooms": str(row.get("bedrooms") or ""),
        "bathrooms": str(row.get("bathrooms") or ""),
        "area": str(row.get("area") or ""),
        "lat": row.get("lat"),
        "lng": row.get("lng"),
        "source": row.get("source", "unknown"),
        "url": row.get("url", ""),
        "scraped_at": str(row.get("scraped_at") or ""),
        "strategy": row.get("strategy", "unknown"),
    }


def _get_comps(neighbourhood: str, limit: int = 5) -> list:
    """Pull recent sold comps for a neighbourhood to display alongside the valuation."""
    try:
        result = (
            supabase.table("sold_comps")
            .select("address, price, bedrooms, bathrooms, sold_date")
            .ilike("neighborhood", f"%{neighbourhood}%")
            .order("sold_date", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


def _fallback_estimate(req: ValuationRequest) -> int:
    """
    Simple formula used when the ML model isn't trained yet.
    Not accurate — just keeps the endpoint functional during dev.
    """
    base = {"Toronto": 800, "Mississauga": 650}.get(req.city, 700)
    multiplier = {"Detached": 1.3, "Semi-Detached": 1.15, "Townhouse": 1.1}.get(req.property_type, 1.0)
    return int(req.sqft * base * multiplier) + req.bedrooms * 20_000 + req.bathrooms * 15_000


def _market_signal(estimated: int, list_price: int) -> str:
    """Turn estimated vs listed price into a human-readable signal."""
    ratio = list_price / estimated if estimated else 1
    if ratio < 0.90:
        return "Listed below estimated value — potential opportunity"
    if ratio > 1.10:
        return "Listed above estimated value — room to negotiate"
    return "Priced in line with estimated market value"


# ── Entrypoint ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
