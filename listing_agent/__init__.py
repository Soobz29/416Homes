"""
Listing Agent — 24/7 automated Canadian real estate listing monitor.

Zentro-style agent that continuously scans Canadian real estate sites
(Zoocasa, Condos.ca) and alerts on new listings matching criteria.

Features:
  - Configurable search criteria (price, beds, baths, neighborhoods, type)
  - Scheduled scanning every N minutes
  - New listing detection via content hashing
  - Alert via in-memory queue (expandable to email/webhook)
  - Auto-trigger video generation for premium listings
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from dotenv import load_dotenv
from listing_agent.activity_log import log_activity

# Import our new components
from listing_agent.memory import agent_memory
from listing_agent.skills import load_skills
# from telegram_bot import bot as telegram_bot (Removed to prevent circular import)

load_dotenv()
logger = logging.getLogger(__name__)

# White-label Configuration
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agent_config.json")
def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

AGENT_CONFIG = load_config()
AGENT_NAME = AGENT_CONFIG.get("agent_name", "AI Agent")
BROKERAGE_NAME = AGENT_CONFIG.get("brokerage_name", "416Homes")

# ── Default search criteria ────────────────────────────────────────────────
DEFAULT_CRITERIA = {
    "min_price": 0,
    "max_price": 5_000_000,
    "min_beds": 0,
    "max_beds": 10,
    "min_baths": 0,
    "max_baths": 10,
    "property_types": ["Condo", "House", "Townhouse", "Semi-Detached"],
    "neighborhoods": [],  # empty = all
    # empty cities list = all GTA cities; Telegram + API can still filter by city.
    "cities": [],
    "sources": ["browser_use_realtor", "zoocasa", "condos_ca"],
}

# ── Alert storage ──────────────────────────────────────────────────────────
MAX_ALERTS = 200
SEEN_LISTINGS_FILE = Path("listing_agent/seen_listings.json")
SEEN_HASHES_FILE   = Path("listing_agent/seen_hashes.json")
LAST_SCAN_LISTINGS_FILE = Path("listing_agent/last_scan_listings.json")

LISTINGS_PAGE_SIZE = 10
MAX_PERSISTED_LISTINGS = 500

DETAIL_FETCH_CONCURRENCY = int(os.getenv("DETAIL_FETCH_CONCURRENCY", "5"))
MAX_DETAIL_FETCH_PER_SOURCE = int(os.getenv("MAX_DETAIL_FETCH_PER_SOURCE", "50"))


def _normalize_city(address_or_region: str) -> str:
    s = (address_or_region or "").lower()
    # Treat Toronto boroughs as "cities" for filtering UX.
    # (Common user expectation in GTA real estate search.)
    if "north york" in s:
        return "North York"
    if "scarborough" in s:
        return "Scarborough"
    if "etobicoke" in s:
        return "Etobicoke"
    if "downtown" in s or "waterfront" in s or "financial district" in s:
        return "Downtown"
    if "mississauga" in s:
        return "Mississauga"
    if "toronto" in s:
        return "Toronto"
    # Common GTA municipalities
    if "brampton" in s:
        return "Brampton"
    if "vaughan" in s or "woodbridge" in s or "maple" in s:
        return "Vaughan"
    if "markham" in s or "unionville" in s:
        return "Markham"
    if "richmond hill" in s:
        return "Richmond Hill"
    if "oakville" in s:
        return "Oakville"
    if "burlington" in s:
        return "Burlington"
    if "ajax" in s:
        return "Ajax"
    if "pickering" in s:
        return "Pickering"
    if "whitby" in s:
        return "Whitby"
    if "oshawa" in s:
        return "Oshawa"
    if "milton" in s:
        return "Milton"
    return "GTA"


def _normalize_region(address: str) -> str:
    s = (address or "").lower()
    if "downtown" in s or "waterfront" in s or "financial district" in s or "king" in s:
        return "Downtown"
    if "scarborough" in s or "m1" in s:
        return "Scarborough"
    if "etobicoke" in s or "m8" in s or "m9" in s:
        return "Etobicoke"
    if "north york" in s or "willowdale" in s:
        return "North York"
    if "mississauga" in s:
        return "Mississauga"
    if "brampton" in s:
        return "Brampton"
    if "vaughan" in s or "woodbridge" in s or "maple" in s:
        return "Vaughan"
    if "markham" in s or "unionville" in s:
        return "Markham"
    if "richmond hill" in s:
        return "Richmond Hill"
    if "oakville" in s:
        return "Oakville"
    if "burlington" in s:
        return "Burlington"
    if "ajax" in s or "pickering" in s:
        return "Ajax & Pickering"
    return "GTA"


def _is_valid_price(price: Any) -> bool:
    try:
        if price is None:
            return False
        if isinstance(price, (int, float)):
            return int(price) > 0
        # strings like "$699,000" or "699000"
        digits = re.sub(r"[^\d]", "", str(price))
        return int(digits) > 0 if digits else False
    except Exception:
        return False


async def _enrich_listing_details(listing: Dict[str, Any]) -> Dict[str, Any] | None:
    """
    Strict mode: ensure address + price are present.
    Returns enriched listing or None if still incomplete.
    """
    url = listing.get("url") or ""
    source = (listing.get("source") or "").lower()

    # If missing, attempt per-source detail fetch.
    if (not listing.get("address")) or (str(listing.get("address", "")).lower() in {"unknown", "unknown address"}):
        listing["address"] = ""

    if (not _is_valid_price(listing.get("price"))) and url:
        # Realtor.ca detail fetch is already implemented.
        if "realtor" in url or source == "realtor_ca":
            try:
                from scraper.realtor_ca import scrape_listing_details

                d = await scrape_listing_details(url)
                if d:
                    listing["address"] = d.get("address") or listing.get("address")
                    listing["price"] = d.get("price") or listing.get("price")
            except Exception:
                pass
        # Condos.ca: best-effort fetch page and extract price/address from HTML.
        elif "condos.ca" in url or source == "condos_ca":
            try:
                from scrapling.fetchers import StealthyFetcher

                page = await StealthyFetcher.async_fetch(url, headless=True, timeout=45000, wait=4000)
                html = page.html_content or ""
                # address: try title meta / h1
                h1 = page.css_first("h1")
                if h1 and (h1.text or "").strip():
                    listing["address"] = (h1.text or "").strip()
                # price: look for $... in text
                m = re.search(r"\$[\s]*([\d,]+)", html)
                if m:
                    listing["price"] = int(m.group(1).replace(",", ""))
            except Exception:
                pass

    # Normalize city/region after enrichment
    listing["city"] = listing.get("city") or _normalize_city(listing.get("address") or listing.get("region") or "")
    listing["region"] = listing.get("region") or _normalize_region(listing.get("address") or "")

    if (not listing.get("address")) or (str(listing.get("address", "")).lower() in {"unknown", "unknown address"}):
        return None
    if not _is_valid_price(listing.get("price")):
        return None
    return listing


async def enrich_listings_strict(listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enrich and filter listings so Telegram never shows UNKNOWN.
    Caps detail fetch volume per source.
    """
    if not listings:
        return []

    # Normalize initial city/region if missing
    for L in listings:
        L["city"] = L.get("city") or _normalize_city(L.get("address") or L.get("region") or "")
        L["region"] = L.get("region") or _normalize_region(L.get("address") or "")

    # Choose candidates needing enrichment (missing/invalid price or unknown address)
    by_source: Dict[str, List[Dict[str, Any]]] = {}
    for L in listings:
        src = (L.get("source") or "unknown").lower()
        by_source.setdefault(src, []).append(L)

    sem = asyncio.Semaphore(DETAIL_FETCH_CONCURRENCY)

    async def _work(L: Dict[str, Any]) -> Dict[str, Any] | None:
        async with sem:
            return await _enrich_listing_details(L)

    tasks: List[asyncio.Task] = []
    for src, items in by_source.items():
        # Only enrich up to cap per source
        need = []
        for L in items:
            addr = str(L.get("address") or "").strip().lower()
            if (not addr) or addr == "unknown" or (not _is_valid_price(L.get("price"))):
                need.append(L)
        for L in need[:MAX_DETAIL_FETCH_PER_SOURCE]:
            tasks.append(asyncio.create_task(_work(L)))

    enriched_map: Dict[int, Dict[str, Any]] = {}
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, dict):
                enriched_map[id(r)] = r

    # Final filter: only keep complete listings
    out: List[Dict[str, Any]] = []
    for L in listings:
        if (not L.get("address")) or (str(L.get("address", "")).lower() in {"unknown", "unknown address"}):
            continue
        if not _is_valid_price(L.get("price")):
            continue
        out.append(L)
    return out


def _persist_last_scan_listings(listings: List[Dict[str, Any]]) -> None:
    """Write last scan results to JSON for /listings command."""
    try:
        capped = listings[:MAX_PERSISTED_LISTINGS] if listings else []
        data = {
            "scan_at": datetime.utcnow().isoformat(),
            "total": len(listings),
            "listings": capped,
        }
        LAST_SCAN_LISTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LAST_SCAN_LISTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=0, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Failed to persist last scan listings: {e}")


def get_last_scan_listings(
    limit: int = 10,
    offset: int = 0,
    city: str | None = None,
    region: str | None = None,
) -> tuple:
    """
    Read last scan from disk. Returns (scan_at, total_filtered, listings_slice).
    If missing/invalid: (None, 0, []).
    """
    try:
        if not LAST_SCAN_LISTINGS_FILE.exists():
            return (None, 0, [])
        with open(LAST_SCAN_LISTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        all_listings = data.get("listings", []) or []

        if city:
            c = city.strip().lower()
            all_listings = [L for L in all_listings if str(L.get("city", "")).lower() == c]
        if region:
            r = region.strip().lower()
            all_listings = [L for L in all_listings if r in str(L.get("region", "")).lower()]

        total = len(all_listings)
        slice_end = min(offset + limit, total)
        slice_list = all_listings[offset:slice_end]
        scan_at = data.get("scan_at")
        return (scan_at, total, slice_list)
    except Exception as e:
        logger.warning(f"Failed to read last scan listings: {e}")
        return (None, 0, [])


class ListingAlert:
    """A new listing alert."""

    def __init__(self, listing: Dict[str, Any], source: str):
        self.listing = listing
        self.source = source
        self.timestamp = datetime.utcnow().isoformat()
        self.id = hashlib.md5(
            f"{listing.get('address','')}{listing.get('price','')}{source}".encode()
        ).hexdigest()[:12]
        self.video_job_id: Optional[str] = None
        self.buyer_email: Optional[str] = None
        self.seller_email: Optional[str] = None
        self.seen = False

    def to_dict(self):
        return {
            "id": self.id,
            "listing": self.listing,
            "source": self.source,
            "timestamp": self.timestamp,
            "video_job_id": self.video_job_id,
            "buyer_email": self.buyer_email,
            "seller_email": self.seller_email,
            "seen": self.seen,
        }


class ListingAgent:
    """
    24/7 listing monitor that scans Canadian real estate sites
    and detects new listings matching configured criteria.
    """

    def __init__(self):
        self.criteria: Dict[str, Any] = dict(DEFAULT_CRITERIA)
        self.running = False
        self.scan_interval_minutes = 30
        # seen_hashes: hash → ISO timestamp (persisted so restarts don't reset it)
        self.seen_hashes: Dict[str, str] = self._load_seen_hashes()
        self.alerts: List[ListingAlert] = []
        self.last_scan: Optional[str] = None
        self.scan_count = 0
        self.total_found = 0
        self.auto_video = False  # auto-trigger video for premium listings
        self.auto_video_min_price = 1_000_000
        self._task: Optional[asyncio.Task] = None
        self.skills = load_skills()
        self.seen_listings: Dict[str, str] = self._load_seen_listings()

    # ── Public API ──────────────────────────────────────────────────────────

    def start(self, criteria: Optional[Dict] = None, interval_minutes: int = 30,
              auto_video: bool = False, auto_video_min_price: int = 1_000_000):
        """Start the agent loop."""
        if self.running:
            return {"status": "already_running", "scan_interval": self.scan_interval_minutes}

        if criteria:
            self.criteria.update(criteria)

        self.scan_interval_minutes = interval_minutes
        self.auto_video = auto_video
        self.auto_video_min_price = auto_video_min_price
        self.running = True
        self._task = asyncio.ensure_future(self._scan_loop())

        logger.info(f"🤖 {AGENT_NAME} started — scanning every {interval_minutes} min")
        log_activity("SYSTEM", f"{AGENT_NAME} started — scanning every {interval_minutes} min")
        return {
            "status": "started",
            "scan_interval": interval_minutes,
            "criteria": self.criteria,
            "auto_video": auto_video,
        }

    def stop(self):
        """Stop the agent loop."""
        self.running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("🛑 Listing agent stopped")
        log_activity("SYSTEM", "Listing agent stopped")
        return {"status": "stopped", "total_scans": self.scan_count, "total_alerts": len(self.alerts)}

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            "running": self.running,
            "scan_interval_minutes": self.scan_interval_minutes,
            "criteria": self.criteria,
            "last_scan": self.last_scan,
            "scan_count": self.scan_count,
            "total_listings_found": self.total_found,
            "active_alerts": len([a for a in self.alerts if not a.seen]),
            "total_alerts": len(self.alerts),
            "auto_video": self.auto_video,
            "auto_video_min_price": self.auto_video_min_price,
            "known_listings": len(self.seen_hashes),  # persisted hash count
        }

    def get_alerts(self, unseen_only: bool = False, limit: int = 50) -> List[Dict]:
        """Get listing alerts."""
        alerts = self.alerts
        if unseen_only:
            alerts = [a for a in alerts if not a.seen]
        return [a.to_dict() for a in alerts[-limit:]]

    def mark_seen(self, alert_id: str):
        """Mark an alert as seen."""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.seen = True
                return True
        return False

    def update_criteria(self, criteria: Dict[str, Any]):
        """Update search criteria without restarting."""
        self.criteria.update(criteria)
        logger.info(f"🔄 Agent criteria updated: {criteria}")
        return self.criteria

    def refresh_skills(self):
        """Reload skills from disk."""
        self.skills = load_skills()
        logger.info(f"Loaded {len(self.skills)} matching skills.")

    # ── Internal scan loop ──────────────────────────────────────────────────

    async def _scan_loop(self):
        """Main scanning loop — runs until stopped."""
        logger.info("🔍 Agent scan loop started")

        # Do an immediate first scan
        await self._run_scan()

        while self.running:
            try:
                # Wait for the interval
                await asyncio.sleep(self.scan_interval_minutes * 60)
                if not self.running:
                    break
                await self._run_scan()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Agent scan error: {e}")
                await asyncio.sleep(60)  # retry after 1 min

    async def _run_scan(self):
        """Execute one scan cycle across all configured sources."""
        try:
            self.scan_count += 1
            self.last_scan = datetime.utcnow().isoformat()
            logger.info(f"🔍 Agent scan #{self.scan_count} starting...")

            new_listings = []

            try:
                from scraper.aggregator import scrape_all_sources
                listings = await scrape_all_sources()
                
                # Update total_scans counter in memory
                current = agent_memory.recall("total_scans") or 0
                agent_memory.store("total_scans", current + 1)
                from listing_agent.activity_log import log_activity
                log_activity("SCAN", f"Scan #{current + 1} complete: {len(listings)} listings")

                # Strict enrichment so Telegram never shows UNKNOWN.
                listings = await enrich_listings_strict(listings)

                # Persist for /listings command (cap at 500 to keep file small)
                _persist_last_scan_listings(listings)

                # Push same listings to Supabase so dashboard + Telegram show latest (like local)
                try:
                    from memory.store import embed_and_store_listings
                    regular = [L for L in listings if L.get("source") != "housesigma" and "sold_price" not in L]
                    if regular:
                        stored = await embed_and_store_listings(regular)
                        log_activity("SCAN", f"Pushed {stored}/{len(regular)} listings to Supabase")
                except Exception as e:
                    logger.warning(f"Failed to push listings to Supabase: {e}")
                    log_activity("ERROR", f"Supabase push failed: {e}")

                for listing in listings:
                    if self._matches_criteria(listing) and self._is_new(listing, listing.get("source", "unknown")):
                        new_listings.append((listing, listing.get("source", "unknown")))
            except Exception as e:
                logger.error(f"Agent aggregator scan failed: {e}")
                from listing_agent.activity_log import log_activity
                log_activity("ERROR", f"aggregator.scrape_all_sources failed: {e}")

            # Create alerts for new listings
            self._purge_old_seen_listings()
            self._purge_old_seen_hashes()
            
            for listing, source in new_listings:
                listing_id = listing.get("id")
                if listing_id in self.seen_listings:
                    logger.info(f" [SKIP] {listing_id} already alerted within 24hrs")
                    from listing_agent.activity_log import log_activity
                    log_activity("SKIP", f"{listing_id} already alerted within 24hrs")
                    continue
                
                alert = ListingAlert(listing, source)
                # Mark as seen
                self.seen_listings[listing_id] = datetime.utcnow().isoformat()
                self._save_seen_listings()
                
                # Score against buyers
                buyers = agent_memory.recall("buyers", [])
                best_score = 0
                best_buyer = None
                
                if buyers:
                    scores = await self._score_listing(listing, buyers)
                    if scores:
                        # Find highest score
                        best_buyer_name = max(scores, key=scores.get)
                        best_score = scores[best_buyer_name]
                        best_buyer = next((b for b in buyers if b['name'] == best_buyer_name), None)
                        from listing_agent.activity_log import log_activity
                        log_activity("MATCH", f"{alert.id} scored {best_score}/100 for buyer: {best_buyer_name}")

                # Draft personalized outreach emails
                try:
                    from scraper.email_service import draft_alert_emails
                    emails = await draft_alert_emails(listing)
                    if emails:
                        alert.buyer_email = emails.get("buyer_email")
                        alert.seller_email = emails.get("seller_email")
                except Exception as e:
                    logger.warning(f"Failed to draft notification emails: {e}")
                    
                self.alerts.append(alert)
                self.total_found += 1
                agent_memory.log_event("alert_fired", {
                    "alert_id": alert.id,
                    "address": listing.get('address'),
                    "price": listing.get('price'),
                    "region": listing.get('region', 'Unknown'),
                    "source": source,
                    "score": best_score,
                    "buyer": best_buyer['name'] if best_buyer else None
                })
                
                # Telegram Notifications
                if best_score >= 75:
                    await self._send_match_notification(listing, alert, best_buyer, best_score)

                logger.info(
                    f"🏠 NEW listing: {listing.get('address', '?')} — "
                    f"${listing.get('price', '?')} ({source})"
                )

                # Auto-trigger video for premium listings
                if self.auto_video:
                    price = self._parse_price(listing.get("price", "0"))
                    if price >= self.auto_video_min_price:
                        logger.info(f"🎬 Auto-video triggered for premium listing: {listing.get('address')}")
                        alert.video_job_id = f"auto_{alert.id}"
                        agent_memory.log_event("video_generated", {
                            "alert_id": alert.id,
                            "address": listing.get('address'),
                            "job_id": alert.video_job_id
                        })

            # Trim old alerts
            if len(self.alerts) > MAX_ALERTS:
                self.alerts = self.alerts[-MAX_ALERTS:]

            logger.info(
                f"✅ Scan #{self.scan_count} complete: "
                f"{len(new_listings)} new listings found"
            )
            agent_memory.log_event("listing_scanned", {
                "scan_number": self.scan_count,
                "new_count": len(new_listings)
            })
        except Exception as e:
            from listing_agent.activity_log import log_activity
            log_activity("ERROR", f"_run_scan crashed: {type(e).__name__}: {e}")
            import traceback
            log_activity("ERROR", traceback.format_exc()[:500])
            return  # Don't crash — just skip this cycle

    async def _scrape_source(self, source: str) -> List[Dict[str, Any]]:
        """DEPRECATED: Use aggregator.scrape_all_sources instead."""
        from scraper.aggregator import scrape_all_sources
        # This is a fallback wrapper if individual sources are still called somewhere
        results = await scrape_all_sources()
        return [l for l in results if l.get("source") == source]

    def _load_seen_listings(self) -> Dict[str, str]:
        """Load seen listings from disk."""
        if SEEN_LISTINGS_FILE.exists():
            try:
                with open(SEEN_LISTINGS_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading seen listings: {e}")
        return {}

    def _save_seen_listings(self):
        """Save seen listings to disk."""
        try:
            with open(SEEN_LISTINGS_FILE, 'w') as f:
                json.dump(self.seen_listings, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving seen listings: {e}")

    def _purge_old_seen_listings(self):
        """Purge seen listings older than 24 hours."""
        now = datetime.utcnow()
        to_delete = []
        for lid, ts_str in self.seen_listings.items():
            try:
                ts = datetime.fromisoformat(ts_str)
                if now - ts > timedelta(hours=24):
                    to_delete.append(lid)
            except:
                to_delete.append(lid)
        
        for lid in to_delete:
            del self.seen_listings[lid]
        
        if to_delete:
            self._save_seen_listings()
            logger.info(f"🧹 Purged {len(to_delete)} old entries from seen_listings.json")

    # ── Filtering ───────────────────────────────────────────────────────────

    def _matches_criteria(self, listing: Dict[str, Any]) -> bool:
        """Check if a listing matches the configured criteria."""
        price = self._parse_price(listing.get("price", "0"))
        beds = self._parse_int(listing.get("bedrooms") or listing.get("beds", "0"))
        baths = self._parse_int(listing.get("bathrooms") or listing.get("baths", "0"))
        ptype = listing.get("property_type", "Unknown")

        # Price filter
        if price < self.criteria.get("min_price", 0):
            return False
        if price > self.criteria.get("max_price", 999_999_999):
            return False

        # Bedroom filter
        if beds < self.criteria.get("min_beds", 0):
            return False
        if beds > self.criteria.get("max_beds", 99):
            return False

        # Bathroom filter
        if baths < self.criteria.get("min_baths", 0):
            return False
        if baths > self.criteria.get("max_baths", 99):
            return False

        # Property type filter
        allowed_types = self.criteria.get("property_types", [])
        if allowed_types and ptype and ptype != "Unknown":
            # Case-insensitive match
            allowed_lower = [t.lower() for t in allowed_types]
            if ptype.lower() not in allowed_lower:
                return False

        # Region / Neighborhood filter
        neighborhoods = self.criteria.get("neighborhoods", [])
        if neighborhoods:
            addr = listing.get("address", "").lower()
            region = listing.get("region", "").lower()
            # Check if any neighborhood name is in address or matches the region
            if not any(n.lower() in addr or n.lower() == region for n in neighborhoods):
                return False

        # Custom Skills
        for skill_func in self.skills:
            try:
                if not skill_func(listing):
                    return False
            except Exception as e:
                logger.error(f"Error executing skill {skill_func.__name__}: {e}")

        return True

    async def _score_listing(self, listing: Dict[str, Any], buyers: List[Dict[str, Any]]) -> Dict[str, int]:
        """Use Gemini to score a listing against multiple buyer profiles."""
        try:
            from google import genai
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key: return {}

            client = genai.Client(api_key=api_key)
            model_id = "gemini-2.5-flash"

            prompt = f"""
            Score this real estate listing against the following buyer profiles.
            Return ONLY a JSON object mapping buyer names to scores (0-100).
            
            Listing:
            {json.dumps(listing, indent=2)}
            
            Buyers:
            {json.dumps(buyers, indent=2)}
            
            A score of 90+ is 'Urgent Match', 75-89 is 'High Match'.
            Consider budget, bedrooms, and neighbourhood.
            """
            
            try:
                response = await asyncio.to_thread(client.models.generate_content, model=model_id, contents=prompt)
                text = response.text.strip()
                if text.startswith("```"):
                    text = re.sub(r'^```(?:json)?\s*', '', text)
                    text = re.sub(r'\s*```$', '', text)
                return json.loads(text)
            except Exception as gemini_err:
                log_activity("ERROR", f"gemini_call failed in _score_listing: {gemini_err}")
                return {}
        except Exception as e:
            logger.error(f"Error scoring listing: {e}")
            log_activity("ERROR", f"_score_listing failed: {e}")
            return {}

    async def _send_match_notification(self, listing: Dict[str, Any], alert: ListingAlert, buyer: Optional[Dict[str, Any]], score: int):
        """Send match notification to Telegram."""
        buyer_name = buyer['name'] if buyer else "General"
        address = listing.get('address', 'Unknown')
        price = listing.get('price', '?')
        region = listing.get('region', '')
        
        display_address = f"{region} — {address}" if region else address
        
        from telegram_bot import send_notification

        if score >= 90:
            # URGENT match
            msg = (
                "🚨 <b>URGENT MATCH (Score: {score})</b>\n"
                f"• <b>Buyer:</b> {buyer_name}\n"
                f"• <b>Address:</b> {address}\n"
                f"• <b>Price:</b> {price}\n"
                f"• <b>ID:</b> <code>{alert.id}</code>\n\n"
                f"{listing.get('description', '')[:200]}..."
            ).format(score=score)
            # Find photo if available
            photo = listing.get('photos', [None])[0] if 'photos' in listing else None
            await send_notification(msg, photo_url=photo)
            log_activity("ALERT", f"Telegram sent to chat_id for {alert.id} (URGENT)")
        else:
            # HIGH match
            msg = (
                "🔥 <b>HIGH MATCH (Score: {score})</b>\n"
                f"• <b>Buyer:</b> {buyer_name}\n"
                f"• <b>Address:</b> {address}\n"
                f"• <b>Price:</b> {price}\n"
                f"• <b>ID:</b> <code>{alert.id}</code>"
            ).format(score=score)
            await send_notification(msg)
            log_activity("ALERT", f"Telegram sent to chat_id for {alert.id} (HIGH)")

    def _is_new(self, listing: Dict[str, Any], source: str) -> bool:
        """Check if listing has been seen before using a persisted content hash."""
        content = f"{listing.get('address','')}{listing.get('price','')}{source}"
        h = hashlib.md5(content.encode()).hexdigest()
        if h in self.seen_hashes:
            return False
        self.seen_hashes[h] = datetime.utcnow().isoformat()
        self._save_seen_hashes()
        return True

    def _load_seen_hashes(self) -> Dict[str, str]:
        """Load persisted seen-hashes dict (hash → ISO timestamp)."""
        if SEEN_HASHES_FILE.exists():
            try:
                with open(SEEN_HASHES_FILE, "r") as f:
                    data = json.load(f)
                    # Legacy: if it was stored as a list of strings, migrate
                    if isinstance(data, list):
                        ts = datetime.utcnow().isoformat()
                        return {h: ts for h in data}
                    return data
            except Exception as e:
                logger.error(f"Error loading seen hashes: {e}")
        return {}

    def _save_seen_hashes(self) -> None:
        """Persist seen-hashes dict to disk."""
        try:
            SEEN_HASHES_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SEEN_HASHES_FILE, "w") as f:
                json.dump(self.seen_hashes, f)
        except Exception as e:
            logger.error(f"Error saving seen hashes: {e}")

    def _purge_old_seen_hashes(self) -> None:
        """Remove hashes older than 48 hours so genuinely re-listed properties resurface."""
        now = datetime.utcnow()
        to_delete = []
        for h, ts_str in self.seen_hashes.items():
            try:
                if now - datetime.fromisoformat(ts_str) > timedelta(hours=48):
                    to_delete.append(h)
            except Exception:
                to_delete.append(h)
        if to_delete:
            for h in to_delete:
                del self.seen_hashes[h]
            self._save_seen_hashes()
            logger.info(f"🧹 Purged {len(to_delete)} old hashes from seen_hashes.json")

    @staticmethod
    def _parse_price(price_str) -> int:
        """Parse price string to integer."""
        if isinstance(price_str, (int, float)):
            return int(price_str)
        try:
            cleaned = str(price_str).replace("$", "").replace(",", "").strip()
            return int(float(cleaned))
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _parse_int(val) -> int:
        """Parse a value to integer."""
        if isinstance(val, (int, float)):
            return int(val)
        try:
            return int(str(val).strip().split()[0])
        except (ValueError, TypeError, IndexError):
            return 0


# ── Singleton agent instance ───────────────────────────────────────────────
agent = ListingAgent()
