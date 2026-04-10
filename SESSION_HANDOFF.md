# 416Homes — Session Handoff
_Last updated: 2026-04-09_

---

## Current State

Railway is **dead** (ran out of free credits + build was failing).
Backend is being migrated to **DigitalOcean App Platform** using the GitHub Student Pack ($200 credit).
Frontend remains on **Vercel** (unchanged, working).
The last DO build failed on Python version — fix is pushed, next build should succeed.

### Live URLs
- **Frontend (Vercel):** check Vercel dashboard — Next.js `web-next/`
- **Backend (DigitalOcean App Platform):** deploy in progress — will be `https://homes-XXXXX.ondigitalocean.app`
- **Health check:** `GET /api/health` → `{"status":"ok"}`

---

## What Was Done This Session

### Vercel Build Fixed
- Removed `next/font/google` from `layout.tsx` — was failing at build time when Google Fonts unreachable
- Replaced with runtime `<link>` tags for both Inter and Cormorant Garamond
- File: `web-next/src/app/layout.tsx`

### Footer Fixed Across All Pages
- All footers updated: `© 2024/2025` → `© 2026 416Homes · All rights reserved`
- Files: `web-next/src/app/page.tsx`, `web-next/src/app/dashboard/page.tsx`, `web-next/src/app/video/page.tsx`, `web/index.html`, `web/dashboard.html`, `web/video.html`

### Auth Gates Added
- `web/video.html` — added auth guard (redirects to `/login` if not logged in)
- `web/agent.html` — added auth guard + `AGENT_SECRET` password input wired into `startAgent()` / `stopAgent()` headers

### Sqft Fix
- `memory/store.py` was writing `"sqft"` key but Supabase column is `"area"` — silently dropped
- Fixed in `_normalise_for_listings()`, `_normalise_for_sold_comps()`, and searchable_text
- File: `memory/store.py`

### GitHub Actions Fixes
- Added `PYTHONPATH: ${{ github.workspace }}` to agent + train-model jobs
- Removed broken email steps from notify job (secrets not configured)
- File: `.github/workflows/nightly.yml`

### DigitalOcean Migration
- Added `.do/app.yaml` — App Platform spec (2 services: api-server + telegram-worker, $5/month each)
- Removed conflicting Railway config files: `.railway/api-server.json`, `.railway/railway-worker.toml`
- Fixed `nixpacks.toml`: added `--retries 5 --timeout 60` to pip install
- Added `.python-version` with `3.11`
- Split requirements: `requirements.txt` → redirects to `requirements-railway.txt` (slim, for DO); `requirements-full.txt` → full stack (for GitHub Actions scraper + training jobs)
- Updated `nightly.yml` + `retrain.yml` to use `requirements-full.txt` for heavy jobs
- Files: `.do/app.yaml`, `.python-version`, `requirements.txt`, `requirements-full.txt`, `nixpacks.toml`, `.github/workflows/nightly.yml`, `.github/workflows/retrain.yml`

---

## DigitalOcean Deploy Status

**Build failures encountered (both fixed and pushed):**
1. First fail: DO buildpack installed `requirements.txt` (heavy — scipy needed gfortran Fortran compiler not present). Fix: `requirements.txt` now redirects to slim `requirements-railway.txt`.
2. Second fail: Python 3.12.13 returned 404 from DO's CDN. Fix: `.python-version` changed to `3.11`.

**Current commit:** `96e5a2d` — "Fix build: use Python 3.11"
**Expected outcome:** Build should succeed now. If it still fails, paste the new log.

### After DO Build Succeeds — Required Steps
1. **Copy the new DO URL** (format: `https://api-server-XXXXX.ondigitalocean.app`)
2. **Update Vercel env var** `NEXT_PUBLIC_API_URL` to the new DO URL
3. **Set `APP_URL` in DO** to your Vercel frontend URL (for CORS)
4. **Run the scraper** via GitHub Actions → "416Homes Nightly Pipeline" → Run workflow
5. **Check listings appear** in the dashboard (~10 min after scraper finishes)

### Environment Variables Needed in DigitalOcean Dashboard
```
SUPABASE_URL
SUPABASE_KEY
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_JWT_SECRET
GEMINI_API_KEY
RESEND_API_KEY
STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET
STRIPE_PUBLISHABLE_KEY
ELEVENLABS_API_KEY
TELEGRAM_BOT_TOKEN
TELEGRAM_BOT_TOKEN_PUBLIC
TELEGRAM_CHAT_ID
GOOGLE_CLOUD_PROJECT
GOOGLE_CLOUD_LOCATION
APP_URL=https://your-vercel-url.vercel.app
AGENT_SECRET
```

---

## DigitalOcean MCP (Optional — Highly Recommended)
Connect Claude Code directly to your DO account so it can check build logs and deployments without you copy-pasting:
1. DO dashboard → API → Generate New Token (read + write)
2. Claude Code settings → Add custom MCP connector:
   - URL: `https://apps.mcp.digitalocean.com/mcp`
   - Auth: `Authorization: Bearer <your_token>`

---

## File Map (Updated)

```
scraper/
  orchestrator.py       concurrent multi-source runner + dedup
  realtor_ca.py         stealth + API + Playwright fallback
  housesigma.py         sold comps, headless=True
  kijiji.py / redfin.py / zoocasa.py
  run_all.py            CLI: python -m scraper.run_all --source X --area Y

memory/store.py
  _parse_room_count()   converts "1 + 1" → "2" before DB insert
  "area" key (not "sqft") used throughout — matches Supabase column name

valuation/model.py
  market_analysis_from_ppsf()  shared with api/main.py
  ValuationModel               joblib inside try/except (Railway/DO-safe)

agent/main.py           nightly match → valuate → email loop
  table: "alerts"       (not "buyer_alerts")
  alert fields: min_beds, property_types, neighbourhoods

api/main.py             FastAPI
  /api/health           → {"status":"ok"}
  /api/listings         paginated, filterable
  /api/valuate          LightGBM → fallback $600/sqft
  /api/alerts           CRUD (table: alerts)
  /api/video/*          job create/status/revision
  /api/stripe/webhook   payment handler
  CORS reads from APP_URL env var (comma-separated list allowed)

web-next/
  src/app/layout.tsx          Inter + Cormorant Garamond via <link> tags (no next/font/google)
  src/app/globals.css         CSS tokens + glass/gold utilities
  src/app/page.tsx            landing page (Framer Motion)
  src/app/dashboard/page.tsx  dashboard + listing cards + valuation (relative z-10 on filter card)
  src/app/video/page.tsx      video order flow
  src/components/DropdownSelect.tsx  custom dropdown (z-50, onMouseDown)
  src/lib/api.ts              reads NEXT_PUBLIC_API_URL env var

web/
  index.html            static landing (auth.js included)
  dashboard.html        static dashboard fallback
  video.html            auth-gated, redirects to /login if not logged in
  agent.html            auth-gated, AGENT_SECRET input wired to API headers

.do/app.yaml            DigitalOcean App Platform spec
.python-version         3.11
requirements.txt        → redirects to requirements-railway.txt (slim, for DO)
requirements-railway.txt  API-only deps (no scrapling/lightgbm/playwright)
requirements-full.txt   Full stack (scraper + ML — used by GitHub Actions)
nixpacks.toml           python311 + ffmpeg; pip --retries 5 --timeout 60

.github/workflows/
  nightly.yml           scrape(full) + train-model(full) + agent(slim) → notify
  retrain.yml           weekly LightGBM retrain using requirements-full.txt
  refresh-listings.yml  every 3 hours scraper
```

---

## Database Schema Notes

Key tables in Supabase:
- `listings` — active listings with `photo TEXT`, `area` (sqft), `embedding vector(768)`
- `sold_comps` — sold comps from HouseSigma
- `video_jobs` — video pipeline state machine
- `alerts` — buyer alerts (**NOT** `buyer_alerts`)
- `agent_matches` — listing × alert match log
- `users` — email-based user records

Supabase column is `area` (not `sqft`) — this is correct and fixed in `memory/store.py`.

---

## Pending / Next Steps

### Critical (nothing works without these)
1. **DO build succeeds** — if still failing, paste new log in new session
2. **Update Vercel env var** `NEXT_PUBLIC_API_URL` to new DO URL
3. **Set `APP_URL` in DO** to Vercel URL (CORS)
4. **Run scraper** via GitHub Actions to populate listings
5. **Stripe webhook** — update endpoint URL in Stripe dashboard from Railway URL to new DO URL

### Must Do for Valuation to Work
6. **Train the LightGBM model** (needs sold comps in DB first):
   ```bash
   python valuation/model.py
   ```
   Or: GitHub Actions → "416Homes Model Retraining" → Run workflow.
   Target MAPE < 10%. Workflow commits `valuation_model.pkl` back to repo.

### Nice to Have
- Sentry error tracking (free tier at sentry.io)
- PostHog analytics (free tier)
- Listing photo carousel (currently single photo)
- Telegram alert integration (scaffolded, needs `TELEGRAM_BOT_TOKEN`)

---

## Test Commands

```bash
# Scraper
python -m scraper.run_all --source realtor_ca --area toronto
python -m scraper.run_all --source all --area gta

# API
uvicorn api.main:app --reload --port 8000
curl http://localhost:8000/api/health
curl "http://localhost:8000/api/listings?limit=5"

# Valuation
python valuation/model.py    # target MAPE <10%

# Agent
python agent/main.py

# Video
python video_pipeline/pipeline.py https://www.realtor.ca/real-estate/LISTING_URL
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| Frontend | Next.js + React + TypeScript + Tailwind + Framer Motion (Vercel) |
| Backend | FastAPI + uvicorn (DigitalOcean App Platform) |
| Scraping | scrapling + AsyncDynamicSession / Playwright fallback |
| LLM | Gemini 2.0 Flash (`google-genai` SDK) |
| Embeddings | `gemini-embedding-001` |
| Database | Supabase Postgres + pgvector (768-dim) |
| ML | LightGBM (not installed on DO; fallback $600/sqft) |
| Email | Resend |
| Payments | Stripe |
| Video | ElevenLabs TTS + Veo (Vertex AI) |
| CI/CD | GitHub Actions (nightly scrape + model retrain) |

---

## Branch / Commit History

All work is on `main`. No open PRs. No open conflicts.

Recent commits:
- `96e5a2d` Fix build: use Python 3.11
- `8d8060b` Fix DO build: pin Python 3.12, slim requirements.txt
- `31036ef` Migrate to DigitalOcean App Platform + fix build config
- `726bdf6` Resolve merge conflict: use link tags for Inter + Cormorant Garamond
- `139179e` Fix remaining stale footer years: 2025→2026
