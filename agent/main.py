#!/usr/bin/env python3
"""
416Homes Agent Main Loop

Matches new listings to buyer alerts and sends outreach emails.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import os
from dotenv import load_dotenv

from supabase import create_client
from memory.store import search_listings
from valuation.model import ValuationModel
try:
    # New Gemini SDK (package: google-genai)
    from google import genai as _genai  # type: ignore
    _GENAI_SDK = "google-genai"
except Exception:  # pragma: no cover
    # Legacy Gemini SDK (package: google-generativeai)
    import google.generativeai as _genai  # type: ignore
    _GENAI_SDK = "google-generativeai"
import resend

load_dotenv()
logger = logging.getLogger(__name__)

class PropertyAgent:
    """Autonomous property agent that matches listings to buyer alerts"""
    
    def __init__(self):
        _key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        self.supabase = create_client(os.getenv("SUPABASE_URL"), _key)
        
        # Initialize Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        if _GENAI_SDK == "google-genai":
            self.client = _genai.Client(api_key=api_key)
        else:
            _genai.configure(api_key=api_key)
        self.model_id = "gemini-2.5-flash"
        
        # Initialize Resend
        resend.api_key = os.getenv("RESEND_API_KEY")
        
        # Initialize valuation model
        self.valuation_model = ValuationModel()
        self.valuation_model.load_model()
        
        self.agent_email = os.getenv("AGENT_EMAIL")
    
    async def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active buyer alerts joined with user email."""
        try:
            # Join users table so each alert row has the buyer's email
            result = self.supabase.table("alerts")\
                .select("*, users(email)")\
                .eq("is_active", True)\
                .execute()

            rows = result.data if result.data else []
            # Flatten: pull email up from nested users object
            for r in rows:
                if not r.get("email") and isinstance(r.get("users"), dict):
                    r["email"] = r["users"].get("email", "")
            return rows

        except Exception as e:
            logger.error(f"Error fetching alerts: {e}")
            return []
    
    async def get_new_listings(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Get new listings from the last N hours"""
        try:
            cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).isoformat()
            
            result = self.supabase.table("listings")\
                .select("*")\
                .gte("scraped_at", cutoff_time)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error fetching new listings: {e}")
            return []
    
    def calculate_match_score(self, listing: Dict[str, Any], alert: Dict[str, Any]) -> float:
        """Calculate match score between listing and alert criteria"""
        
        score = 0.0
        
        # Price match (40% weight)
        if alert.get('min_price') and alert.get('max_price'):
            price = listing.get('price', 0)
            if alert['min_price'] <= price <= alert['max_price']:
                score += 0.4
            elif price < alert['min_price']:
                score += 0.2  # Below minimum but close
            elif price > alert['max_price']:
                score += 0.1  # Above maximum but close
        
        # Bedrooms match (25% weight)
        if alert.get('min_beds'):
            beds = listing.get('bedrooms', 0)
            if isinstance(beds, str):
                try:
                    beds = int(beds)
                except (ValueError, TypeError):
                    beds = 0
            if beds >= alert['min_beds']:
                score += 0.25

        # Bathrooms match — alerts table has no min_bathrooms column; weight stays with bedrooms/price.
        # Property type match (10% weight)
        if alert.get('property_types'):
            property_type = listing.get('source', '').lower()
            alert_types = [pt.lower() for pt in alert['property_types']]
            if any(pt in property_type for pt in alert_types):
                score += 0.1
        
        # Neighborhood match (10% weight)
        if alert.get('neighbourhoods'):
            listing_neighbourhood = listing.get('address', '').lower()
            alert_neighbourhoods = [n.lower() for n in alert['neighbourhoods']]
            if any(neighbourhood in listing_neighbourhood for neighbourhood in alert_neighbourhoods):
                score += 0.1
        
        return min(score, 1.0)
    
    async def generate_outreach_email(self, listing: Dict[str, Any], alert: Dict[str, Any], match_score: float) -> str:
        """Generate personalized outreach email using Gemini"""
        
        try:
            # Get valuation for context
            valuation = self.valuation_model.predict(listing)
            
            if 'error' in valuation:
                logger.warning(f"Could not get valuation for {listing.get('address', 'Unknown')}")
                estimated_value = listing.get('price', 0)
                market_analysis = "Market price"
            else:
                estimated_value = valuation.get('estimated_value', listing.get('price', 0))
                market_analysis = valuation.get('market_analysis', 'Market price')
            
            prompt = f"""
            You are a professional real estate agent assistant. Generate a concise, professional outreach email for a property listing that matches a buyer's criteria.
            
            LISTING DETAILS:
            Address: {listing.get('address', 'Unknown')}
            Price: ${listing.get('price', 0):,}
            Bedrooms: {listing.get('bedrooms', 'N/A')}
            Bathrooms: {listing.get('bathrooms', 'N/A')}
            Square Feet: {listing.get('area', 'N/A')}
            Source: {listing.get('source', 'Unknown')}
            URL: {listing.get('url', 'Unknown')}
            
            BUYER CRITERIA:
            Email: {alert.get('email', 'Unknown')}
            Min Price: ${alert.get('min_price', 0):,}
            Max Price: ${alert.get('max_price', 0):,}
            Min Bedrooms: {alert.get('min_beds', 'N/A')}
            Property Types: {', '.join(alert.get('property_types') or [])}
            Neighbourhoods: {', '.join(alert.get('neighbourhoods') or [])}
            
            VALUATION CONTEXT:
            Estimated Value: ${estimated_value:,}
            Market Analysis: {market_analysis}
            Match Score: {match_score:.2f}/1.0
            
            Generate an email that:
            1. Is professional and concise
            2. Mentions the match score and why it's a good fit
            3. Includes a clear call to action
            4. Is personalized for the buyer
            5. Includes your agent contact information
            
            Keep it under 200 words.
            """
            
            if _GENAI_SDK == "google-genai":
                if not self.client:
                    raise RuntimeError("Gemini client not initialized")
                response = self.client.models.generate_content(model=self.model_id, contents=prompt)
                return response.text
            else:
                model = _genai.GenerativeModel(self.model_id)
                response = model.generate_content(prompt)
                return getattr(response, "text", "") or ""
            
        except Exception as e:
            logger.error(f"Error generating email: {e}")
            return f"Error generating outreach email for {listing.get('address', 'Unknown')}"
    
    async def send_outreach_email(self, listing: Dict[str, Any], alert: Dict[str, Any], email_content: str):
        """Send outreach email to listing agent"""
        
        try:
            # Extract agent email from listing URL or use default
            agent_email = os.getenv("LISTING_AGENT_EMAIL", "listing@realestate.com")
            
            params = {
                "from": f"416Homes Agent <{self.agent_email}>",
                "to": [agent_email],
                "subject": f"🏠 Buyer Match: {listing.get('address', 'Unknown')}",
                "html": email_content,
                "reply_to": self.agent_email
            }
            
            r = resend.Emails.send(params)
            
            if getattr(r, 'id', None):
                logger.info(f"Outreach email sent for {listing.get('address', 'Unknown')}")
                return True
            else:
                logger.error(f"Failed to send email (no id returned)")
                return False
                
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    async def send_telegram_alert(self, chat_id: str, listing: Dict[str, Any], valuation: Dict[str, Any]):
        """Send a Telegram notification to a buyer when a matching listing is found."""
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            return
        try:
            import httpx
            price = listing.get("price", 0)
            beds = listing.get("bedrooms", listing.get("beds", "?"))
            baths = listing.get("bathrooms", listing.get("baths", "?"))
            market_analysis = valuation.get("market_analysis", "—")
            url = listing.get("url", "")
            address = listing.get("address", "Unknown")
            msg = (
                f"🏠 *New Match: {address}*\n"
                f"💰 ${price:,} CAD\n"
                f"🛏 {beds}bd · 🚿 {baths}ba\n"
                f"📊 Fair value: {market_analysis}\n"
                f"🔗 [View listing]({url})"
            )
            async with httpx.AsyncClient(timeout=10) as c:
                resp = await c.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
                )
                if resp.status_code != 200:
                    logger.warning(f"Telegram notification failed: {resp.text}")
                else:
                    logger.info(f"Telegram alert sent to chat_id {chat_id} for {address}")
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")

    async def record_match(self, listing: Dict[str, Any], alert: Dict[str, Any], match_score: float, email_sent: bool):
        """Record the match in database"""
        
        try:
            match_data = {
                "listing_id": listing.get("id"),
                "alert_id": alert.get("id"),
                "match_score": match_score,
                "match_reason": f"Score {match_score:.2f}/1.0",
                "email_sent": email_sent,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table("agent_matches").insert(match_data).execute()
            
            if result.data:
                logger.info(f"Match recorded: {listing.get('address')} → {alert.get('email')}")
                return True
            else:
                logger.error(f"Failed to record match")
                return False
                
        except Exception as e:
            logger.error(f"Error recording match: {e}")
            return False
    
    async def process_alert(self, alert: Dict[str, Any]):
        """Process a single buyer alert"""
        
        logger.info(f"Processing alert for {alert.get('email')}")
        
        # Get new listings
        listings = await self.get_new_listings()
        
        if not listings:
            logger.info("No new listings to process")
            return
        
        good_matches = [
            (listing, self.calculate_match_score(listing, alert))
            for listing in listings
        ]
        good_matches = [(l, s) for l, s in good_matches if s >= 0.6]

        if not good_matches:
            logger.info("No matching listings found for this alert")
            return

        # Process up to 5 matches concurrently; semaphore prevents Resend rate limit
        semaphore = asyncio.Semaphore(5)

        async def _process_match(listing, match_score):
            async with semaphore:
                email_content = await self.generate_outreach_email(listing, alert, match_score)
                email_sent = await self.send_outreach_email(listing, alert, email_content)
                await self.record_match(listing, alert, match_score, email_sent)

                # Send Telegram notification if the buyer has linked their account
                if alert.get("telegram_chat_id"):
                    valuation = self.valuation_model.predict(listing)
                    await self.send_telegram_alert(alert["telegram_chat_id"], listing, valuation)

        await asyncio.gather(*[_process_match(l, s) for l, s in good_matches])
        logger.info(f"Alert processing complete: {len(good_matches)} matches found and processed")
    
    async def run_agent_loop(self):
        """Main agent loop"""
        
        logger.info("Starting 416Homes agent loop...")
        
        # Get all active alerts
        alerts = await self.get_active_alerts()
        
        if not alerts:
            logger.info("No active alerts found")
            return
        
        logger.info(f"Processing {len(alerts)} active alerts")
        
        # Process each alert
        for alert in alerts:
            await self.process_alert(alert)
        
        logger.info("Agent loop completed")

async def main():
    """Main entry point"""
    
    agent = PropertyAgent()
    await agent.run_agent_loop()

if __name__ == "__main__":
    asyncio.run(main())
