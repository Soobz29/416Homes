import asyncio
import logging
import os
import json
import re
from typing import List, Dict, Any
import requests
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

# URL mappings matching the existing scraper target areas
AREA_URLS = {
    "toronto": "https://www.realtor.ca/map#ZoomLevel=12&Center=43.718501%2C-79.378125&LatitudeMax=43.8555&LongitudeMax=-79.1169&LatitudeMin=43.5810&LongitudeMin=-79.6393&Sort=6-D&PropertyTypeGroupID=1&TransactionTypeId=2&PropertySearchTypeId=0&Currency=CAD",
    "mississauga": "https://www.realtor.ca/map#ZoomLevel=12&Center=43.630560%2C-79.663500&LatitudeMax=43.7320&LongitudeMax=-79.4830&LatitudeMin=43.5290&LongitudeMin=-79.8440&Sort=6-D&PropertyTypeGroupID=1&TransactionTypeId=2&PropertySearchTypeId=0&Currency=CAD",
    "gta": "https://www.realtor.ca/map#ZoomLevel=11&Center=43.742879%2C-79.480450&LatitudeMax=43.9560&LongitudeMax=-79.1169&LatitudeMin=43.5290&LongitudeMin=-79.8440&Sort=6-D&PropertyTypeGroupID=1&TransactionTypeId=2&PropertySearchTypeId=0&Currency=CAD",
}

async def scrape_realtor_with_browser_use(city: str = "gta") -> List[Dict[str, Any]]:
    """
    Uses Browser Use Cloud to dynamically extract Real Estate listings from Realtor.ca map page.
    """
    url = AREA_URLS.get(city.lower(), AREA_URLS["gta"])
    
    # We ask the agent to return the structured data fields needed by 416Homes
    request_prompt = (
        "Extract all property listings visible on the map and side panel. "
        "For each property return: "
        "- 'address': Full address string\n"
        "- 'price': Price as an integer (e.g. 1500000)\n"
        "- 'bedrooms': Number of bedrooms as string (e.g. '2+1')\n"
        "- 'bathrooms': Number of bathrooms as string (e.g. '2')\n"
        "- 'property_type': Type of property (e.g. 'Condo', 'Detached')\n"
        "- 'url': The URL link to the property listing details page"
    )
    
    logger.info(f"Triggering Browser Use Cloud agent for Realtor.ca ({city})")
    extracted_data = await _run_browser_use_extraction(url, request_prompt)
    
    listings = []
    
    # Map the raw objects back to standard 416Homes schema
    for item in extracted_data:
        price = item.get("price", 0)
        
        # Clean price if returned as string
        if isinstance(price, str):
            try:
                price = int(re.sub(r'[^\d]', '', price))
            except ValueError:
                price = 0
                
        # Skip items that don't look valid
        if not price or not item.get("address"):
            continue
            
        href = item.get("url", "")
        mls = href.split('/')[-1] if href else hashlib.md5(item["address"].encode()).hexdigest()[:12]
            
        listings.append({
            "id": f"realtor_ca_{mls}",
            "source": "realtor_ca",
            "url": href if href.startswith("http") else f"https://www.realtor.ca{href}",
            "address": item.get("address", ""),
            "city": city.title(),
            "price": price,
            "bedrooms": item.get("bedrooms", "0"),
            "bathrooms": item.get("bathrooms", "0"),
            "property_type": item.get("property_type", "Unknown"),
            "sqft": "",
            "lat": None,
            "lng": None,
            "scraped_at": datetime.utcnow().isoformat(),
        })
        
    logger.info(f"✨ Browser Use extracted {len(listings)} structured listings.")
    return listings


async def _run_browser_use_extraction(url: str, request: str) -> List[Dict[str, Any]]:
    """
    Calls the https://api.browser-use.com/api/v2/tasks endpoint and polls for JSON results.
    """
    api_key = os.getenv("BROWSER_USE_API_KEY")
    if not api_key:
        logger.error("BROWSER_USE_API_KEY is missing from environment variables.")
        # Return empty list properly so agent doesn't crash
        return []
        
    base_url = os.getenv("BROWSER_USE_BASE_URL", "https://api.browser-use.com/api/v2")
    
    # JSON schema we want the AI to conform to
    extraction_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "url": {"type": "string"},
            "request": {"type": "string"},
            "data": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": True
                }
            },
            "notes": {"type": ["string", "null"]}
        },
        "required": ["url", "request", "data"]
    }

    task_prompt = (
        f"Open this URL: {url}\n"
        f"Extraction request: {request}\n"
        "Wait for the content to load fully.\n"
        "Return ONLY JSON matching the provided structuredOutput schema.\n"
        "Set missing values to null instead of guessing.\n"
        "Include a notes field when blocked by auth/captcha/anti-bot or when data quality is limited."
    )

    hostname = url.split("//")[-1].split("/")[0]

    headers = {
        "Content-Type": "application/json",
        "X-Browser-Use-API-Key": api_key,
    }

    payload = {
        "task": task_prompt,
        "startUrl": url,
        "structuredOutput": json.dumps(extraction_schema),
        "maxSteps": 100,
        "allowedDomains": [hostname],
        "highlightElements": False,
        "flashMode": False,
    }

    try:
        # Create Task
        logger.info(f"Submitting Browser Use Cloud task...")
        resp = await asyncio.to_thread(requests.post, f"{base_url}/tasks", headers=headers, json=payload)
        
        if resp.status_code not in (200, 201, 202):
            logger.error(f"Browser Use API task creation failed ({resp.status_code}): {resp.text}")
            return []
            
        task_data = resp.json()
        task_id = task_data.get("id")
        
        if not task_id:
            logger.error("Browser Use did not return a valid task id.")
            return []

        logger.info(f"Browser Use Cloud task {task_id} successfully created. Polling status...")

        # Poll Status (max 180 attempts ~ 6 minutes as per SDK)
        for attempt in range(180):
            await asyncio.sleep(2)
            
            status_resp = await asyncio.to_thread(requests.get, f"{base_url}/tasks/{task_id}/status", headers=headers)
            
            if status_resp.status_code != 200:
                logger.error(f"Browser Use polling failed ({status_resp.status_code}): {status_resp.text}")
                return []
                
            status_payload = status_resp.json()
            status = status_payload.get("status")
            
            if status == "finished":
                output_str = status_payload.get("output", "{}")
                try:
                    # Parse the output JSON which is returned as a string payload
                    # Strip any markdown fences
                    output_str = re.sub(r'^```(?:json)?\s*', '', output_str.strip())
                    output_str = re.sub(r'\s*```$', '', output_str)
                    
                    parsed_data = json.loads(output_str)
                    return parsed_data.get("data", [])
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Browser Use output JSON: {e}\nRaw Output: {output_str}")
                    return []
                    
            elif status == "stopped":
                logger.warning(f"Browser Use task stopped prematurely. Output: {status_payload.get('output', '')}")
                return []
                
        logger.warning(f"Browser Use task timed out after 180 attempts.")
        return []

    except Exception as e:
        logger.error(f"Browser Use network request failed: {e}")
        return []
