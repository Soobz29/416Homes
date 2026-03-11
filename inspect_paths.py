import httpx
import asyncio
import json
import re

async def inspect():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    # Zoocasa
    print("\n--- Zoocasa NEXT_DATA Path Finding ---")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://www.zoocasa.com/toronto-on-real-estate", headers=headers, timeout=15)
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', resp.text)
            if match:
                data = json.loads(match.group(1))
                # Search for specific listing data
                def find_key_recursive(obj, target_key, path=""):
                    if isinstance(obj, dict):
                        if target_key in obj:
                            print(f"Key '{target_key}' found at: {path}.{target_key}")
                            if isinstance(obj[target_key], list) and len(obj[target_key]) > 0:
                                print(f"Sample item keys: {list(obj[target_key][0].keys())}")
                        for k, v in obj.items():
                            find_key_recursive(v, target_key, f"{path}.{k}")
                    elif isinstance(obj, list):
                        for i, v in enumerate(obj):
                            find_key_recursive(v, target_key, f"{path}[{i}]")

                find_key_recursive(data, "listings")
            else:
                print("NEXT_DATA not found for Zoocasa")
    except Exception as e:
        print(f"Zoocasa Err: {e}")

    # Condos.ca
    print("\n--- Condos.ca NEXT_DATA Path Finding ---")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://condos.ca/toronto/condos-for-sale", headers=headers, timeout=15)
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', resp.text)
            if match:
                data = json.loads(match.group(1))
                find_key_recursive(data, "listings")
                find_key_recursive(data, "data")
            else:
                print("NEXT_DATA not found for Condos.ca")
    except Exception as e:
        print(f"Condos.ca Err: {e}")

if __name__ == "__main__":
    asyncio.run(inspect())
