# Web Crawling Setup - Cloudflare + Firecrawl

## Overview

Bypass 403 blocks on Realtor.ca and Condos.ca using browser-based crawling.

**Backends:**

- **Cloudflare Browser Rendering** (recommended) – Production-ready, trusted IPs
- **Firecrawl** (optional) – Developer-friendly API

## Setup

### Cloudflare Browser Rendering

1. **Get Account ID:**
   - Go to [Cloudflare Dashboard](https://dash.cloudflare.com)
   - Account ID is in the URL: `dash.cloudflare.com/<account-id>/`
   - Or find it in Account Home → Copy Account ID

2. **Create API Token:**
   - Profile → API Tokens → Create Token
   - Use template: "Edit Cloudflare Workers"
   - Add permission: **Browser Rendering: Edit**
   - Create Token → Copy the token

3. **Add to environment:**
   ```env
   CLOUDFLARE_ACCOUNT_ID=abc123def456
   CLOUDFLARE_API_TOKEN=your-token-here
   DEFAULT_CRAWL_BACKEND=cloudflare
   ```

### Firecrawl (Optional)

1. Sign up at [firecrawl.dev](https://firecrawl.dev)
2. Get API key from dashboard
3. Add to environment:
   ```env
   FIRECRAWL_API_KEY=fc-your-key-here
   ```

## Usage

### Via API

```bash
curl -X POST https://api.yourdomain.com/api/crawl \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.realtor.ca/map",
    "backend": "cloudflare",
    "max_depth": 2,
    "max_pages": 20,
    "include_patterns": ["/real-estate/"]
  }'
```

### In Code

```python
from scraper.crawler import CrawlRequest, CrawlBackend, crawl_site

request = CrawlRequest(
    url="https://www.realtor.ca/map",
    backend=CrawlBackend.CLOUDFLARE,
    max_depth=1,
    max_pages=20,
    include_patterns=["/real-estate/"],
)

result = await crawl_site(request)

for page in result.pages:
    print(f"{page.title}: {page.url}")
```

### Automatic Fallback

Realtor.ca scraper automatically uses the crawler if direct scraping and browser fallback fail:

```python
# In scraper orchestrator
listings = await scrape_realtor_ca(area="gta")  # Tries direct → Scrapling → browser → crawler
```

## Pricing

**Cloudflare Browser Rendering:**
- Pay-as-you-go: ~$0.005 per crawl
- Estimate: $5/month for 1000 crawls

**Firecrawl:**
- Free: 500 pages/month
- Starter: $29/month (10K pages)
- Growth: $99/month (50K pages)

## Testing

Test directly:

```bash
python -c "
import asyncio
from scraper.crawler import CrawlRequest, CrawlBackend, crawl_site

async def test():
    request = CrawlRequest(
        url='https://example.com',
        backend=CrawlBackend.CLOUDFLARE,
        max_depth=1,
        max_pages=5,
    )
    result = await crawl_site(request)
    print('Success:', result.stats.success)
    print('Pages:', len(result.pages))

asyncio.run(test())
"
```

## Troubleshooting

**"CLOUDFLARE_ACCOUNT_ID required"**
- Check environment variables are set in Railway
- Verify variable names match exactly

**"Crawl job timed out"**
- Reduce max_pages
- Reduce max_depth
- Check Cloudflare dashboard for job status

**"Crawler fallback failed"**
- Check API credentials
- Verify network connectivity
- Check Cloudflare/Firecrawl service status
