# Task 1: Fix Scrapers

Fix Kijiji, Redfin, and Zoocasa so each returns real listings.
Then add Scrapling stealth as the primary strategy for all three.
Execute every step in sequence. Do not stop. Commit at the end.

---

## Step 1 — Inspect Kijiji DOM

Run this script to print the real HTML of a Kijiji listing card:

```python
# tools/inspect_kijiji.py
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36")
        print("Navigating to Kijiji...")
        await page.goto("https://www.kijiji.ca/b-real-estate/greater-toronto-area/c34l1700272",
                        wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)
        # Try several possible card selectors and print what has the most matches
        for sel in ["li[data-listing-id]", "article", "[data-qa='adListing']",
                    ".search-item", "li.regular-ad", "[class*='listing']"]:
            els = await page.query_selector_all(sel)
            if els:
                print(f"FOUND {len(els)} elements with selector: {sel}")
                html = await els[0].inner_html()
                print(f"First element HTML (first 800 chars):\\n{html[:800]}\\n---")
        await browser.close()

asyncio.run(main())
```

Create this file, run it with `python tools/inspect_kijiji.py`, read the output.
Identify: (a) the card selector with the most matches, (b) the sub-selectors for
address/title, price, beds, baths, and href.

## Step 2 — Update kijiji.py

Open `scraper/kijiji.py`. Replace the selector values with what you found.
Specifically update:
- `await page.wait_for_selector('CARD_SELECTOR', timeout=20000)`
- `await page.query_selector_all('CARD_SELECTOR')`
- The inner `query_selector` calls for title, price, beds, baths, href

Run: `python -m scraper.run_all --source kijiji --area toronto`
If result is ≥10 listings, continue. If 0, re-inspect and try again.

## Step 3 — Inspect Redfin DOM

```python
# tools/inspect_redfin.py
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36")
        print("Navigating to Redfin...")
        await page.goto("https://www.redfin.ca/city/135726/Ontario/Toronto",
                        wait_until="networkidle", timeout=30000)
        await asyncio.sleep(4)
        for sel in ["[data-rf-test-id='homecard']", ".HomeCard", ".home-card",
                    "[class*='HomeCard']", "[class*='home-card']", ".MapHomeCard"]:
            els = await page.query_selector_all(sel)
            if els:
                print(f"FOUND {len(els)} with: {sel}")
                html = await els[0].inner_html()
                print(f"{html[:600]}\\n---")
        await browser.close()

asyncio.run(main())
```

Run it. Find the real card selector and sub-selectors.

## Step 4 — Update redfin.py

Apply the correct selectors to `scraper/redfin.py`.
Run: `python -m scraper.run_all --source redfin --area toronto`
Must return ≥5 listings.

## Step 5 — Inspect Zoocasa DOM

```python
# tools/inspect_zoocasa.py
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36")
        print("Navigating to Zoocasa...")
        await page.goto("https://www.zoocasa.com/toronto-on-real-estate",
                        wait_until="networkidle", timeout=30000)
        await asyncio.sleep(4)
        for sel in [".listing-card", "[class*='ListingCard']", "[class*='listing-card']",
                    "[class*='PropertyCard']", "[class*='property-card']", "article"]:
            els = await page.query_selector_all(sel)
            if els:
                print(f"FOUND {len(els)} with: {sel}")
                html = await els[0].inner_html()
                print(f"{html[:600]}\\n---")
        await browser.close()

asyncio.run(main())
```

Run it. Find real selectors. Update `scraper/zoocasa.py`.
Run: `python -m scraper.run_all --source zoocasa --area toronto`
Must return ≥5 listings.

## Step 6 — Add Scrapling stealth to all three scrapers

For each of kijiji.py, redfin.py, zoocasa.py:

1. Add a `scrape_scrapling_X()` function modelled on `scraper/realtor_ca.py → scrape_scrapling()`:

```python
from scrapling.fetchers import AsyncDynamicSession

async def scrape_scrapling_kijiji(area: str) -> list[dict]:
    """Strategy 1: Scrapling stealth browser"""
    print(f"  Strategy 1 (Scrapling): Kijiji {area}...")
    try:
        url = AREA_CONFIGS[area]["url"]
        async with AsyncDynamicSession(stealth=True) as fetcher:
            await asyncio.sleep(random.uniform(1.0, 2.5))
            page = await fetcher.fetch(url)
            cards = page.css("LI_SELECTOR_YOU_FOUND", adaptive=True)
            listings = []
            for card in cards:
                try:
                    address = card.css("ADDRESS_SELECTOR", adaptive=True)
                    price_el = card.css("PRICE_SELECTOR", adaptive=True)
                    # ... extract all fields
                    listings.append({
                        "id": f"kijiji_{...}",
                        "address": address[0].text if address else "",
                        "price": price_num,
                        "bedrooms": beds, "bathrooms": baths,
                        "area": area, "lat": None, "lng": None,
                        "source": "kijiji", "url": full_url,
                        "scraped_at": datetime.utcnow().isoformat(),
                        "strategy": "scrapling"
                    })
                except Exception:
                    continue
            return listings
    except Exception as e:
        print(f"  Scrapling failed: {e}")
        return []
```

2. Rename the existing Playwright function to `scrape_playwright_kijiji()`.

3. Update the main entry function to try Scrapling first:

```python
async def scrape_kijiji(area: str) -> list[dict]:
    area = area.lower()
    if area not in AREA_CONFIGS:
        raise ValueError(f"Unknown area: {area}")
    for strategy in [scrape_scrapling_kijiji, scrape_playwright_kijiji]:
        try:
            result = await strategy(area)
            if result:
                print(f"  Kijiji: {len(result)} listings via {strategy.__name__}")
                return result
        except Exception as e:
            print(f"  {strategy.__name__} failed: {e}")
    print(f"  Kijiji: all strategies failed for {area}")
    return []
```

Do the same pattern for redfin.py and zoocasa.py.

## Step 7 — Run full multi-source test

```bash
python -m scraper.run_all --source all --area gta
```

All sources should return listings. Orchestrator should print a total count.

## Step 8 — Clean up tools directory

```bash
rm -rf tools/
```

## Step 9 — Commit

```bash
git add scraper/kijiji.py scraper/redfin.py scraper/zoocasa.py
git commit -m "fix: real DOM selectors + Scrapling stealth for Kijiji, Redfin, Zoocasa"
```

## Step 10 — Mark done in CLAUDE.md

Open CLAUDE.md, find `| 1 | Fix Kijiji...` in the task table, change `[ ]` to `[x]`.
Then move to Task 2 by running `/project:persist-video-jobs`.
