import httpx
import asyncio
import json
import re

async def inspect():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    # Zoocasa
    print("\n--- Zoocasa NEXT_DATA Detail ---")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://www.zoocasa.com/toronto-on-real-estate", headers=headers, timeout=15)
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', resp.text)
            if match:
                data = json.loads(match.group(1))
                # props -> pageProps -> initialState -> listings -> listings
                try:
                    listings = data['props']['pageProps']['initialState']['listings']['listings']
                    print(f"Zoocasa: Found {len(listings)} listings")
                    print(f"Fields: {list(listings[0].keys())[:10]}")
                    print(f"Sample: {listings[0].get('address')}, {listings[0].get('price')}")
                except Exception as e:
                    print(f"Zoocasa path fail: {e}")
            else:
                print("NEXT_DATA not found for Zoocasa")
    except Exception as e:
        print(f"Zoocasa Err: {e}")

    # Condos.ca
    print("\n--- Condos.ca NEXT_DATA Detail ---")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://condos.ca/toronto/condos-for-sale", headers=headers, timeout=15)
            # Sometimes script IDs are different
            match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>', resp.text)
            if not match:
                # Try finding any large JSON script
                scripts = re.findall(r'<script[^>]*>(.+?)</script>', resp.text)
                for s in scripts:
                    if '"listings"' in s and '"props"' in s:
                        print("Found potential listings script")
                        data = json.loads(s)
                        break
                else:
                    data = None
            else:
                data = json.loads(match.group(1))

            if data:
                # props -> pageProps -> data -> listings
                try:
                    for p in ["props", "pageProps", "data", "listings"]:
                        print(f"Checking {p}...")
                        # This info is purely for me to debug
                    
                    # Search for data
                    def find_data_recursive(obj):
                        if isinstance(obj, dict):
                            if "address" in obj and "price" in obj: return [obj]
                            for v in obj.values():
                                res = find_data_recursive(v)
                                if res: return res
                        elif isinstance(obj, list):
                            if len(obj) > 0 and isinstance(obj[0], dict) and "address" in obj[0]:
                                return obj
                            for v in obj:
                                res = find_data_recursive(v)
                                if res: return res
                        return None
                    
                    listings = find_data_recursive(data)
                    if listings:
                        print(f"Condos.ca: Found {len(listings)} listings")
                        print(f"Fields: {list(listings[0].keys())[:10]}")
                    else:
                        print("Condos.ca: Could not find listings in data")
                except Exception as e:
                    print(f"Condos.ca error: {e}")
            else:
                 print("NEXT_DATA not found for Condos.ca")

    except Exception as e:
        print(f"Condos.ca Err: {e}")

if __name__ == "__main__":
    asyncio.run(inspect())
