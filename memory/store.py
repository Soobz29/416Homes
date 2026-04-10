import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
import os

# google-genai is NOT imported at module level — lazy-loaded on first embedding call
# to keep API server startup memory low (~100MB instead of ~400MB).
_genai = None
_GENAI_SDK = "none"
_genai_loaded = False

def _load_genai():
    """Import google-genai once, on first use."""
    global _genai, _GENAI_SDK, _genai_loaded
    if _genai_loaded:
        return
    _genai_loaded = True
    try:
        from google import genai as _g  # type: ignore
        _genai = _g
        _GENAI_SDK = "google-genai"
        return
    except Exception:
        pass
    try:
        import google.generativeai as _g  # type: ignore
        _genai = _g
        _GENAI_SDK = "google-generativeai"
    except Exception:
        _genai = None
        _GENAI_SDK = "none"

load_dotenv()
logger = logging.getLogger(__name__)

class MemoryStore:
    """Supabase-backed memory store with pgvector embeddings"""
    
    def __init__(self):
        supabase_url = (os.getenv("SUPABASE_URL") or "").strip()
        # Prefer service_role for server-side reads/writes (RLS-safe),
        # fall back to anon key if needed.
        supabase_key = (
            (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or "").strip()
        )
        self.supabase: Optional[Client] = None
        if not supabase_url or not supabase_key:
            logger.warning(
                "SUPABASE_URL or Supabase key missing/empty; memory store disabled (API can still boot)"
            )
        else:
            try:
                self.supabase = create_client(supabase_url, supabase_key)
            except Exception as e:
                logger.error("Failed to create Supabase client: %s", e)
                self.supabase = None
        
        # Gemini client — lazy, initialised on first embedding call via _ensure_genai_client()
        self._gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.embedding_model_id = os.getenv("GEMINI_EMBEDDING_MODEL") or "gemini-embedding-001"
        self.client = None  # set on first use

        # In-memory LRU cache for embeddings (text → vector), avoids redundant API calls
        self._embedding_cache: Dict[str, List[float]] = {}

    def _ensure_genai_client(self):
        """Lazy-init the Gemini client — imports google-genai only on first call."""
        if self.client is not None:
            return
        _load_genai()
        try:
            if _GENAI_SDK == "google-genai" and _genai is not None:
                self.client = _genai.Client(api_key=self._gemini_api_key)
                self.embedding_model_id = os.getenv("GEMINI_EMBEDDING_MODEL") or "gemini-embedding-001"
            elif _GENAI_SDK == "google-generativeai" and _genai is not None:
                _genai.configure(api_key=self._gemini_api_key)
                self.client = _genai
                self.embedding_model_id = os.getenv("GEMINI_EMBEDDING_MODEL") or "text-embedding-004"
        except Exception as e:
            logger.warning("Gemini client init failed (%s): %s", _GENAI_SDK, e)

    @staticmethod
    def _safe_scalar(value: Any, default: Any = None, prefer_int: bool = False) -> Any:
        """Coerce value to a scalar for DB (no dicts/lists). For int columns use prefer_int=True."""
        if value is None:
            return default
        if isinstance(value, dict):
            # e.g. {"gt":0,"gte":2500} from a range filter - take a number if present
            for k in ("gte", "lte", "gt", "lt"):
                if k in value and isinstance(value[k], (int, float)):
                    return int(value[k]) if prefer_int else value[k]
            return default
        if isinstance(value, (list, tuple)):
            return value[0] if value and prefer_int else (int(value[0]) if value and isinstance(value[0], (int, float)) else default)
        if isinstance(value, (int, float)):
            return int(value) if prefer_int and isinstance(value, float) and value == int(value) else value
        if isinstance(value, str) and value.strip():
            try:
                n = int(value.replace(",", "").strip())
                return n if prefer_int else value
            except ValueError:
                pass
        return value if not prefer_int else default

    def _extract_neighbourhood(self, address: str) -> str:
        """Extract neighbourhood from address string"""
        if not address:
            return "Unknown"
        
        # Split by comma and take middle component if available
        parts = [part.strip() for part in address.split(',')]
        if len(parts) >= 2:
            # Skip first part (street number/name) and last part (city/province)
            # Take the middle part as neighbourhood
            return parts[1] if len(parts) > 2 else parts[0].split()[0] if parts[0] else "Unknown"
        
        # Fallback: try to extract from first part
        first_part = parts[0]
        words = first_part.split()
        if len(words) > 2:
            return words[1]  # Second word might be neighbourhood
        
        return "Unknown"
    
    @staticmethod
    def _to_coord(val: Any):
        """Return float coordinate or None — never an empty string."""
        if val is None or val == "":
            return None
        try:
            return float(val) or None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_room_count(val: Any) -> str:
        """Parse room count strings like '1 + 1' (bedroom + den) into their integer sum ('2').
        Returns the value unchanged if it doesn't match that pattern."""
        if isinstance(val, str) and '+' in val:
            try:
                return str(sum(int(x.strip()) for x in val.split('+')))
            except (ValueError, TypeError):
                pass
        return str(val) if val not in (None, "") else ""

    @staticmethod
    def _fix_zoocasa_wrapped_photo_url(url: str) -> str:
        if not url or "cdn.zoocasa.com/https://" not in url:
            return url
        inner = url.split("cdn.zoocasa.com/", 1)[1]
        if inner.startswith("https://") and inner.endswith("-1.jpg"):
            return inner[: -len("-1.jpg")]
        return inner

    @staticmethod
    def _extract_photo_url(listing: Dict[str, Any]) -> Optional[str]:
        """Extract a canonical photo URL from top-level or raw_data candidate keys."""
        def _from_value(value: Any) -> Optional[str]:
            if not value:
                return None
            if isinstance(value, str):
                v = MemoryStore._fix_zoocasa_wrapped_photo_url(value.strip())
                if v.startswith("http://") or v.startswith("https://"):
                    return v
                return None
            if isinstance(value, list):
                for item in value:
                    got = _from_value(item)
                    if got:
                        return got
                return None
            if isinstance(value, dict):
                for key in ("url", "href", "src", "highResPath", "HighResPath"):
                    got = _from_value(value.get(key))
                    if got:
                        return got
                return None
            return None

        raw_data = listing.get("raw_data") if isinstance(listing.get("raw_data"), dict) else {}
        candidates = [
            listing.get("photo"),
            listing.get("photos"),
            raw_data.get("image_root_storage_key"),
            raw_data.get("photo"),
            raw_data.get("photos"),
            raw_data.get("image"),
            raw_data.get("images"),
            raw_data.get("image_url"),
            raw_data.get("image_urls"),
            raw_data.get("photo_url"),
            raw_data.get("photo_urls"),
            raw_data.get("thumbnail"),
            raw_data.get("thumbnails"),
        ]
        for candidate in candidates:
            out = _from_value(candidate)
            if out:
                return out
        return None

    def _normalise_for_listings(self, listing: Dict[str, Any]) -> Dict[str, Any]:
        """Translate scraper dict to exact Supabase listings column names. Coerce scalars so no dicts hit DB."""
        price = self._safe_scalar(listing.get("price"), 0, prefer_int=True)
        if price is None:
            price = 0
        try:
            price = int(price)
        except (TypeError, ValueError):
            price = 0
        bedrooms = self._parse_room_count(self._safe_scalar(listing.get("bedrooms"), ""))
        bathrooms = self._parse_room_count(self._safe_scalar(listing.get("bathrooms"), ""))
        sqft_raw = listing.get("area") or listing.get("sqft")
        sqft = self._safe_scalar(sqft_raw, 0, prefer_int=True)
        if isinstance(sqft, dict):
            sqft = 0
        if sqft is None:
            sqft = 0
        try:
            sqft = int(sqft)
        except (TypeError, ValueError):
            sqft = 0
        days_on_market = self._safe_scalar(listing.get("days_on_market"), 0, prefer_int=True)
        if days_on_market is None:
            days_on_market = 0
        try:
            days_on_market = int(days_on_market)
        except (TypeError, ValueError):
            days_on_market = 0
        return {
            "id": str(listing.get("id", "")),
            "source": str(listing.get("source", "")),
            "url": str(listing.get("url", "")),
            "address": str(listing.get("address", "") or ""),
            "neighbourhood": str(listing.get("neighbourhood") or self._extract_neighbourhood(listing.get("address", "") or "")),
            "city": str(listing.get("city", "Toronto") or "Toronto"),
            "price": price,
            "bedrooms": (bedrooms if not isinstance(bedrooms, dict) else None) or None,
            "bathrooms": (bathrooms if not isinstance(bathrooms, dict) else None) or None,
            "area": sqft,
            "property_type": str(listing.get("property_type", "Unknown") or "Unknown"),
            "days_on_market": days_on_market,
            "photo": self._extract_photo_url(listing),
            "listing_agent_email": listing.get("listing_agent_email"),
            "listing_agent_name": listing.get("listing_agent_name"),
            "lat": self._to_coord(listing.get("lat")),
            "lng": self._to_coord(listing.get("lng")),
            "raw_data": listing,
            "embedding": None,  # Will be filled later
            "scraped_at": listing.get("scraped_at", "") or "",
            "is_active": True
        }

    async def backfill_missing_listing_photos(self, limit: int = 1000) -> int:
        """Backfill listings.photo from raw_data candidate image fields."""
        try:
            if not self.supabase:
                logger.warning("Supabase not configured; skip photo backfill")
                return 0
            # Pull recent rows and update only those with missing/blank photo.
            rows = (
                self.supabase.table("listings")
                .select("id,photo,raw_data")
                .order("scraped_at", desc=True)
                .limit(limit)
                .execute()
                .data
                or []
            )
            updated = 0
            for row in rows:
                existing = (row.get("photo") or "").strip()
                if existing:
                    continue
                recovered = self._extract_photo_url(row)
                if not recovered:
                    continue
                self.supabase.table("listings").update({"photo": recovered}).eq("id", row["id"]).execute()
                updated += 1
            logger.info("Backfilled listing photos for %d rows", updated)
            return updated
        except Exception as e:
            logger.error("Failed to backfill listing photos: %s", e)
            return 0
    
    def _normalise_for_sold_comps(self, comp: Dict[str, Any]) -> Dict[str, Any]:
        """Translate scraper dict to exact Supabase sold_comps column names"""
        dom_raw = comp.get("days_on_market", 0)
        try:
            dom = int(dom_raw) if dom_raw not in (None, "") else 0
        except (TypeError, ValueError):
            dom = 0
        return {
            "id": comp.get("id", ""),
            "address": comp.get("address", ""),
            "neighbourhood": comp.get("neighbourhood") or self._extract_neighbourhood(comp.get("address", "")),
            "city": comp.get("city", "Toronto"),
            "sold_price": comp.get("price", 0),  # Map price → sold_price
            "list_price": comp.get("list_price"),
            "bedrooms": comp.get("bedrooms", ""),
            "bathrooms": comp.get("bathrooms", ""),
            "area": comp.get("area", comp.get("sqft", "0")),
            "property_type": comp.get("property_type", "Unknown"),
            "sold_date": comp.get("sold_date"),
            "days_on_market": dom,
            "lat": self._to_coord(comp.get("lat")),
            "lng": self._to_coord(comp.get("lng")),
            "scraped_at": comp.get("scraped_at", "")
        }
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text using Gemini (in-memory LRU cache, 1024 entries)."""
        if not text:
            return [0.0] * 768
        if text in self._embedding_cache:
            return self._embedding_cache[text]
        embedding = await self._embed_text_uncached(text)
        if len(self._embedding_cache) >= 1024:
            # Evict oldest entry
            self._embedding_cache.pop(next(iter(self._embedding_cache)))
        self._embedding_cache[text] = embedding
        return embedding

    async def _embed_text_uncached(self, text: str) -> List[float]:
        """Internal: call Gemini API without caching. Lazily loads google-genai on first call."""
        try:
            if not text:
                return [0.0] * 768

            self._ensure_genai_client()

            if _GENAI_SDK == "google-genai":
                if not self.client:
                    raise RuntimeError("Gemini client not initialized")
                kwargs = {"model": self.embedding_model_id, "contents": text}
                response = self.client.models.embed_content(**kwargs)
                embedding = list(response.embeddings[0].values) if response.embeddings else []
            elif _GENAI_SDK == "google-generativeai" and _genai is not None:
                resp = _genai.embed_content(
                    model=f"models/{self.embedding_model_id}",
                    content=text,
                )
                embedding = (resp.get("embedding") if isinstance(resp, dict) else None) or []
            else:
                return [0.0] * 768

            # Ensure 768 dimensions by truncating or padding if needed
            if len(embedding) > 768:
                embedding = embedding[:768]
            elif len(embedding) < 768:
                embedding = embedding + [0.0] * (768 - len(embedding))
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            # Return zero embedding as fallback
            return [0.0] * 768
    
    async def embed_and_store_listing(self, listing: Dict[str, Any]) -> bool:
        """Store a listing with its embedding"""
        try:
            if not self.supabase:
                logger.error("Supabase not configured; cannot store listing")
                return False
            # Normalise data first
            normalised = self._normalise_for_listings(listing)
            
            # Create searchable text from listing
            searchable_text = f"""
            {normalised['address']}
            {normalised['bedrooms']} bedrooms
            {normalised['bathrooms']} bathrooms
            {normalised['area']} sqft
            ${normalised['price']:,}
            {normalised['source']}
            """.strip()
            
            # Generate embedding
            embedding = await self.embed_text(searchable_text)
            normalised["embedding"] = embedding
            
            # Store in Supabase
            result = self.supabase.table("listings").upsert(normalised).execute()
            
            if result.data:
                logger.info(f"Stored listing {listing['id']} to database")
                return True
            else:
                logger.error(f"Failed to store listing {listing['id']}")
                return False
                
        except Exception as e:
            err_str = str(e)
            logger.error(f"Error storing listing {listing.get('id', 'unknown')}: {err_str}")
            if "numeric" in err_str or "integer" in err_str or "invalid input" in err_str:
                # Log each numeric field to find the culprit
                try:
                    n = self._normalise_for_listings(listing)
                    logger.error(
                        f"Numeric fields dump for {listing.get('id')}: "
                        f"price={n.get('price')!r} area={n.get('area')!r} "
                        f"days_on_market={n.get('days_on_market')!r} "
                        f"lat={n.get('lat')!r} lng={n.get('lng')!r} "
                        f"bedrooms={n.get('bedrooms')!r} bathrooms={n.get('bathrooms')!r}"
                    )
                except Exception:
                    pass
            return False
    
    async def embed_and_store_listings(self, listings: List[Dict[str, Any]]) -> int:
        """Store multiple listings concurrently"""
        tasks = [self.embed_and_store_listing(listing) for listing in listings]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for result in results if result is True)
        logger.info(f"Stored {success_count}/{len(listings)} listings successfully")
        
        return success_count

    async def clear_listings(self) -> int:
        """Delete all rows from the listings table. Returns number of ids removed."""
        try:
            if not self.supabase:
                logger.warning("Supabase not configured; skip clear_listings")
                return 0
            ids = []
            page_size = 500
            offset = 0
            while True:
                result = (
                    self.supabase.table("listings")
                    .select("id")
                    .range(offset, offset + page_size - 1)
                    .execute()
                )
                page = [r["id"] for r in (result.data or [])]
                ids.extend(page)
                if len(page) < page_size:
                    break
                offset += page_size
            if not ids:
                logger.info("listings table already empty")
                return 0
            chunk_size = 200
            deleted = 0
            for i in range(0, len(ids), chunk_size):
                chunk = ids[i : i + chunk_size]
                self.supabase.table("listings").delete().in_("id", chunk).execute()
                deleted += len(chunk)
            logger.info(f"Cleared {deleted} listings from database")
            return deleted
        except Exception as e:
            logger.error(f"Failed to clear listings: {e}")
            raise

    async def replace_listings(self, listings: List[Dict[str, Any]]) -> int:
        """Remove all existing listings and store the new set. Use for full refresh."""
        await self.clear_listings()
        if not listings:
            return 0
        return await self.embed_and_store_listings(listings)
    
    async def search_similar_listings(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for similar listings using vector similarity"""
        try:
            if not self.supabase:
                return []
            # Generate query embedding
            query_embedding = await self.embed_text(query)
            
            # Perform vector search using Supabase pgvector
            result = self.supabase.rpc(
                "match_listings",  # Use correct RPC function name
                {
                    "query_embedding": query_embedding,
                    "match_threshold": 0.7,
                    "match_count": limit
                }
            ).execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    async def store_sold_comp(self, comp: Dict[str, Any]) -> bool:
        """Store sold comparable property"""
        try:
            if not self.supabase:
                return False
            # Normalise data first
            normalised = self._normalise_for_sold_comps(comp)
            
            result = self.supabase.table("sold_comps").upsert(normalised).execute()
            
            if result.data:
                logger.info(f"Stored sold comp {comp['id']} to database")
                return True
            else:
                logger.error(f"Failed to store sold comp {comp['id']}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing sold comp {comp.get('id', 'unknown')}: {e}")
            return False
    
    async def get_sold_comps_by_neighborhood(self, neighborhood: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get sold comps for a specific neighborhood"""
        try:
            if not self.supabase:
                return []
            result = self.supabase.table("sold_comps")\
                .select("*")\
                .eq("neighbourhood", neighborhood)\
                .order("sold_date", desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Failed to get sold comps for {neighborhood}: {e}")
            return []
    
    async def get_listings(self, city: str = None, cities: List[str] = None, limit: int = 20, offset: int = 0, min_price: int = None, max_price: int = None, min_beds: float = None, min_baths: float = None) -> List[Dict[str, Any]]:
        """Get listings with filters. Pass city (single) or cities (list) for location. offset/limit for pagination."""
        try:
            if not self.supabase:
                return []
            query = self.supabase.table("listings").select("*")
            if cities:
                query = query.in_("city", cities)
            elif city:
                query = query.eq("city", city)
            if min_price:
                query = query.gte("price", min_price)
            if max_price:
                query = query.lte("price", max_price)
            if min_beds:
                query = query.gte("bedrooms", min_beds)
            if min_baths:
                query = query.gte("bathrooms", min_baths)
            # range is 0-indexed inclusive: range(offset, offset+limit-1) gives `limit` rows
            end = offset + limit - 1
            result = query.order("scraped_at", desc=True).range(offset, end).execute()
            return result.data or []
            
        except Exception as e:
            logger.error(f"Failed to get listings: {e}")
            return []

# Global memory store instance
memory_store = MemoryStore()

# Convenience functions
async def embed_and_store_listings(listings: List[Dict[str, Any]]) -> int:
    """Store multiple listings to database"""
    return await memory_store.embed_and_store_listings(listings)

async def replace_listings(listings: List[Dict[str, Any]]) -> int:
    """Clear all listings and store the new set (full refresh)."""
    return await memory_store.replace_listings(listings)

async def store_sold_comps(comps: List[Dict[str, Any]]) -> int:
    """Store multiple sold comps to database"""
    tasks = [memory_store.store_sold_comp(comp) for comp in comps]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success_count = sum(1 for result in results if result is True)
    logger.info(f"Stored {success_count}/{len(comps)} sold comps successfully")
    
    return success_count

async def search_listings(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search listings using vector similarity"""
    return await memory_store.search_similar_listings(query, limit)

async def backfill_missing_listing_photos(limit: int = 1000) -> int:
    """Backfill missing listings.photo values from raw_data fields."""
    return await memory_store.backfill_missing_listing_photos(limit=limit)
