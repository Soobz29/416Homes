import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from google import genai

load_dotenv()
logger = logging.getLogger(__name__)

class MemoryStore:
    """Supabase-backed memory store with pgvector embeddings"""
    
    def __init__(self):
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        
        # Initialize Gemini for embeddings
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.embedding_model_id = "text-embedding-004"
    
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
    
    def _normalise_for_listings(self, listing: Dict[str, Any]) -> Dict[str, Any]:
        """Translate scraper dict to exact Supabase listings column names"""
        return {
            "id": listing.get("id", ""),
            "source": listing.get("source", ""),
            "url": listing.get("url", ""),
            "address": listing.get("address", ""),
            "neighbourhood": listing.get("neighbourhood") or self._extract_neighbourhood(listing.get("address", "")),
            "city": listing.get("city", "Toronto"),
            "price": listing.get("price", 0),
            "bedrooms": listing.get("bedrooms", ""),
            "bathrooms": listing.get("bathrooms", ""),
            "sqft": listing.get("area", listing.get("sqft", "0")),  # Map area → sqft
            "property_type": listing.get("property_type", "Unknown"),
            "days_on_market": listing.get("days_on_market", 0),
            "listing_agent_email": listing.get("listing_agent_email"),
            "listing_agent_name": listing.get("listing_agent_name"),
            "lat": listing.get("lat"),
            "lng": listing.get("lng"),
            "raw_data": listing,
            "embedding": None,  # Will be filled later
            "scraped_at": listing.get("scraped_at", ""),
            "is_active": True
        }
    
    def _normalise_for_sold_comps(self, comp: Dict[str, Any]) -> Dict[str, Any]:
        """Translate scraper dict to exact Supabase sold_comps column names"""
        return {
            "id": comp.get("id", ""),
            "address": comp.get("address", ""),
            "neighbourhood": comp.get("neighbourhood") or self._extract_neighbourhood(comp.get("address", "")),
            "city": comp.get("city", "Toronto"),
            "sold_price": comp.get("price", 0),  # Map price → sold_price
            "list_price": comp.get("list_price"),
            "bedrooms": comp.get("bedrooms", ""),
            "bathrooms": comp.get("bathrooms", ""),
            "sqft": comp.get("area", comp.get("sqft", "0")),  # Map area → sqft
            "property_type": comp.get("property_type", "Unknown"),
            "sold_date": comp.get("sold_date"),
            "days_on_market": comp.get("days_on_market", 0),
            "lat": comp.get("lat"),
            "lng": comp.get("lng"),
            "scraped_at": comp.get("scraped_at", "")
        }
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text using Gemini"""
        try:
            # Generate embedding
            response = self.client.models.embed_content(
                model=self.embedding_model_id,
                contents=text
            )
            embedding = response.embeddings[0].values
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
            # Normalise data first
            normalised = self._normalise_for_listings(listing)
            
            # Create searchable text from listing
            searchable_text = f"""
            {normalised['address']}
            {normalised['bedrooms']} bedrooms
            {normalised['bathrooms']} bathrooms
            {normalised['sqft']} sqft
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
            logger.error(f"Error storing listing {listing.get('id', 'unknown')}: {e}")
            return False
    
    async def embed_and_store_listings(self, listings: List[Dict[str, Any]]) -> int:
        """Store multiple listings concurrently"""
        tasks = [self.embed_and_store_listing(listing) for listing in listings]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for result in results if result is True)
        logger.info(f"Stored {success_count}/{len(listings)} listings successfully")
        
        return success_count
    
    async def search_similar_listings(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for similar listings using vector similarity"""
        try:
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
    
    async def get_listings(self, city: str = None, limit: int = 20, min_price: int = None, max_price: int = None, min_beds: float = None, min_baths: float = None) -> List[Dict[str, Any]]:
        """Get listings with filters"""
        try:
            query = self.supabase.table("listings").select("*")
            
            if city:
                query = query.eq("city", city)
            if min_price:
                query = query.gte("price", min_price)
            if max_price:
                query = query.lte("price", max_price)
            if min_beds:
                query = query.gte("bedrooms", min_beds)
            if min_baths:
                query = query.gte("bathrooms", min_baths)
            
            result = query.order("scraped_at", desc=True).limit(limit).execute()
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
