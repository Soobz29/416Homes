import asyncio
from curl_cffi.requests import AsyncSession

async def main():
    async with AsyncSession(impersonate="chrome120") as s:
        response = await s.post('https://api2.realtor.ca/Listing.svc/PropertySearch_Post', data={'LatitudeMax':'43.9'}, headers={'User-Agent': 'Mozilla/5.0'})
        with open('akamai.html', 'w') as f:
            f.write(response.text)

asyncio.run(main())
