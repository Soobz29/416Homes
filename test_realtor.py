import asyncio
from curl_cffi.requests import AsyncSession

REALTOR_API = "https://api2.realtor.ca/Listing.svc/PropertySearch_Post"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://www.realtor.ca",
    "Referer": "https://www.realtor.ca/",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
}

payload = {
    "ZoomLevel": "13",
    "LatitudeMax": "43.9560",
    "LatitudeMin": "43.5290",
    "LongitudeMax": "-79.1169",
    "LongitudeMin": "-79.8440",
    "Sort": "6-D",
    "PropertyTypeGroupID": "1",
    "TransactionTypeId": "2",
    "PropertySearchTypeId": "0",
    "Currency": "CAD",
    "RecordsPerPage": "50",
    "ApplicationId": "1",
    "CultureId": "1",
    "Version": "7.0",
    "CurrentPage": "1",
}

async def main():
    async with AsyncSession(impersonate="chrome120") as s:
        # Get cookies first
        await s.get("https://www.realtor.ca/", headers={"User-Agent": HEADERS["User-Agent"]})
        
        response = await s.post(REALTOR_API, data=payload, headers=HEADERS)
        import json
        try:
            data = response.json()
            for item in data.get('Results', [])[:5]:
                print(f"https://www.realtor.ca{item.get('RelativeDetailsURL', '')}")
        except Exception as e:
            print("Failed to parse JSON")

asyncio.run(main())
