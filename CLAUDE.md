# 416Homes — Agent Instructions

You are a senior full-stack Python engineer working on 416Homes.
You have full autonomy. Never ask for permission. Never explain what you are
about to do — just do it, then summarize what changed and what was verified.

---

## What This Project Is

A zero-cost autonomous real estate agent for Toronto + Mississauga:

1. **Nightly scraper** — pulls active listings from 5 sources concurrently
2. **Valuation model** — LightGBM trained on sold comps, flags underpriced listings
3. **Agent loop** — matches listings to buyer alerts, emails listing agents via Gemini
4. **Video product** — converts any listing URL to a cinematic 30-sec MP4 ($99–$299 CAD, ~$8 cost)
5. **Virtual Tour product** — converts listing photos to a hosted room-by-room interactive tour ($49 CAD)
6. **FastAPI backend** — serves listings, valuations, video orders, tour orders, Stripe payments

---

## Deployment

| Service | Platform | URL |
|---------|----------|-----|
| Frontend (Next.js) | Vercel | https://416-homes.vercel.app |
| Backend (FastAPI) | DigitalOcean App Platform | https://fouronesixhomes-mcr6b.ondigitalocean.app |
| Database | Supabase | (env vars in DO + Vercel) |
| Telegram bots | DigitalOcean (worker component) | — |

**Git**: all code lives on `main` branch. Push to main → Vercel auto-deploys frontend, DO auto-deploys backend.

The worktree used for recent work is at:
`C:\Users\soobo\Downloads\416homesV3\.claude\worktrees\crazy-jepsen\`

---

## File Map

```
scraper/
  orchestrator.py      concurrent multi-source runner + deduplication
  realtor_ca.py        Scrapling(stealth) → API → Playwright fallback
  housesigma.py        sold comps, 33 neighbourhoods
  kijiji.py            listings + sqft regex extraction
  redfin.py            listings + sqft regex extraction
  zoocasa.py           listings + virtual_tour_url capture
  transit_data.py      TTC subway + LRT proximity scoring (0–10)
  run_all.py           CLI: python -m scraper.run_all --source X --area Y

memory/store.py        Supabase pgvector embed + search; persists floor_plan_url
valuation/model.py     LightGBM train + inference
agent/main.py          nightly match → valuate → email loop
video_pipeline/
  pipeline.py          URL → photos → script → voice → animate → MP4
tour_pipeline/
  pipeline.py          URL → photos → Gemini classify → room manifest → hosted tour
api/
  main.py              FastAPI: listings, alerts, valuation, video, tours, Stripe
  init_db.py           prints ALL Supabase schema SQL to paste and run
telegram_bot.py        admin bot: /listings, /status, /scan, /link
public_telegram_bot.py public user bot: alerts, /search, /listings
web-next/
  src/app/
    page.tsx           homepage (nav has: How It Works, Features, Get Started, Videos, Virtual Tours)
    dashboard/page.tsx listings dashboard + valuation tab + videos tab
    video/page.tsx     video product order page ($99/$249/$299)
    tours/page.tsx     virtual tour order page ($49)
    tours/[id]/page.tsx hosted interactive tour viewer
  src/components/
    listing-card.tsx   listing card with transit badge + ⬡ 3D Tour badge
    FloorPlanViewer.tsx  SSR-safe dynamic() shell
    FloorPlanViewerInner.tsx  iframe embed (real URL or Matterport demo)
  src/lib/api.ts       fetchListings — maps all fields including floor_plan_url
  src/types/index.ts   Listing interface includes floor_plan_url, transit_score, is_assignment
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| Scraping | scrapling + AsyncDynamicSession / Playwright fallback |
| LLM | Gemini 2.0 Flash |
| Embeddings | Gemini text-embedding-004 (768-dim) |
| Database | Supabase Postgres + pgvector |
| ML | LightGBM |
| API | FastAPI + uvicorn |
| Email/Payments | Resend / Stripe |
| Video | ElevenLabs TTS, FFmpeg, Google Cloud TTS fallback |
| CI/CD | GitHub Actions |

---

## Coding Rules

- All async code uses `async/await`. Never call `asyncio.run()` inside a function.
- All scrapers return: `id, address, price, bedrooms, bathrooms, area, lat, lng, source, url, scraped_at, strategy`
- Per-listing errors are caught and skipped — never crash the whole run.
- Secrets always come from `.env` via `python-dotenv`. Never hardcode.
- Supabase writes for listings go through `memory/store.py → embed_and_store_listing()`.
- HouseSigma comps go directly to the `sold_comps` table.
- After every code change run the relevant test command. Fix failures before continuing.

---

## Current State (as of 2026-04-15)

### ✅ Recently shipped (this session)

**Dashboard UX fixes:**
- "Back to 416Homes" button now navigates correctly (`<Link href="/">`)
- Transit badge is color-coded: Elite (9-10) / Excellent (7-8) / Good (5-6) / Fair (3-4) / Limited (1-2)
- `floor_plan_url` wired through `api.ts` fetchListings → listing cards
- `FloorPlanViewerInner`: Matterport demo mode (`jm5WwEA3HUN`) when no real tour URL

**Transit scoring (scraper/transit_data.py):**
- Expanded from ~20 keywords to 80+ covering full TTC subway (Yonge-University, Bloor-Danforth, Sheppard), Eglinton Crosstown LRT, Ontario Line, Finch West LRT, Hurontario LRT, 30+ Toronto neighbourhoods
- `api/main.py`: `_resolve_transit_score()` — city fallback so every listing gets a score: Toronto=4, Mississauga/905=3, other GTA=2. Never returns null.

**Floor plan / virtual tour scraping:**
- `scraper/realtor_ca.py`: captures `VirtualTourUrl` as `floor_plan_url`
- `scraper/zoocasa.py`: captures `virtual_tour_url` / `tour_url` as `floor_plan_url`
- `scraper/kijiji.py` + `redfin.py`: sqft regex extraction from card text
- `memory/store.py`: persists `floor_plan_url` column
- `api/main.py`: extracts `floor_plan_url` from DB row + raw_data fallback

**Listing cards:**
- Gold `⬡ 3D Tour` badge shown when `listing.floor_plan_url` is set
- Transit badge with tier label + color scale

**Virtual Tour product ($49 CAD) — NEW:**
- `tour_pipeline/pipeline.py`: fetch photos → Gemini Vision classify by room → build manifest → Supabase → email delivery link
- `api/main.py`: `POST /api/tour-jobs`, `GET /api/tour-jobs/{id}`, `POST /tour/create-checkout` (Stripe $49), `POST /tour/stripe-webhook`
- `web-next/src/app/tours/page.tsx`: product order page with progress polling + completion panel (shareable link + embed code)
- `web-next/src/app/tours/[id]/page.tsx`: interactive room-by-room viewer with lightbox + keyboard nav
- Nav links added to homepage + dashboard

**Telegram bots:**
- Fixed `API_BASE_URL` env var on DigitalOcean (was causing "unable to fetch listings")
- Both bots now show beds/baths/sqft + floor plan link per listing card

**Homepage / video page:**
- Removed tech-heavy labels ("Live from Supabase", "Auto-refreshed from listings API")
- Replaced with brand copy + video CTA
- Video page preview overlay: removed hardcoded address/price/headline

### ⚠️ Manual steps still needed

1. **Supabase SQL migration** — run this in Supabase SQL editor to enable tour jobs:
```sql
CREATE TABLE IF NOT EXISTS tour_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  listing_url TEXT,
  customer_email TEXT NOT NULL,
  customer_name TEXT,
  status TEXT DEFAULT 'pending',
  progress INTEGER DEFAULT 0,
  tour_url TEXT,
  photo_manifest JSONB,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

2. **Valuation model** — not yet trained. Run once with sold_comps in Supabase:
```bash
python valuation/model.py
```
Then trigger GitHub Actions → "416Homes Model Retraining" → Run workflow (commits `valuation_model.pkl` back to main).

3. **Stripe webhook for tours** — add `/tour/stripe-webhook` URL in Stripe dashboard pointing to the DO backend.

---

## API Endpoints Reference

```
GET  /api/listings          listings with transit_score, floor_plan_url, is_assignment
GET  /api/listings/search   vector search + ILIKE fallback
POST /api/valuate           LightGBM valuation
POST /api/tour-jobs         create tour job (dev/internal, bypasses Stripe)
GET  /api/tour-jobs/{id}    poll tour job status + manifest
POST /tour/create-checkout  Stripe checkout $49 CAD for virtual tour
POST /tour/stripe-webhook   Stripe webhook → creates tour_jobs record
POST /video/create-checkout Stripe checkout $99/$249/$299 for video
POST /video/stripe-webhook  Stripe webhook → creates video_jobs record
GET  /api/video-jobs/{id}   poll video job status
GET  /health                health check
```

---

## Test Commands

```bash
# Scrapers
python -m scraper.run_all --source kijiji --area toronto  # ≥10 listings
python -m scraper.run_all --source all --area gta

# Backend
uvicorn api.main:app --reload --port 8000
curl http://localhost:8000/health
curl http://localhost:8000/api/listings?limit=5

# Valuation model
python valuation/model.py   # target MAPE <10%

# Video pipeline
python video_pipeline/pipeline.py https://www.realtor.ca/real-estate/LISTING_URL

# Agent loop
python agent/main.py

# Tour job (test without Stripe)
curl -X POST http://localhost:8000/api/tour-jobs \
  -H "Content-Type: application/json" \
  -d '{"listing_url":"https://www.realtor.ca/real-estate/123","customer_email":"test@test.com"}'
```

---

## Environment Variables

Required in both DO (backend) and `.env` (local):
```
SUPABASE_URL
SUPABASE_KEY
SUPABASE_SERVICE_ROLE_KEY
GEMINI_API_KEY
RESEND_API_KEY
STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET
ELEVENLABS_API_KEY
APP_URL=https://416-homes.vercel.app
API_BASE_URL=https://fouronesixhomes-mcr6b.ondigitalocean.app  # for Telegram bots on DO
```

Required in Vercel (frontend):
```
NEXT_PUBLIC_API_URL=https://fouronesixhomes-mcr6b.ondigitalocean.app
```
