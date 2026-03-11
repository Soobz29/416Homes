import httpx
import asyncio
import json
import re

async def inspect():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    # Zoocasa
    print("\n--- Zoocasa NEXT_DATA ---")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://www.zoocasa.com/toronto-on-real-estate", headers=headers, timeout=15)
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', resp.text)
            if match:
                data = json.loads(match.group(1))
                # print(json.dumps(data, indent=2)[:2000])
                # Find where listings are
                def find_listings(obj, path=""):
                    if isinstance(obj, dict):
                        if "listings" in obj and isinstance(obj["listings"], list):
                            print(f"Found listings at {path}.listings (count: {len(obj['listings'])})")
                            return obj["listings"]
                        for k, v in obj.items():
                            res = find_listings(v, f"{path}.{k}")
                            if res: return res
                    elif isinstance(obj, list):
                        for i, v in enumerate(obj):
                            res = find_listings(v, f"{path}[{i}]")
                            if res: return res
                    return None
                
                listings = find_listings(data)
                if listings:
                    print(f"Sample listing keys: {list(listings[0].keys())}")
                    print(f"Sample listing address: {listings[0].get('address') or listings[0].get('full_address')}")
            else:
                print("NEXT_DATA not found for Zoocasa")
    except Exception as e:
        print(f"Zoocasa Err: {e}")

    # Condos.ca
    print("\n--- Condos.ca NEXT_DATA ---")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://condos.ca/toronto/condos-for-sale", headers=headers, timeout=15)
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', resp.text)
            if match:
                data = json.loads(match.group(1))
                def find_listings_condos(obj, path=""):
                    if isinstance(obj, dict):
                        if "listings" in obj and isinstance(obj["listings"], list):
                            print(f"Found listings at {path}.listings (count: {len(obj['listings'])})")
                            return obj["listings"]
                        if "data" in obj and isinstance(obj["data"], list) and len(obj["data"]) > 0 and "address" in obj["data"][0]:
                            print(f"Found data list at {path}.data (count: {len(obj['data'])})")
                            return obj["data"]
                        for k, v in obj.items():
                            res = find_listings_condos(v, f"{path}.{k}")
                            if res: return res
                    elif isinstance(obj, list):
                        for i, v in enumerate(obj):
                            res = find_listings_condos(v, f"{path}[{i}]")
                            if res: return res
                    return None
                
                listings = find_listings_condos(data)
                if listings:
                    print(f"Sample listing keys: {list(listings[0].keys())}")
                    print(f"Sample listing address: {listings[0].get('address')}")
            else:
                print("NEXT_DATA not found for Condos.ca")
    except Exception as e:
        print(f"Condos.ca Err: {e}")

if __name__ == "__main__":
    asyncio.run(inspect())
