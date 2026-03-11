import httpx
import asyncio
import re

async def capture():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    # Zoocasa
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://www.zoocasa.com/toronto-on-real-estate", headers=headers, timeout=15)
            with open("zoocasa_scripts.txt", "w", encoding="utf-8") as f:
                scripts = re.findall(r'<script[^>]*>(.+?)</script>', resp.text, re.DOTALL)
                for i, s in enumerate(scripts):
                    if len(s) > 100:
                        f.write(f"--- Script {i} ({len(s)} chars) ---\n")
                        f.write(s[:500] + "...\n\n")
            print("Zoocasa scripts captured")
    except Exception as e:
        print(f"Zoocasa Err: {e}")

    # Condos.ca
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://condos.ca/toronto/condos-for-sale", headers=headers, timeout=15)
            with open("condos_ca_scripts.txt", "w", encoding="utf-8") as f:
                scripts = re.findall(r'<script[^>]*>(.+?)</script>', resp.text, re.DOTALL)
                for i, s in enumerate(scripts):
                    if len(s) > 100:
                        f.write(f"--- Script {i} ({len(s)} chars) ---\n")
                        f.write(s[:500] + "...\n\n")
            print("Condos.ca scripts captured")
    except Exception as e:
        print(f"Condos.ca Err: {e}")

if __name__ == "__main__":
    asyncio.run(capture())
