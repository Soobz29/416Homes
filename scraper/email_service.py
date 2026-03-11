import os
import json
import logging
import asyncio
import re
from typing import Dict, Any
from listing_agent.activity_log import log_activity

logger = logging.getLogger(__name__)

MAX_EMAILS_PER_DAY = 50

async def draft_alert_emails(listing: Dict[str, Any]) -> Dict[str, str]:
    """
    Uses Gemini 2.0 Flash to draft two emails based on a real estate listing:
    1. An email to the Buyer (the User) summarizing the listing and its potential.
    2. An email to the Seller/Listing Agent asking for more details or booking a showing.
    """
    try:
        from google import genai
        from listing_agent.memory import agent_memory

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not set for email service.")
            return _fallback_emails(listing)

        # Rate Limit Check
        emails_sent_today = agent_memory.data.get("metrics", {}).get("emails_sent_today", 0)
        if emails_sent_today >= MAX_EMAILS_PER_DAY:
            logger.warning(f"[resend] Daily cap reached ({MAX_EMAILS_PER_DAY}) — skipping email")
            log_activity("SKIP", f"Email cap reached ({MAX_EMAILS_PER_DAY}/day)")
            # Still return drafted content for UI/logs, just don't send
            return _fallback_emails(listing)

        client = genai.Client(api_key=api_key)
        model_id = "gemini-2.5-flash"

        address = listing.get('address', 'Unknown Property')
        price = listing.get('price', 'Unknown Price')
        if isinstance(price, int):
            price = f"${price:,}"
            
        prompt = f"""You are an elite real estate AI agent acting on behalf of a buyer. 
A new off-market or highly desirable property just matched the buyer's criteria.

Property Details:
- Address: {address}
- Price: {price}
- Bedrooms: {listing.get('beds') or listing.get('bedrooms', 'N/A')}
- Bathrooms: {listing.get('baths') or listing.get('bathrooms', 'N/A')}
- Property Type: {listing.get('property_type', 'N/A')}

Draft two emails:
1. `buyer_email`: A short, exciting update to the buyer (your client) telling them why this property is a great match and that you're ready to book a showing.
2. `seller_email`: A professional inquiry to the listing agent/seller asking for the status, any offers, and requesting a showing time tomorrow.

Return ONLY a valid JSON object with the keys "buyer_email" and "seller_email". Do not wrap in markdown blocks.
"""

        try:
            response = await asyncio.to_thread(client.models.generate_content, model=model_id, contents=prompt)
            text = response.text.strip()
            text = re.sub(r'^```(?:json)?\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            email_data = json.loads(text)
        except Exception as e:
            log_activity("ERROR", f"gemini_call failed in draft_alert_emails: {e}")
            email_data = {}

        seller_email = email_data.get("seller_email", _fallback_emails(listing)["seller_email"])
        buyer_email = email_data.get("buyer_email", _fallback_emails(listing)["buyer_email"])

        import resend
        resend.api_key = os.getenv("RESEND_API_KEY", "")
        to_email = listing.get("agent_email") or os.getenv("AGENT_EMAIL", "agent@416homes.ca")

        if resend.api_key and seller_email:
            logger.info(f"[resend] Attempting to send to: {to_email}")
            logger.info(f"[resend] API key present: {bool(resend.api_key)}")
            try:
                result = resend.Emails.send({
                    "from": "onboarding@resend.dev",
                    "to": to_email,
                    "subject": f"Inquiry: {listing.get('address')}",
                    "html": seller_email
                })
                logger.info(f"[resend] Response: {result}")
                log_activity("EMAIL", f"Resend called for {to_email} — response: {getattr(result, 'id', result)}")
                
                # Increment metrics via event log
                agent_memory.log_event("email_sent", {
                    "to": to_email,
                    "address": listing.get("address")
                })
                
            except Exception as resend_err:
                logger.error(f"[resend] Send failed: {resend_err}")
                log_activity("ERROR", f"resend_send failed: {resend_err}")

        return {
            "buyer_email": buyer_email,
            "seller_email": seller_email
        }

    except Exception as e:
        logger.error(f"Failed to generate AI emails: {e}")
        return _fallback_emails(listing)

def _fallback_emails(listing: Dict[str, Any]) -> Dict[str, str]:
    address = listing.get('address', 'the property')
    return {
        "buyer_email": f"Hi there,\n\nGreat news! We just found a new listing that matches your criteria at {address}. Let me know if you'd like to book a showing!\n\nBest,\nYour 416Homes Agent",
        "seller_email": f"Hello,\n\nI am representing a qualified buyer interested in your listing at {address}. Could you please let me know if you are reviewing offers anytime soon, and if we can schedule a walkthrough tomorrow?\n\nThank you,\n416Homes Partner"
    }
