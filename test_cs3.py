import asyncio
from curl_cffi.requests import AsyncSession

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
    s = AsyncSession(impersonate="chrome120")
    # First get the api subdomain to set Incapsula cookies for api2!
    res = await s.get("https://api2.realtor.ca/")
    print("API GET Status:", res.status_code)
    
    # Now add headers for POST
    s.headers.update({
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://www.realtor.ca",
        "Referer": "https://www.realtor.ca/",
    })
    
    res2 = await s.post('https://api2.realtor.ca/Listing.svc/PropertySearch_Post', data=payload)
    print("POST Status:", res2.status_code)
    try:
        data = res2.json()
        print("Success! Listings:", len(data.get("Results", [])))
    except:
        print("Failed to decode. First 200 chars:", res2.text[:200])

asyncio.run(main())
