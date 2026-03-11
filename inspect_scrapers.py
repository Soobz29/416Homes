import httpx
import asyncio
import json

async def inspect():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    print("--- Zoocasa API ---")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://www.zoocasa.com/api/listings/search",
                params={"city": "toronto", "province": "on", "listing_type": "sale", "per_page": 5},
                headers=headers,
                timeout=15
            )
            print(f"Status: {resp.status_code}")
            print(f"Content Type: {resp.headers.get('content-type')}")
            print(f"Body snippet: {resp.text[:500]}")
    except Exception as e:
        print(f"Zoocasa API Err: {e}")

    print("\n--- Zoocasa HTML (NEXT_DATA) ---")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://www.zoocasa.com/toronto-on-real-estate", headers=headers, timeout=15)
            print(f"Status: {resp.status_code}")
            if "__NEXT_DATA__" in resp.text:
                print("Found __NEXT_DATA__")
            else:
                print("NEXT_DATA not found")
    except Exception as e:
        print(f"Zoocasa HTML Err: {e}")

    print("\n--- Condos.ca API ---")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://condos.ca/api/v2/listings",
                params={"city": "toronto", "status": "for-sale", "per_page": 5},
                headers=headers,
                timeout=15
            )
            print(f"Status: {resp.status_code}")
            print(f"Content Type: {resp.headers.get('content-type')}")
            print(f"Body snippet: {resp.text[:500]}")
    except Exception as e:
        print(f"Condos.ca API Err: {e}")

    print("\n--- Condos.ca HTML (NEXT_DATA) ---")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://condos.ca/toronto/condos-for-sale", headers=headers, timeout=15)
            print(f"Status: {resp.status_code}")
            if "__NEXT_DATA__" in resp.text:
                print("Found __NEXT_DATA__")
            else:
                print("NEXT_DATA not found")
    except Exception as e:
        print(f"Condos.ca HTML Err: {e}")

if __name__ == "__main__":
    asyncio.run(inspect())
