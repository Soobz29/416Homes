from fastapi import FastAPI, HTTPException, BackgroundTasks, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
from dotenv import load_dotenv
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
import random
import string

from memory.store import memory_store, search_listings
from video_pipeline.pipeline import create_video_job, get_video_job_status

load_dotenv()
logger = logging.getLogger(__name__)

try:
    from supabase import create_client, Client  # type: ignore
except Exception:  # pragma: no cover - optional dependency in some envs
    create_client = None  # type: ignore[misc]
    Client = Any  # type: ignore[misc]

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase_client: Optional[Client] = None

# Use service_role key when set so the API can read/write users and alerts with RLS enabled.
_key = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY
if create_client and SUPABASE_URL and _key:
    try:
        supabase_client = create_client(SUPABASE_URL, _key)
        if not SUPABASE_SERVICE_ROLE_KEY:
            logger.warning(
                "SUPABASE_SERVICE_ROLE_KEY not set; with RLS enabled, user/alert operations may fail. "
                "Add service_role key from Supabase Dashboard → Settings → API."
            )
    except Exception as e:  # pragma: no cover
        logger.error(f"Failed to initialize Supabase client: {e}")
        supabase_client = None

app = FastAPI(
    title="416Homes API",
    description="Toronto Real Estate Intelligence Platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static + HTML pages
WEB_ROOT = Path("web")
_static_dir = WEB_ROOT / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")
else:
    logger.warning("Static directory missing (%s). Skipping /static mount.", _static_dir)


@app.get("/", response_class=HTMLResponse)
async def serve_landing():
    """Serve main landing page."""
    path = WEB_ROOT / "index.html"
    if path.exists():
        return FileResponse(str(path))
    return HTMLResponse("<h1>416Homes API</h1><p>Frontend not bundled on this deployment.</p>")


@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve buyer dashboard (requires auth in future)."""
    path = WEB_ROOT / "dashboard.html"
    if path.exists():
        return FileResponse(str(path))
    return HTMLResponse("<h1>416Homes</h1><p>Dashboard is deployed separately (Vercel).</p>")


@app.get("/video", response_class=HTMLResponse)
async def serve_video_order():
    """Serve video order page."""
    path = WEB_ROOT / "video.html"
    if path.exists():
        return FileResponse(str(path))
    return HTMLResponse("<h1>416Homes</h1><p>Video page is deployed separately.</p>")


@app.get("/agent", response_class=HTMLResponse)
async def serve_agent_dashboard():
    """Serve agent dashboard."""
    path = WEB_ROOT / "agent.html"
    if path.exists():
        return FileResponse(str(path))
    return HTMLResponse("<h1>416Homes</h1><p>Agent dashboard is deployed separately.</p>")


@app.get("/login", response_class=HTMLResponse)
async def serve_login():
    """Serve login page."""
    path = WEB_ROOT / "login.html"
    if path.exists():
        return FileResponse(str(path))
    return HTMLResponse("<h1>416Homes</h1><p>Login is handled by the frontend.</p>")

# Pydantic models
class ListingResponse(BaseModel):
    id: str
    address: str
    price: int
    bedrooms: str
    bathrooms: str
    area: str
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
    comparable_sales: Optional[List[dict]] = None

class VideoJobRequest(BaseModel):
    listing_url: str
    customer_email: str
    customer_name: Optional[str] = None

class VideoJobResponse(BaseModel):
    id: str
    status: str
    message: str

class Alert(BaseModel):
    id: str
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    min_beds: Optional[float] = None
    property_types: Optional[List[str]] = None
    neighbourhoods: Optional[List[str]] = None
    cities: Optional[List[str]] = None
    keywords: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None


class AlertCreate(BaseModel):
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    min_beds: Optional[float] = None
    property_types: Optional[List[str]] = None
    neighbourhoods: Optional[List[str]] = None
    cities: Optional[List[str]] = None
    keywords: Optional[str] = None
    is_active: bool = True


class AlertUpdate(BaseModel):
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    min_beds: Optional[float] = None
    property_types: Optional[List[str]] = None
    neighbourhoods: Optional[List[str]] = None
    cities: Optional[List[str]] = None
    keywords: Optional[str] = None
    is_active: Optional[bool] = None

from listing_agent import get_last_scan_listings
from scraper.listing_utils import is_badge_or_headline_only


# Health check
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "416Homes API",
        "version": "1.0.0"
    }


def _ensure_supabase() -> Client:
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Supabase client not configured")
    return supabase_client


def _get_or_create_user_by_email(email: str) -> Dict[str, Any]:
    email = (email or "").strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    client = _ensure_supabase()
    try:
        resp = (
            client.table("users")
            .select("*")
            .eq("email", email)
            .limit(1)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if rows:
            return rows[0]

        insert_resp = (
            client.table("users")
            .insert({"email": email})
            .execute()
        )
        data = getattr(insert_resp, "data", None) or []
        if not data:
            raise RuntimeError("Failed to insert user")
        return data[0]
    except Exception as e:
        logger.error(f"Supabase user lookup failed for {email}: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve user")


def _user_pk(user: Dict[str, Any]) -> tuple[str, Any]:
    """Return (column_name, value) for users table primary key. Supports id or uuid column."""
    uid = user.get("id")
    if uid is not None:
        return ("id", uid)
    uid = user.get("uuid")
    if uid is not None:
        return ("uuid", uid)
    raise HTTPException(status_code=500, detail="User record missing id/uuid")


def _get_user_id_from_header(x_user_email: str | None) -> str:
    if not x_user_email:
        raise HTTPException(status_code=401, detail="Missing x-user-email header")
    user = _get_or_create_user_by_email(x_user_email)
    _, user_id = _user_pk(user)
    return str(user_id)


def _generate_link_code(length: int = 6) -> str:
    """Generate a short human-typed code like TG-A1B2C3 (6 chars, 30 min expiry)."""
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(random.choice(chars) for _ in range(length))
    return f"TG-{suffix}"

# Listings endpoints
@app.get("/api/listings")
async def get_listings(
    city: str = "GTA",
    limit: int = 20,
    offset: int = 0,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    bedrooms: Optional[str] = None,
    bathrooms: Optional[str] = None,
    property_types: Optional[str] = None,
):
    """
    Get property listings with optional filters.

    Preference order:
    1. Supabase `listings` table (shared across hosts and Telegram/API).
    2. Local last-scan JSON snapshot if Supabase is empty/unavailable.
    """
    try:
        # Treat GTA / empty as no city filter (All GTA).
        city_filter = None if (not city or city.lower() == "gta") else city.strip()
        # When dashboard selects "Toronto", include boroughs stored as separate cities.
        TORONTO_BOROUGHS = ("Toronto", "Downtown", "North York", "Scarborough", "Etobicoke")
        if city_filter and city_filter.lower() == "toronto":
            cities_filter: Optional[List[str]] = list(TORONTO_BOROUGHS)
        else:
            cities_filter = None

        rows: list[dict] = []
        scan_at: Optional[str] = None

        # 1) Prefer Supabase `listings` table so API works even when the
        #    last-scan JSON file is missing on this host.
        if supabase_client:
            try:
                min_beds = float(bedrooms) if bedrooms and str(bedrooms).strip() else None
                min_baths = float(bathrooms) if bathrooms and str(bathrooms).strip() else None
                rows = await memory_store.get_listings(
                    city=city_filter if not cities_filter else None,
                    cities=cities_filter,
                    limit=1000,
                    min_price=min_price,
                    max_price=max_price,
                    min_beds=min_beds,
                    min_baths=min_baths,
                )
                if rows:
                    scan_at = (rows[0].get("scraped_at") or "").strip() or None
                    logger.info(
                        "Listings API using Supabase source: %d rows (city=%s)",
                        len(rows),
                        city_filter or "ALL",
                    )
            except Exception as e:
                logger.warning("Supabase listings query failed: %s", e)

        # 2) Fallback to last-scan JSON snapshot if Supabase had no usable rows.
        if not rows:
            scan_at, total, all_listings = get_last_scan_listings(
                limit=1000, offset=0, city=city_filter, region=None
            )
            rows = all_listings or []
            if rows:
                logger.info(
                    "Listings API using last-scan JSON source: %d rows (city=%s)",
                    len(rows),
                    city_filter or "ALL",
                )

        def _num(v) -> Optional[float]:
            try:
                if v is None:
                    return None
                if isinstance(v, (int, float)):
                    return float(v)
                s = "".join(ch for ch in str(v) if ch.isdigit() or ch == ".")
                return float(s) if s else None
            except Exception:
                return None

        # Apply filters in-memory
        filtered = []
        for r in rows:
            p = _num(r.get("price"))
            if min_price is not None and (p is None or p < min_price):
                continue
            if max_price is not None and (p is None or p > max_price):
                continue

            b = _num(r.get("bedrooms"))
            if bedrooms is not None and bedrooms != "" and b is not None and b < float(bedrooms):
                continue

            ba = _num(r.get("bathrooms"))
            if bathrooms is not None and bathrooms != "" and ba is not None and ba < float(bathrooms):
                continue

            if property_types:
                types_set = {t.strip().lower() for t in property_types.split(",") if t.strip()}
                if types_set:
                    row_type = (r.get("property_type") or r.get("strategy") or "").lower()
                    row_type = row_type.replace("-", " ").replace("_", " ")
                    if not any(t in row_type or row_type in t for t in types_set):
                        continue

            filtered.append(r)

        total = len(filtered)
        limited = filtered[offset : offset + limit]
        normalised = [_normalise_listing(r) for r in limited]
        return {
            "listings": normalised,
            "total": total,
            "limit": limit,
            "offset": offset,
            "scan_time": scan_at,
        }

    except Exception as e:
        logger.error(f"Error fetching listings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch listings")


@app.get("/api/alerts", response_model=List[Alert])
async def get_alerts(x_user_email: Optional[str] = Header(None, alias="x-user-email")):
    """
    List alerts for the current user. The web app should pass x-user-email header.
    """
    user_id = _get_user_id_from_header(x_user_email)
    client = _ensure_supabase()
    try:
        resp = (
            client.table("alerts")
            .select(
                "id,min_price,max_price,min_beds,property_types,neighbourhoods,cities,keywords,is_active,created_at"
            )
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        return [
            Alert(
                id=str(r.get("id")),
                min_price=r.get("min_price"),
                max_price=r.get("max_price"),
                min_beds=r.get("min_beds"),
                property_types=r.get("property_types"),
                neighbourhoods=r.get("neighbourhoods"),
                cities=r.get("cities"),
                keywords=r.get("keywords"),
                is_active=bool(r.get("is_active", True)),
                created_at=str(r.get("created_at")) if r.get("created_at") else None,
            )
            for r in rows
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alerts")


@app.get("/api/me")
async def get_me(x_user_email: Optional[str] = Header(None, alias="x-user-email")):
    """
    Return current user profile (id, email, telegram_chat_id) for dashboard.
    Used to show "Connected!" when Telegram is linked and for "Check status" button.
    """
    if not x_user_email:
        raise HTTPException(status_code=401, detail="Missing x-user-email header")
    user = _get_or_create_user_by_email(x_user_email)
    _, uid = _user_pk(user)
    return {
        "id": str(uid),
        "email": user.get("email"),
        "telegram_chat_id": user.get("telegram_chat_id"),
        "telegram_username": user.get("telegram_username"),
    }


@app.post("/api/link-code")
async def create_link_code(x_user_email: Optional[str] = Header(None, alias="x-user-email")):
    """
    Generate a short one-time link code for connecting a Telegram chat to this user.
    """
    email = (x_user_email or "").strip()
    if not email:
        raise HTTPException(status_code=401, detail="Missing x-user-email header")
    user = _get_or_create_user_by_email(email)
    client = _ensure_supabase()
    code = _generate_link_code()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    # Merge into existing preferences JSON, overwriting link_code/link_expires_at.
    prefs = user.get("preferences") or {}
    if not isinstance(prefs, dict):
        prefs = {}
    prefs.update({"link_code": code, "link_expires_at": expires_at})

    pk_col, pk_val = _user_pk(user)
    try:
        client.table("users").update({"preferences": prefs}).eq(pk_col, pk_val).execute()
        logger.info("Link code generated for user %s (%s=%s), code=%s", email, pk_col, pk_val, code)
    except Exception as e:
        logger.exception("Error saving link code for user %s: %s", pk_val, e)
        raise HTTPException(status_code=500, detail="Failed to generate link code")

    return {"code": code, "expires_at": expires_at}


@app.post("/api/alerts", response_model=Alert)
async def create_alert(
    payload: AlertCreate,
    x_user_email: Optional[str] = Header(None, alias="x-user-email"),
):
    """
    Create a new alert for the current user.
    """
    user_id = _get_user_id_from_header(x_user_email)
    client = _ensure_supabase()
    data = payload.dict(exclude_unset=True)
    data["user_id"] = user_id
    try:
        resp = client.table("alerts").insert(data).execute()
        rows = getattr(resp, "data", None) or []
        if not rows:
            raise RuntimeError("Insert returned no rows")
        r = rows[0]
        return Alert(
            id=str(r.get("id")),
            min_price=r.get("min_price"),
            max_price=r.get("max_price"),
            min_beds=r.get("min_beds"),
            property_types=r.get("property_types"),
            neighbourhoods=r.get("neighbourhoods"),
            cities=r.get("cities"),
            keywords=r.get("keywords"),
            is_active=bool(r.get("is_active", True)),
            created_at=str(r.get("created_at")) if r.get("created_at") else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to create alert")


@app.patch("/api/alerts/{alert_id}", response_model=Alert)
async def update_alert(
    alert_id: str,
    payload: AlertUpdate,
    x_user_email: Optional[str] = Header(None, alias="x-user-email"),
):
    """
    Update an existing alert owned by the current user.
    """
    user_id = _get_user_id_from_header(x_user_email)
    client = _ensure_supabase()
    data = payload.dict(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    try:
        resp = (
            client.table("alerts")
            .update(data)
            .eq("id", alert_id)
            .eq("user_id", user_id)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if not rows:
            raise HTTPException(status_code=404, detail="Alert not found")
        r = rows[0]
        return Alert(
            id=str(r.get("id")),
            min_price=r.get("min_price"),
            max_price=r.get("max_price"),
            min_beds=r.get("min_beds"),
            property_types=r.get("property_types"),
            neighbourhoods=r.get("neighbourhoods"),
            cities=r.get("cities"),
            keywords=r.get("keywords"),
            is_active=bool(r.get("is_active", True)),
            created_at=str(r.get("created_at")) if r.get("created_at") else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update alert")


@app.delete("/api/alerts/{alert_id}", status_code=204)
async def delete_alert(
    alert_id: str,
    x_user_email: Optional[str] = Header(None, alias="x-user-email"),
):
    """
    Delete an alert owned by the current user.
    """
    user_id = _get_user_id_from_header(x_user_email)
    client = _ensure_supabase()
    try:
        resp = (
            client.table("alerts")
            .delete()
            .eq("id", alert_id)
            .eq("user_id", user_id)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if not rows:
            raise HTTPException(status_code=404, detail="Alert not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete alert")
    return None


@app.get("/api/listings/search")
async def search_listings_endpoint(q: str, limit: int = 10):
    """Search listings using vector similarity"""
    
    try:
        results = await search_listings(q, limit)
        return results
    except Exception as e:
        logger.error(f"Error searching listings: {e}")
        # Return mock results for demo
        return []

# Valuation endpoint (minimal Railway deployment)
@app.post("/api/valuate")
async def valuate_property(data: dict):
    """Temporary mock valuation - full model disabled for Railway deployment"""
    sqft = 1500
    try:
        sqft = int(data.get("sqft", sqft) or sqft)
    except Exception:
        sqft = 1500
    return {
        "estimated_value": sqft * 600,  # Simple $600/sqft estimate
        "confidence": 0.7,
        "market_analysis": "Full valuation model temporarily disabled. Using simple price estimation.",
        "note": "Upgrade to full LightGBM model coming soon",
    }

# Video job endpoints
@app.post("/api/video-jobs", response_model=VideoJobResponse)
async def create_video_job_endpoint(request: VideoJobRequest):
    """Create a new video job"""
    
    try:
        job_id = await create_video_job(
            listing_url=request.listing_url,
            customer_email=request.customer_email,
            customer_name=request.customer_name
        )
        
        if job_id:
            return VideoJobResponse(
                id=job_id,
                status="pending",
                message="Video job created successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to create video job")
            
    except Exception as e:
        logger.error(f"Error creating video job: {e}")
        # Return demo job for testing
        return VideoJobResponse(
            id="demo-job-123",
            status="pending",
            message="Demo video job created successfully"
        )

@app.get("/api/video-jobs/{job_id}")
async def get_video_job(job_id: str):
    """Get video job status"""
    
    try:
        job_status = await get_video_job_status(job_id)
        
        if job_status:
            return job_status
        else:
            # Return demo job for testing
            return {
                "id": job_id,
                "status": "completed",
                "progress": 100,
                "video_url": "https://storage.googleapis.com/416homes-videos/demo-video.mp4",
                "created_at": "2024-03-03T22:00:00Z",
                "updated_at": "2024-03-03T22:05:00Z"
            }
            
    except Exception as e:
        logger.error(f"Error getting video job: {e}")
        raise HTTPException(status_code=500, detail="Failed to get video job status")

# API root helper
@app.get("/api")
async def api_root():
    return JSONResponse(content={"message": "416Homes API is running", "dashboard": "/dashboard"})

def _normalise_listing(row: dict) -> dict:
    # Normalise area / sqft; some sources may store complex objects or zeros.
    raw_area = row.get("sqft", row.get("area"))
    if isinstance(raw_area, dict):
        raw_area = None
    if isinstance(raw_area, (int, float)) and raw_area <= 0:
        raw_area = None

    addr = (row.get("address") or "").strip()
    if is_badge_or_headline_only(addr):
        addr = "Address not available"

    return {
        "id":          row.get("id", ""),
        "address":     addr,
        "price":       row.get("price") or 0,
        "bedrooms":    str(row.get("bedrooms") or ""),
        "bathrooms":   str(row.get("bathrooms") or ""),
        # Dashboard expects 'area'; source data may use 'sqft' (Supabase) or 'area' (last_scan JSON).
        "area":        ("" if raw_area is None else str(raw_area)),
        "city":        str(row.get("city") or ""),
        "lat":         row.get("lat"),
        "lng":         row.get("lng"),
        "source":      row.get("source", "unknown"),
        "url":         row.get("url", ""),
        "scraped_at":  str(row.get("scraped_at") or ""),
        "strategy":    row.get("strategy", "unknown"),
    }

def _get_comps(neighbourhood: str, limit: int = 5) -> list:
    try:
        from supabase import create_client
        import os
        client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        result = (
            client.table("sold_comps")
            .select("address, sold_price, list_price, bedrooms, bathrooms, sold_date")
            .ilike("neighbourhood", f"%{neighbourhood}%")
            .order("sold_date", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception:
        return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
